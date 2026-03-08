"""
FastAPI service for LexIntel document pipeline.

Exposes the document processing pipeline as HTTP endpoints so the
reasoning engine and frontend can call it without importing Python modules.

Run with:
    cd LexIntel/backend
    uvicorn document_pipeline.api:app --reload --port 8001

Endpoints:
    POST /process/dataset   — process N cases from the JSONL dataset
    POST /process/pdf       — process a single PDF (upload)
    GET  /health            — health check
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from document_pipeline.pipeline import process_dataset, process_document

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LexIntel Document Pipeline API",
    description="Processes legal documents into structured events.",
    version="1.0.0",
)

# Allow Next.js frontend (port 3000) and reasoning engine (port 8000) to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

class DatasetProcessRequest(BaseModel):
    """Request body for dataset processing."""
    dataset_path: str = "../dataset/text.data.jsonl"
    limit: int = 5

class EventResponse(BaseModel):
    """A single structured event."""
    event_id: str
    actor: str
    action: str
    time: str | None
    location: str | None
    source_document: str
    confidence: float

class ProcessResponse(BaseModel):
    """Response from any processing endpoint."""
    status: str
    events_extracted: int
    events: list[dict[str, Any]]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "service": "LexIntel Document Pipeline",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/process/dataset", "/process/pdf"],
    }


@app.post("/process/dataset", response_model=ProcessResponse)
def process_dataset_endpoint(request: DatasetProcessRequest) -> ProcessResponse:
    """
    Process cases from the JSONL dataset file.

    The dataset_path can be absolute or relative to LexIntel/backend.
    Returns all extracted events as structured JSON.

    Example body:
        { "dataset_path": "../dataset/text.data.jsonl", "limit": 5 }
    """
    path = Path(request.dataset_path)

    # Try resolving relative to backend folder
    if not path.exists():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / request.dataset_path

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {request.dataset_path}. "
                   f"Make sure text.data.jsonl is in LexIntel/dataset/"
        )

    try:
        events = process_dataset(str(path), limit=request.limit)
    except Exception as e:
        logger.error("Dataset processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return ProcessResponse(
        status="success",
        events_extracted=len(events),
        events=events,
    )


@app.post("/process/pdf", response_model=ProcessResponse)
async def process_pdf_endpoint(file: UploadFile = File(...)) -> ProcessResponse:
    """
    Process a single uploaded PDF file.

    Upload a PDF legal document and receive extracted structured events.
    Accepts multipart/form-data with field name 'file'.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Upload a .pdf file."
        )

    # Save to a temp file (pdfplumber needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        events = process_document(tmp_path)
    except Exception as e:
        logger.error("PDF processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)  # clean up temp file

    return ProcessResponse(
        status="success",
        events_extracted=len(events),
        events=events,
    )