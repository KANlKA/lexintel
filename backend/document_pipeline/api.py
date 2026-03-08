"""
FastAPI service for LexIntel document pipeline.

Exposes the document processing pipeline as HTTP endpoints so the
reasoning engine and frontend can call it without importing Python modules.

Run with:
    cd LexIntel/backend
    uvicorn document_pipeline.api:app --reload --port 8001

Endpoints:
    GET  /health                — health check
    POST /process/dataset       — process N cases from the JSONL dataset
    POST /process/pdf           — process a single PDF (upload)
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LexIntel Document Pipeline API",
    description="Processes legal documents into structured events.",
    version="1.0.0",
)

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


@app.on_event("startup")
def startup_event():
    """Initialize database schema on startup. Safe to run multiple times."""
    try:
        from document_pipeline.database.postgres_client import initialize_schema
        initialize_schema()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(
            "Database schema init skipped: %s. "
            "Set DATABASE_URL in .env to enable persistence.", e
        )


# ── Request / Response models ────────────────────────────────────────────────

class DatasetProcessRequest(BaseModel):
    dataset_path: str = "../dataset/text.data.jsonl"
    limit: int = 5


class ProcessResponse(BaseModel):
    status: str
    events_extracted: int
    events: list[dict[str, Any]]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {
        "service": "LexIntel Document Pipeline API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/health", "/process/dataset", "/process/pdf"],
    }


@app.get("/health")
def health() -> dict:
    return {
        "service": "LexIntel Document Pipeline API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/health", "/process/dataset", "/process/pdf"],
    }


@app.post("/process/dataset", response_model=ProcessResponse)
def process_dataset_endpoint(request: DatasetProcessRequest) -> ProcessResponse:
    """
    Process cases from the JSONL dataset file.

    Example body:
        { "dataset_path": "../dataset/text.data.jsonl", "limit": 5 }
    """
    from document_pipeline.pipeline import process_dataset

    path = Path(request.dataset_path)
    if not path.exists():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / request.dataset_path

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset not found: {request.dataset_path}. "
                "Make sure text.data.jsonl is in LexIntel/dataset/"
            ),
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

    Use curl to test (Swagger UI has a known bug with file uploads):
        curl -X POST http://localhost:8001/process/pdf \\
             -H "accept: application/json" \\
             -F "file=@/path/to/document.pdf"
    """
    from document_pipeline.pipeline import process_document

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

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
        os.unlink(tmp_path)

    return ProcessResponse(
        status="success",
        events_extracted=len(events),
        events=events,
    )