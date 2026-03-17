"""
FastAPI service for LexIntel document pipeline.

Run with:
    cd LexIntel/backend
    uvicorn document_pipeline.api:app --reload --port 8001
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, List

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
    try:
        from document_pipeline.database.postgres_client import initialize_schema
        initialize_schema()
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning("DB init skipped: %s", e)


# ── Models ───────────────────────────────────────────────────────────────────

class DatasetProcessRequest(BaseModel):
    dataset_path: str = "../dataset/text.data.jsonl"
    limit: int = 5


class ProcessResponse(BaseModel):
    status: str
    events_extracted: int
    events: list[dict[str, Any]]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "service": "LexIntel Document Pipeline API",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/health", "/process/dataset", "/process/pdf", "/process/case"],
    }


@app.post("/process/dataset", response_model=ProcessResponse)
def process_dataset_endpoint(request: DatasetProcessRequest) -> ProcessResponse:
    from document_pipeline.pipeline import process_dataset

    path = Path(request.dataset_path)
    if not path.exists():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / request.dataset_path

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {request.dataset_path}.",
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
    Process a single uploaded PDF.
    Test with curl:
        curl -X POST http://localhost:8001/process/pdf -F "file=@/path/to/doc.pdf"
    """
    from document_pipeline.pipeline import process_document

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

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

    return ProcessResponse(status="success", events_extracted=len(events), events=events)


@app.post("/process/case", response_model=ProcessResponse)
async def process_case_endpoint(files: List[UploadFile] = File(...)) -> ProcessResponse:
    """
    Process multiple documents as a single case workspace.

    All uploaded files are processed individually and their events are
    combined into one flat list. Each event is tagged with the original
    filename as source_document.

    Accepts: PDF, PNG, JPG, JPEG, TXT
    """
    from document_pipeline.pipeline import process_document
    from document_pipeline.preprocessing.ocr import extract_text_from_image
    from document_pipeline.extraction.event_extractor import extract_events

    ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
    all_events: list[dict[str, Any]] = []
    processed_files: list[str] = []
    failed_files: list[str] = []

    for file in files:
        filename = file.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED:
            logger.warning("Skipping unsupported file type: %s", filename)
            continue

        content = await file.read()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if suffix == ".pdf":
                events = process_document(tmp_path)

            elif suffix in {".png", ".jpg", ".jpeg"}:
                # OCR the image then extract events
                text = extract_text_from_image(tmp_path)
                if text:
                    event_objs = extract_events(text, source_document=filename)
                    events = [e.model_dump() for e in event_objs]
                else:
                    events = []

            elif suffix == ".txt":
                text = content.decode("utf-8", errors="ignore")
                event_objs = extract_events(text, source_document=filename)
                events = [e.model_dump() for e in event_objs]

            else:
                events = []

            # Tag each event with the original uploaded filename
            for e in events:
                e["source_document"] = filename

            all_events.extend(events)
            processed_files.append(filename)
            logger.info("Processed %s -> %d events", filename, len(events))

        except Exception as e:
            logger.error("Failed processing %s: %s", filename, e)
            failed_files.append(filename)
        finally:
            os.unlink(tmp_path)

    if not all_events and not processed_files:
        raise HTTPException(
            status_code=422,
            detail=f"No events extracted. Failed files: {failed_files}",
        )

    logger.info(
        "Case processed: %d files, %d total events, %d failed",
        len(processed_files), len(all_events), len(failed_files),
    )

    return ProcessResponse(
        status="success",
        events_extracted=len(all_events),
        events=all_events,
    )
