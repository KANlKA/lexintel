"""
FastAPI service for LexIntel reasoning engine.

Runs on port 8000. Calls the document pipeline (port 8001) or directly
imports the pipeline module, then applies graph/timeline/contradiction/
weakness analysis.

Run with:
    cd LexIntel/backend
    uvicorn reasoning_engine.api:app --reload --port 8000

Endpoints:
    GET  /health           — health check
    POST /analyze          — full pipeline + reasoning on a dataset
    GET  /events           — last analyzed events
    GET  /timeline         — chronological timeline
    GET  /contradictions   — detected contradictions
    GET  /weaknesses       — weakness scores (sorted high → low)
    GET  /summary          — case summary stats
"""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reasoning_engine.event_graph import EventGraph
from reasoning_engine.timeline_builder import build_timeline
from reasoning_engine.contradiction_detector import detect_contradictions
from reasoning_engine.weakness_analyzer import analyze_weaknesses

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LexIntel Reasoning Engine API",
    description="Analyzes legal events for timeline, contradictions, and weaknesses.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache — holds the last analyzed case set
# Replace with DB reads once persistence is fully wired
_cache: dict[str, Any] = {}


def _resolve_dataset_path(dataset_path: str) -> Path:
    path = Path(dataset_path)
    if path.exists():
        return path

    backend_dir = Path(__file__).resolve().parent.parent
    candidate = backend_dir / dataset_path
    if candidate.exists():
        return candidate

    repo_candidate = backend_dir.parent / dataset_path.lstrip("./")
    if repo_candidate.exists():
        return repo_candidate

    return path


@app.on_event("startup")
def startup_event():
    """Initialize schema and prewarm analysis cache for local development."""
    try:
        from document_pipeline.database.postgres_client import initialize_schema
        initialize_schema()
        logger.info("Database schema ready.")
    except Exception as e:
        logger.warning("DB init skipped: %s", e)

    preload_enabled = os.getenv("LEXINTEL_PRELOAD_ANALYSIS", "1") != "0"
    if not preload_enabled or _cache.get("events"):
        return

    dataset_path = os.getenv("LEXINTEL_DATASET_PATH", "../dataset/text.data.jsonl")
    limit = int(os.getenv("LEXINTEL_PRELOAD_LIMIT", "3"))
    try:
        _run_analysis(dataset_path=dataset_path, limit=limit)
        logger.info("Preloaded reasoning cache from %s (limit=%d).", dataset_path, limit)
    except Exception as e:
        logger.warning("Startup preload skipped: %s", e)


# ── Models ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    dataset_path: str = "../dataset/text.data.jsonl"
    limit: int = 5


class AnalyzeSummary(BaseModel):
    events_total: int
    timed_events: int
    uncertain_events: int
    contradictions_total: int
    critical_contradictions: int
    high_weakness_events: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {
        "service": "LexIntel Reasoning Engine API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/health", "/analyze", "/events", "/timeline", "/contradictions", "/weaknesses", "/summary"],
    }


@app.get("/health")
def health() -> dict:
    return {
        "service": "LexIntel reasoning API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/analyze", "/events", "/timeline", "/contradictions", "/weaknesses", "/summary"],
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Run the full pipeline + reasoning chain on a dataset.

    Steps:
      1. Extract events via document pipeline
      2. Build event graph
      3. Build timeline
      4. Detect contradictions
      5. Score weaknesses
      6. Persist results to DB (if DATABASE_URL set)

    Example body:
        { "dataset_path": "../dataset/text.data.jsonl", "limit": 5 }
    """
    try:
        return _run_analysis(dataset_path=request.dataset_path, limit=request.limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


def _run_analysis(dataset_path: str, limit: int) -> dict[str, Any]:
    from document_pipeline.pipeline import process_dataset

    path = _resolve_dataset_path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    events = process_dataset(str(path), limit=limit)
    if not events:
        raise ValueError("No events extracted from dataset.")

    graph = EventGraph()
    graph.build(events)
    timeline = build_timeline(events)
    contradictions = detect_contradictions(events)
    weaknesses = analyze_weaknesses(events, contradictions)
    _persist_reasoning(contradictions, weaknesses)

    _cache["events"] = events
    _cache["timeline"] = timeline
    _cache["contradictions"] = contradictions
    _cache["weaknesses"] = weaknesses
    _cache["graph_summary"] = graph.summary()

    return {
        "status": "success",
        "events_extracted": len(events),
        "timeline_events": len(timeline),
        "contradictions_found": len(contradictions),
        "weaknesses_scored": len(weaknesses),
        "graph": graph.summary(),
    }


def _persist_reasoning(
    contradictions: list[dict],
    weaknesses: list[dict],
) -> None:
    """Persist contradiction and weakness results to DB. Silent on failure."""
    try:
        from document_pipeline.database.postgres_client import (
            get_connection,
            insert_contradiction,
            insert_weakness,
        )
        with get_connection() as conn:
            for c in contradictions:
                insert_contradiction(conn, c)
            for w in weaknesses:
                insert_weakness(conn, w)
        logger.info(
            "[Reasoning] Persisted %d contradictions, %d weakness scores.",
            len(contradictions),
            len(weaknesses),
        )
    except Exception as e:
        logger.warning("[Reasoning] DB persist skipped: %s", e)


@app.get("/events")
def get_events() -> list[dict[str, Any]]:
    """Return all events from the last /analyze call."""
    if "events" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["events"]


@app.get("/timeline")
def get_timeline() -> list[dict[str, Any]]:
    """Return events sorted chronologically from the last /analyze call."""
    if "timeline" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["timeline"]


@app.get("/contradictions")
def get_contradictions() -> list[dict[str, Any]]:
    """Return detected contradictions from the last /analyze call."""
    if "contradictions" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["contradictions"]


@app.get("/weaknesses")
def get_weaknesses() -> list[dict[str, Any]]:
    """Return weakness scores sorted high → low from the last /analyze call."""
    if "weaknesses" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["weaknesses"]


@app.get("/summary")
def get_summary() -> dict[str, Any]:
    """Return summary statistics from the last /analyze call."""
    if "events" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")

    events = _cache["events"]
    timeline = _cache["timeline"]
    contradictions = _cache["contradictions"]
    weaknesses = _cache["weaknesses"]

    return {
        "events_total": len(events),
        "timed_events": sum(1 for t in timeline if not t.get("time_uncertain")),
        "uncertain_events": sum(1 for t in timeline if t.get("time_uncertain")),
        "contradictions_total": len(contradictions),
        "critical_contradictions": sum(1 for c in contradictions if c["severity"] == "critical"),
        "high_weakness_events": sum(1 for w in weaknesses if w["severity"] == "high"),
        "medium_weakness_events": sum(1 for w in weaknesses if w["severity"] == "medium"),
        "low_weakness_events": sum(1 for w in weaknesses if w["severity"] == "low"),
        "graph": _cache.get("graph_summary", {}),
    }
