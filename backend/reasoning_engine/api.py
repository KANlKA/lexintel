"""
FastAPI service for LexIntel reasoning engine.

Run with:
    cd LexIntel/backend
    uvicorn reasoning_engine.api:app --reload --port 8000
"""

import logging
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

_cache: dict[str, Any] = {}


@app.on_event("startup")
def startup_event():
    try:
        from document_pipeline.database.postgres_client import initialize_schema
        initialize_schema()
    except Exception as e:
        logger.warning("DB init skipped: %s", e)


# ── Models ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    dataset_path: str = "../dataset/text.data.jsonl"
    limit: int = 5


# ── Core reasoning function ──────────────────────────────────────────────────

def _run_reasoning(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Shared reasoning logic used by both /analyze and /analyze/events.
    Builds graph, timeline, contradictions, weaknesses, persists to DB.
    """
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


def _persist_reasoning(contradictions: list[dict], weaknesses: list[dict]) -> None:
    try:
        from document_pipeline.database.postgres_client import (
            get_connection, insert_contradiction, insert_weakness,
        )
        with get_connection() as conn:
            for c in contradictions:
                insert_contradiction(conn, c)
            for w in weaknesses:
                insert_weakness(conn, w)
    except Exception as e:
        logger.warning("DB persist skipped: %s", e)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "service": "LexIntel reasoning API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/analyze", "/analyze/events", "/events", "/timeline", "/contradictions", "/weaknesses", "/summary"],
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Run full pipeline + reasoning on the JSONL dataset.
    Used by the dashboard for the default CAP dataset.
    """
    from document_pipeline.pipeline import process_dataset

    path = Path(request.dataset_path)
    if not path.exists():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / request.dataset_path

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {request.dataset_path}")

    try:
        events = process_dataset(str(path), limit=request.limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    if not events:
        raise HTTPException(status_code=422, detail="No events extracted.")

    return _run_reasoning(events)


@app.post("/analyze/events")
def analyze_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Run reasoning on a pre-extracted list of events.

    Used by the case workspace upload flow:
      1. Frontend uploads files -> POST /process/case (port 8001) -> gets events[]
      2. Frontend sends those events -> POST /analyze/events (port 8000) -> gets full analysis

    This keeps file handling on port 8001 and reasoning on port 8000.
    """
    if not events:
        raise HTTPException(status_code=422, detail="No events provided.")

    return _run_reasoning(events)


@app.get("/events")
def get_events() -> list[dict[str, Any]]:
    if "events" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["events"]


@app.get("/timeline")
def get_timeline() -> list[dict[str, Any]]:
    if "timeline" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["timeline"]


@app.get("/contradictions")
def get_contradictions() -> list[dict[str, Any]]:
    if "contradictions" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["contradictions"]


@app.get("/weaknesses")
def get_weaknesses() -> list[dict[str, Any]]:
    if "weaknesses" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")
    return _cache["weaknesses"]


@app.get("/summary")
def get_summary() -> dict[str, Any]:
    if "events" not in _cache:
        raise HTTPException(status_code=404, detail="No analysis run yet. Call POST /analyze first.")

    events = _cache["events"]
    timeline = _cache["timeline"]
    contradictions = _cache["contradictions"]
    weaknesses = _cache["weaknesses"]

    try:
        return {
            "events_total": len(events),
            "timed_events": sum(1 for t in timeline if not t.get("time_uncertain")),
            "uncertain_events": sum(1 for t in timeline if t.get("time_uncertain")),
            "contradictions_total": len(contradictions),
            "critical_contradictions": sum(1 for c in contradictions if c.get("severity") == "critical"),
            "high_weakness_events": sum(1 for w in weaknesses if w.get("severity") == "high"),
            "medium_weakness_events": sum(1 for w in weaknesses if w.get("severity") == "medium"),
            "low_weakness_events": sum(1 for w in weaknesses if w.get("severity") == "low"),
            "graph": _cache.get("graph_summary", {}),
        }
    except Exception as e:
        logger.exception("Failed building summary response: %s", e)
        raise HTTPException(status_code=500, detail="Failed to build summary from cached analysis.")
