from fastapi import FastAPI
from document_pipeline.pipeline import process_dataset
from reasoning_engine.timeline_builder import build_timeline
from reasoning_engine.contradiction_detector import detect_contradictions
from reasoning_engine.weakness_analyzer import score_weakness

app = FastAPI()
_cache = {}  # replace with DB later


@app.get("/")
def root():
    return {
        "service": "LexIntel reasoning API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/analyze", "/events", "/timeline", "/contradictions", "/weaknesses"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(dataset_path: str, limit: int = 5):
    events = process_dataset(dataset_path, limit=limit)
    timeline = build_timeline(events)
    contradictions = detect_contradictions(events)
    weaknesses = [score_weakness(e, contradictions) for e in events]
    _cache["last"] = {"events": events, "timeline": timeline,
                      "contradictions": contradictions, "weaknesses": weaknesses}
    return _cache["last"]

@app.get("/events")
def get_events():
    return _cache.get("last", {}).get("events", [])

@app.get("/timeline")
def get_timeline():
    return _cache.get("last", {}).get("timeline", [])

@app.get("/contradictions")
def get_contradictions():
    return _cache.get("last", {}).get("contradictions", [])

@app.get("/weaknesses")
def get_weaknesses():
    return _cache.get("last", {}).get("weaknesses", [])
