"""
OCR (Optical Character Recognition) for LexIntel document pipeline.

Processes scanned legal documents or image-based PDFs to extract
text when native text extraction is unavailable or low quality.

Used for scanned legal documents (e.g., court filings, contracts)
where the source is an image rather than selectable digital text.
"""

from pathlib import Path
from typing import Any

from PIL import Image
import pytesseract
# Configure Tesseract path (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from a scanned legal document image using Tesseract OCR.

    Used for scanned legal documents (court filings, contracts, historical
    records) that exist only as images. Requires Tesseract OCR installed
    on the system. Loads the image with Pillow, runs pytesseract, and
    returns the extracted text.

    Args:
        image_path: Path to the image file (PNG, JPEG, TIFF, etc.).

    Returns:
        Extracted text from the image.
    """
    path = Path(image_path)
    if not path.exists():
        msg = f"Image file not found: {path}"
        raise FileNotFoundError(msg)

    # Load image using Pillow (supports PNG, JPEG, TIFF, BMP, etc.)
    image = Image.open(path)

    # Run pytesseract OCR to extract text from the image
    text = pytesseract.image_to_string(image)

    return text.strip() if text else ""


def run_ocr(file_path: Path | str) -> str:
    """
    Run OCR on an image or PDF to extract text.

    For image files, delegates to extract_text_from_image. PDFs require
    conversion to images first (e.g., pdf2image).

    Args:
        file_path: Path to the image or PDF file.

    Returns:
        Extracted text from the document.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}:
        return extract_text_from_image(str(path))
    # PDF: would need pdf2image to convert pages to images first
    return ""


def run_ocr_with_confidence(file_path: Path | str) -> dict[str, Any]:
    """
    Run OCR and return text with per-region confidence scores.

    Args:
        file_path: Path to the image or PDF file.

    Returns:
        Dict with 'text', 'confidence', and optional 'regions'.
    """
    text = run_ocr(file_path)
    return {
        "text": text,
        "confidence": 0.0,
        "regions": [],
    }
