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

    pattern = re.compile(
        r"(?im)(?:^|\n)\s*.*?\b(facts|witness|testified|investigation)\b"
    )

    matches = list(pattern.finditer(text))

    if not matches:
        result["other"] = text
        return result

    def _to_key(kw: str) -> str:
        kw_lower = kw.lower()
        if kw_lower == "facts":
            return "facts"
        if kw_lower in ("witness", "testified"):
            return "witness"
        return "other"

    parts: dict[str, list[str]] = {"facts": [], "witness": [], "other": []}

    first_pos = matches[0].start()
    if first_pos > 0:
        prefix = text[:first_pos].strip()
        if prefix:
            parts["other"].append(prefix)

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


# Heading patterns found in legal documents, ordered from most to least specific
_HEADING_PATTERNS: list[tuple[int, re.Pattern]] = [
    # "ARTICLE 1", "ARTICLE I" — level 1
    (1, re.compile(r"^(?:ARTICLE|CHAPTER)\s+(?:\d+|[IVXLCDM]+)\b[^\n]*", re.MULTILINE | re.IGNORECASE)),
    # "Section 2.1", "Sec. 3" — level 2
    (2, re.compile(r"^(?:SECTION|SEC\.?)\s+\d+(?:\.\d+)*\b[^\n]*", re.MULTILINE | re.IGNORECASE)),
    # "I.", "II.", "III." — numbered Roman headings — level 2
    (2, re.compile(r"^[IVXLCDM]{1,6}\.\s+[A-Z][^\n]{0,80}$", re.MULTILINE)),
    # "1.", "2.", "12." — simple numbered clause — level 3
    (3, re.compile(r"^\d{1,2}\.\s+[A-Z][^\n]{0,80}$", re.MULTILINE)),
    # "FACTS", "BACKGROUND", "FINDINGS", "JUDGMENT", "ORDER" — all-caps standalone — level 2
    (2, re.compile(
        r"^(?:FACTS|BACKGROUND|FINDINGS?|JUDGMENT|ORDER|CONCLUSION|"
        r"EVIDENCE|WITNESSES?|INVESTIGATION|CHARGES?|GROUNDS?|DECISION)\s*$",
        re.MULTILINE,
    )),
]


def split_into_sections(text: str) -> list[Section]:
    """
    Split document text into logical sections based on headings and structure.

    Detects legal document headings (ARTICLE, SECTION, Roman numerals,
    numbered clauses, all-caps keywords) and returns them as ordered Section
    objects with title, content, level, and character positions.

    Args:
        text: Raw document text.

    Returns:
        List of Section objects in document order.
    """
    if not text.strip():
        return []

    # Collect all heading matches with their level
    heading_hits: list[tuple[int, int, int, str]] = []  # (start, end, level, title)

    for level, pattern in _HEADING_PATTERNS:
        for m in pattern.finditer(text):
            heading_hits.append((m.start(), m.end(), level, m.group(0).strip()))

    if not heading_hits:
        # No headings found — return whole document as one section
        return [
            Section(
                title="Document",
                content=text.strip(),
                level=0,
                start_char=0,
                end_char=len(text),
            )
        ]

    # Sort by position, remove overlapping matches (keep first found)
    heading_hits.sort(key=lambda x: x[0])
    deduplicated: list[tuple[int, int, int, str]] = []
    last_end = -1
    for start, end, level, title in heading_hits:
        if start >= last_end:
            deduplicated.append((start, end, level, title))
            last_end = end

    sections: list[Section] = []

    # Content before first heading
    first_start = deduplicated[0][0]
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            sections.append(
                Section(
                    title="Preamble",
                    content=preamble,
                    level=0,
                    start_char=0,
                    end_char=first_start,
                )
            )

    # Each heading → its content runs until the next heading
    for i, (start, end, level, title) in enumerate(deduplicated):
        content_start = end
        content_end = deduplicated[i + 1][0] if i + 1 < len(deduplicated) else len(text)
        content = text[content_start:content_end].strip()
        sections.append(
            Section(
                title=title,
                content=content,
                level=level,
                start_char=start,
                end_char=content_end,
            )
        )

    return sections


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