"""
Main pipeline for LexIntel document processing.

Orchestrates the full document processing pipeline: load input, split sections,
extract entities, extract events, and return structured event dictionaries.

Database persistence is handled automatically — events are saved to PostgreSQL
after each case is processed. If DATABASE_URL is not set, pipeline still works
but logs a warning (useful for local dev without Supabase).
"""

import logging
from typing import Any

from document_pipeline.extraction.event_extractor import extract_events
from document_pipeline.extraction.ner import extract_entities
from document_pipeline.ingestion.dataset_loader import load_cases
from document_pipeline.ingestion.pdf_loader import extract_pdf_text
from document_pipeline.preprocessing.section_splitter import split_sections

logger = logging.getLogger(__name__)


def _try_save_events(events: list[dict[str, Any]]) -> None:
    """
    Attempt to persist events to PostgreSQL.
    Fails silently with a warning if DATABASE_URL is not configured.
    This keeps the pipeline usable in dev without a database.
    """
    try:
        from document_pipeline.database.postgres_client import (
            get_connection,
            insert_events_batch,
        )
        with get_connection() as conn:
            inserted = insert_events_batch(conn, events)
            saved = sum(1 for i in inserted if i is not None)
            logger.info("[Pipeline] Saved %d/%d events to database.", saved, len(events))
    except Exception as e:
        logger.warning(
            "[Pipeline] Database save skipped: %s. "
            "Set DATABASE_URL in .env to enable persistence.",
            e,
        )


def process_document(file_path: str) -> list[dict[str, Any]]:
    """
    Process a single PDF document through the full pipeline.

    Steps: extract PDF text → split sections → extract entities → extract events
           → persist to database.
    Returns structured events as dictionaries.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of event dicts.
    """
    print(f"[Pipeline] Loading PDF: {file_path}")
    text = extract_pdf_text(file_path)

    print("[Pipeline] Splitting into sections")
    sections = split_sections(text)

    section_texts = [
        sections["facts"],
        sections["witness"],
        sections["other"],
    ]
    combined_text = "\n\n".join(t for t in section_texts if t)

    print("[Pipeline] Extracting entities")
    entities = extract_entities(combined_text)
    print(
        f"[Pipeline] Entities found: persons={len(entities['persons'])}, "
        f"locations={len(entities['locations'])}, dates={len(entities['dates'])}, "
        f"times={len(entities['times'])}"
    )

    print("[Pipeline] Extracting events")
    event_objs = extract_events(combined_text, source_document=file_path)
    print(f"[Pipeline] Extracted {len(event_objs)} events")

    events = [e.model_dump() for e in event_objs]

    # Persist to database
    _try_save_events(events)

    return events


def process_dataset(file_path: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    Process a dataset of cases through the pipeline.

    Loads cases from the dataset, extracts events for each case, persists
    them to PostgreSQL, and returns a flat list of structured event dicts.

    Args:
        file_path: Path to the dataset file (e.g., text.data.jsonl).
        limit: Maximum number of cases to process (default 100).

    Returns:
        List of event dicts.
    """
    print(f"[Pipeline] Loading dataset: {file_path} (limit={limit})")
    cases = load_cases(file_path, limit=limit)
    print(f"[Pipeline] Loaded {len(cases)} cases")

    all_events: list[dict[str, Any]] = []

    for i, case in enumerate(cases):
        case_id = case.get("case_id", "")
        text = case.get("text", "")
        if not text:
            continue

        print(f"[Pipeline] Processing case {i + 1}/{len(cases)}: {case_id}")

        sections = split_sections(text)
        section_texts = [
            sections["facts"],
            sections["witness"],
            sections["other"],
        ]
        combined_text = "\n\n".join(t for t in section_texts if t)

        entities = extract_entities(combined_text)
        print(
            f"[Pipeline] Entities: persons={len(entities['persons'])}, "
            f"locations={len(entities['locations'])}, dates={len(entities['dates'])}, "
            f"times={len(entities['times'])}"
        )

        event_objs = extract_events(combined_text, source_document=str(case_id))
        case_events = [e.model_dump() for e in event_objs]

        # Persist this case's events immediately
        _try_save_events(case_events)

        all_events.extend(case_events)
        print(f"[Pipeline] Extracted {len(event_objs)} events from case {case_id}")

    print(f"[Pipeline] Total events extracted: {len(all_events)}")
    return all_events