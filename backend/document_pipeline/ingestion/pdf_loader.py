"""
PDF loader for LexIntel document pipeline.

Loads legal documents from PDF files and extracts text content
for downstream preprocessing and event extraction.

Uses pdfplumber for text extraction.
"""

from pathlib import Path
from typing import Any

import pdfplumber


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from a PDF legal document using pdfplumber.

    Opens the PDF, iterates through all pages, extracts text, and returns
    a single combined string. Empty pages are ignored. Output is cleaned
    (normalized whitespace, stripped).

    Args:
        file_path: Path to the PDF file.

    Returns:
        Clean concatenated text from all non-empty pages.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

    page_texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and (clean := text.strip()):
                page_texts.append(clean)

    return _clean_text("\n\n".join(page_texts))


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove excessive newlines."""
    if not text:
        return ""
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def load_pdf(file_path: Path | str) -> dict[str, Any]:
    """
    Load a PDF file and extract its text content and metadata.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Dict with 'text' (str), 'metadata' (dict), and 'pages' (list of page texts).
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

    page_texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and (clean := text.strip()):
                page_texts.append(clean)

    full_text = _clean_text("\n\n".join(page_texts))
    return {
        "text": full_text,
        "metadata": {"source": str(path), "filename": path.name},
        "pages": page_texts,
    }


def extract_text_from_pdf(file_path: Path | str) -> str:
    """
    Extract raw text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Concatenated text content from all pages.
    """
    return extract_pdf_text(str(file_path))
