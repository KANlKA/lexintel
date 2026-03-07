"""
Dataset loader for LexIntel document pipeline.

Loads document datasets (e.g., JSONL, JSON) containing legal documents
for batch processing through the extraction pipeline.

Supports the CAP (Case Law Access Project) dataset format.
"""

import json
from pathlib import Path
from typing import Iterator


def load_cases(file_path: str, limit: int = 100) -> list[dict[str, str]]:
    """
    Load cases from a CAP dataset JSONL file.

    Extracts case narrative text from casebody.data.opinions[0].text.
    Returns structured objects with case_id and text.

    Args:
        file_path: Path to the text.data.jsonl file.
        limit: Maximum number of cases to load (default 100).

    Returns:
        List of dicts: [{"case_id": str, "text": str}, ...]
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"Dataset file not found: {path}"
        raise FileNotFoundError(msg)

    cases: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if len(cases) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError:
                continue

            case_id = _get_case_id(case)
            text = _get_opinion_text(case)

            if text:  # only include cases with extractable text
                cases.append({"case_id": case_id, "text": text})

    return cases


def _get_case_id(case: dict) -> str:
    """Safely extract case ID. Returns empty string if missing."""
    case_id = case.get("id")
    if case_id is not None:
        return str(case_id)
    return case.get("name_abbreviation", "") or ""


def _get_opinion_text(case: dict) -> str:
    """Safely extract opinion text from casebody.data.opinions[0].text."""
    try:
        casebody = case.get("casebody")
        if not isinstance(casebody, dict):
            return ""
        data = casebody.get("data")
        if not isinstance(data, dict):
            return ""
        opinions = data.get("opinions")
        if not isinstance(opinions, list) or len(opinions) == 0:
            return ""
        first_opinion = opinions[0]
        if not isinstance(first_opinion, dict):
            return ""
        text = first_opinion.get("text")
        return str(text) if text is not None else ""
    except (TypeError, KeyError, IndexError):
        return ""


def load_jsonl_dataset(file_path: Path | str) -> Iterator[dict]:
    """
    Load documents from a JSONL (JSON Lines) file.

    Each line is expected to be a valid JSON object representing a document
    with fields such as 'id', 'text', 'metadata', etc.

    Args:
        file_path: Path to the JSONL file.

    Yields:
        Document dicts, one per line in the file.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"Dataset file not found: {path}"
        raise FileNotFoundError(msg)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_dataset(file_path: Path | str) -> list[dict]:
    """
    Load all documents from a dataset file into memory.

    Supports JSONL format. Extend for other formats (JSON, CSV) as needed.

    Args:
        file_path: Path to the dataset file.

    Returns:
        List of document dictionaries.
    """
    return list(load_jsonl_dataset(file_path))
