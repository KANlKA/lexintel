"""
Section splitter for LexIntel document pipeline.

Splits legal documents into logical sections (e.g., Facts, Witness Statements,
Investigation, Findings) to improve event extraction accuracy and structure.
"""

import re
from dataclasses import dataclass
from typing import Any


def split_sections(text: str) -> dict[str, str]:
    """
    Split legal document text into logical sections using keyword detection.

    Uses rule-based matching for section headers: "facts", "witness",
    "testified", "investigation". Returns a dict with keys "facts", "witness",
    "other". If no section keywords are detected, the full text is returned
    under "other".

    Args:
        text: Raw legal document text.

    Returns:
        Dict with "facts", "witness", "other" keys containing section text.
    """
    result: dict[str, str] = {"facts": "", "witness": "", "other": ""}
    text = text.strip()
    if not text:
        return result

    # Find section boundaries: keyword at start of line (case-insensitive)
    # Map keywords to output keys: facts, witness, other
    # "witness" and "testified" -> witness; "investigation" -> other
    pattern = re.compile(
        r"(?im)(?:^|\n)\s*.*?\b(facts|witness|testified|investigation)\b"
    )

    matches = list(pattern.finditer(text))

    if not matches:
        result["other"] = text
        return result

    # Map keyword to output key
    def _to_key(kw: str) -> str:
        kw_lower = kw.lower()
        if kw_lower == "facts":
            return "facts"
        if kw_lower in ("witness", "testified"):
            return "witness"
        return "other"  # investigation

    parts: dict[str, list[str]] = {"facts": [], "witness": [], "other": []}

    # Content before first match goes to "other"
    first_pos = matches[0].start()
    if first_pos > 0:
        prefix = text[:first_pos].strip()
        if prefix:
            parts["other"].append(prefix)

    # Split content between markers
    for i, match in enumerate(matches):
        key = _to_key(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            parts[key].append(content)

    result = {
        "facts": "\n\n".join(parts["facts"]) if parts["facts"] else "",
        "witness": "\n\n".join(parts["witness"]) if parts["witness"] else "",
        "other": "\n\n".join(parts["other"]) if parts["other"] else "",
    }

    return result


@dataclass
class Section:
    """Represents a logical section of a legal document."""

    title: str
    content: str
    level: int
    start_char: int
    end_char: int


def split_into_sections(text: str) -> list[Section]:
    """
    Split document text into logical sections based on headings and structure.

    Uses patterns typical in legal documents (e.g., "Article 1", "Section 2.1",
    numbered clauses) to identify section boundaries.

    Args:
        text: Raw document text.

    Returns:
        List of Section objects in document order.
    """
    # Placeholder: implement heading detection and boundary logic
    if not text.strip():
        return []
    return [
        Section(
            title="",
            content=text.strip(),
            level=0,
            start_char=0,
            end_char=len(text),
        )
    ]


def split_into_chunks(
    text: str, max_chunk_size: int = 4096, overlap: int = 256
) -> list[dict[str, Any]]:
    """
    Split long text into overlapping chunks for processing by LLMs or NER models.

    Args:
        text: Document text to chunk.
        max_chunk_size: Maximum characters per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List of dicts with 'text', 'start', 'end', and 'index'.
    """
    chunks: list[dict[str, Any]] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        chunk_text = text[start:end]
        chunks.append({"text": chunk_text, "start": start, "end": end, "index": idx})
        start = end - overlap if end < len(text) else len(text)
        idx += 1
    return chunks
