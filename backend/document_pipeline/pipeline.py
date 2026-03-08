

from typing import Any

from document_pipeline.extraction.event_extractor import extract_events
"""
Main pipeline for LexIntel document processing.

Orchestrates the full document processing pipeline: load input, split sections,
extract entities, extract events, and return structured event dictionaries.
"""
from document_pipeline.extraction.ner import extract_entities
from document_pipeline.ingestion.dataset_loader import load_cases
from document_pipeline.ingestion.pdf_loader import extract_pdf_text
from document_pipeline.preprocessing.section_splitter import split_sections


def process_document(file_path: str) -> list[dict[str, Any]]:
    """
    Process a single PDF document through the full pipeline.

    Steps: extract PDF text → split sections → extract entities → extract events.
    Returns structured events as dictionaries.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of event dicts (from model_dump()).
    """
    print(f"[Pipeline] Loading PDF: {file_path}")
    text = extract_pdf_text(file_path)

    print("[Pipeline] Splitting into sections")
    sections = split_sections(text)

    # Combine section content for entity/event extraction
    section_texts = [
        sections["facts"],
        sections["witness"],
        sections["other"],
    ]
    combined_text = "\n\n".join(t for t in section_texts if t)

    print("[Pipeline] Extracting entities")
    entities = extract_entities(combined_text)
    print(f"[Pipeline] Entities found: persons={len(entities['persons'])}, locations={len(entities['locations'])}, dates={len(entities['dates'])}, times={len(entities['times'])}")

    print("[Pipeline] Extracting events")
    event_objs = extract_events(
        combined_text,
        source_document=file_path,
    )
    print(f"[Pipeline] Extracted {len(event_objs)} events")

    return [e.model_dump() for e in event_objs]


def process_dataset(file_path: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    Process a dataset of cases through the pipeline.

    Loads cases from the dataset, extracts events for each case, and returns
    a flat list of structured events as dictionaries.

    Args:
        file_path: Path to the dataset file (e.g., text.data.jsonl).
        limit: Maximum number of cases to process (default 100).

    Returns:
        List of event dicts (from model_dump()).
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
        print(f"[Pipeline] Entities: persons={len(entities['persons'])}, locations={len(entities['locations'])}, dates={len(entities['dates'])}, times={len(entities['times'])}")

        print("[Pipeline] Extracting events")
        event_objs = extract_events(
            combined_text,
            source_document=str(case_id),
        )
        all_events.extend(e.model_dump() for e in event_objs)
        print(f"[Pipeline] Extracted {len(event_objs)} events from case {case_id}")

    print(f"[Pipeline] Total events extracted: {len(all_events)}")
    return all_events
