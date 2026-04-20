"""
Dataset loader for LexIntel document pipeline.

Loads document datasets (e.g., JSONL, JSON) containing legal documents
for batch processing through the extraction pipeline.

Supports:
- CAP dataset format
- Simple evaluation dataset format with 'case_id' and 'text'
"""

import json
from pathlib import Path
from typing import Iterator


def load_cases(file_path: str, limit: int = 100) -> list[dict[str, str]]:
    """
    Load cases from dataset JSONL file.

    Supports both:
      1) CAP dataset format
      2) Simple evaluation dataset format

    Returns:
        List of dicts:
        [
            {
                "case_id": str,
                "text": str
            }
        ]
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

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
                print("Skipping invalid JSON line")
                continue

            case_id = _get_case_id(case)
            text = _get_opinion_text(case)

            if text:
                cases.append(
                    {
                        "case_id": case_id,
                        "text": text,
                    }
                )

    return cases


def _get_case_id(case: dict) -> str:
    """
    Safely extract case ID.

    Supports:
      - case_id
      - id
      - name_abbreviation fallback
    """

    if "case_id" in case:
        return str(case["case_id"])

    if "id" in case:
        return str(case["id"])

    return case.get("name_abbreviation", "") or ""


def _get_opinion_text(case: dict) -> str:
    """
    Safely extract opinion text.

    Supports:

    1) Simple dataset format:
        {
            "case_id": "...",
            "text": "..."
        }

    2) CAP dataset format:
        casebody.data.opinions[0].text
    """

    # -----------------------------
    # NEW: simple dataset support
    # -----------------------------

    if "text" in case:

        text = case.get("text")

        if text:
            return str(text)

    # -----------------------------
    # Existing CAP dataset logic
    # -----------------------------

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

        if text:
            return str(text)

        return ""

    except (TypeError, KeyError, IndexError):

        return ""


def load_jsonl_dataset(file_path: Path | str) -> Iterator[dict]:
    """
    Load documents from a JSONL file.

    Each line is expected to be a valid JSON object.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with path.open(encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if line:
                yield json.loads(line)


def load_dataset(file_path: Path | str) -> list[dict]:
    """
    Load entire dataset into memory.
    """

    return list(load_jsonl_dataset(file_path))