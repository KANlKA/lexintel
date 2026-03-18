"""
PostgreSQL client for LexIntel document pipeline.

Handles persistence of extracted events and document metadata
to a PostgreSQL database using psycopg2.

Setup: pip install psycopg2-binary
Connection string from Supabase dashboard:
  postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# --- Schema DDL (run once to create tables) ---
# user_id column is included from the start so RLS works correctly.
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    time            TEXT,
    location        TEXT,
    source_document TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.8,
    user_id         UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contradictions (
    id              SERIAL PRIMARY KEY,
    event1_id       TEXT REFERENCES events(event_id),
    event2_id       TEXT REFERENCES events(event_id),
    type            TEXT NOT NULL,
    description     TEXT,
    severity        TEXT DEFAULT 'moderate',
    user_id         UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS timeline (
    id              SERIAL PRIMARY KEY,
    event_id        TEXT REFERENCES events(event_id),
    parsed_time     TEXT,
    time_uncertain  BOOLEAN DEFAULT FALSE,
    position        INT,
    user_id         UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weakness_scores (
    id              SERIAL PRIMARY KEY,
    event_id        TEXT REFERENCES events(event_id),
    weakness_score  FLOAT NOT NULL,
    reasons         TEXT[],
    user_id         UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE events          ENABLE ROW LEVEL SECURITY;
ALTER TABLE contradictions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline        ENABLE ROW LEVEL SECURITY;
ALTER TABLE weakness_scores ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'events' AND policyname = 'own events'
  ) THEN
    CREATE POLICY "own events" ON events FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'contradictions' AND policyname = 'own contradictions'
  ) THEN
    CREATE POLICY "own contradictions" ON contradictions FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'timeline' AND policyname = 'own timeline'
  ) THEN
    CREATE POLICY "own timeline" ON timeline FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'weakness_scores' AND policyname = 'own weaknesses'
  ) THEN
    CREATE POLICY "own weaknesses" ON weakness_scores FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;
"""


def _get_connection_string() -> str:
    """Get PostgreSQL connection string from environment."""
    conn_str = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not conn_str:
        raise ValueError(
            "DATABASE_URL not set. Add your Supabase connection string to .env\n"
            "Example: DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres"
        )
    return conn_str


@contextmanager
def get_connection(connection_string: str | None = None) -> Generator[Any, None, None]:
    """
    Create a PostgreSQL connection context manager.

    Args:
        connection_string: PostgreSQL URI. If None, reads from DATABASE_URL env var.

    Yields:
        psycopg2 connection object.
    """
    conn_str = connection_string or _get_connection_string()
    conn = None
    try:
        conn = psycopg2.connect(conn_str)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Database error: %s", e)
        raise
    finally:
        if conn:
            conn.close()


def initialize_schema(connection_string: str | None = None) -> None:
    """
    Create all required tables if they don't exist.
    Safe to call multiple times — uses IF NOT EXISTS and DO $$ blocks.
    Call this once on startup.
    """
    with get_connection(connection_string) as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
    logger.info("Database schema initialized.")


def insert_event(
    connection: Any,
    event: dict[str, Any],
    document_id: str | None = None,
    user_id: str | None = None,
) -> str | None:
    """
    Insert an extracted event into the events table.

    Args:
        connection: Active psycopg2 connection.
        event: Event dict with event_id, actor, action, etc.
        document_id: Optional override for source_document.
        user_id: Optional Supabase user UUID for RLS.

    Returns:
        event_id string if inserted, None on duplicate.
    """
    sql = """
        INSERT INTO events (event_id, actor, action, time, location, source_document, confidence, user_id)
        VALUES (%(event_id)s, %(actor)s, %(action)s, %(time)s, %(location)s, %(source_document)s, %(confidence)s, %(user_id)s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id;
    """
    row = {
        "event_id": event.get("event_id"),
        "actor": event.get("actor", ""),
        "action": event.get("action", ""),
        "time": event.get("time"),
        "location": event.get("location"),
        "source_document": document_id or event.get("source_document", ""),
        "confidence": event.get("confidence", 0.8),
        "user_id": user_id,
    }
    with connection.cursor() as cur:
        cur.execute(sql, row)
        result = cur.fetchone()
        return result[0] if result else None


def insert_events_batch(
    connection: Any,
    events: list[dict[str, Any]],
    document_id: str | None = None,
    user_id: str | None = None,
) -> list[str | None]:
    """
    Insert multiple events efficiently.

    Args:
        connection: Active psycopg2 connection.
        events: List of event dicts.
        document_id: Optional override for source_document.
        user_id: Optional Supabase user UUID for RLS.

    Returns:
        List of inserted event_ids (None for duplicates).
    """
    if not events:
        return []

    sql = """
        INSERT INTO events (event_id, actor, action, time, location, source_document, confidence, user_id)
        VALUES (%(event_id)s, %(actor)s, %(action)s, %(time)s, %(location)s, %(source_document)s, %(confidence)s, %(user_id)s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id;
    """
    rows = [
        {
            "event_id": e.get("event_id"),
            "actor": e.get("actor", ""),
            "action": e.get("action", ""),
            "time": e.get("time"),
            "location": e.get("location"),
            "source_document": document_id or e.get("source_document", ""),
            "confidence": e.get("confidence", 0.8),
            "user_id": user_id,
        }
        for e in events
    ]
    ids: list[str | None] = []
    with connection.cursor() as cur:
        for row in rows:
            cur.execute(sql, row)
            result = cur.fetchone()
            ids.append(result[0] if result else None)
    logger.info("Inserted %d events into database.", sum(1 for i in ids if i))
    return ids


def insert_contradiction(
    connection: Any,
    contradiction: dict[str, Any],
    user_id: str | None = None,
) -> int | None:
    """Insert a detected contradiction."""
    sql = """
        INSERT INTO contradictions (event1_id, event2_id, type, description, severity, user_id)
        VALUES (%(event1_id)s, %(event2_id)s, %(type)s, %(description)s, %(severity)s, %(user_id)s)
        RETURNING id;
    """
    row = {**contradiction, "user_id": user_id}
    with connection.cursor() as cur:
        cur.execute(sql, row)
        result = cur.fetchone()
        return result[0] if result else None


def insert_weakness(
    connection: Any,
    weakness: dict[str, Any],
    user_id: str | None = None,
) -> int | None:
    """Insert a weakness score record."""
    sql = """
        INSERT INTO weakness_scores (event_id, weakness_score, reasons, user_id)
        VALUES (%(event_id)s, %(weakness_score)s, %(reasons)s, %(user_id)s)
        RETURNING id;
    """
    row = {
        "event_id": weakness.get("event_id"),
        "weakness_score": weakness.get("weakness_score", 0.0),
        "reasons": weakness.get("reasons", []),
        "user_id": user_id,
    }
    with connection.cursor() as cur:
        cur.execute(sql, row)
        result = cur.fetchone()
        return result[0] if result else None


def fetch_all_events(connection: Any) -> list[dict[str, Any]]:
    """Retrieve all events from the database."""
    with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM events ORDER BY created_at;")
        return [dict(row) for row in cur.fetchall()]


def fetch_contradictions(connection: Any) -> list[dict[str, Any]]:
    """Retrieve all contradictions from the database."""
    with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM contradictions ORDER BY severity DESC;")
        return [dict(row) for row in cur.fetchall()]