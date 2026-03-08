"""
OCR (Optical Character Recognition) for LexIntel document pipeline.

Processes scanned legal documents or image-based PDFs to extract
text when native text extraction is unavailable or low quality.

Cross-platform: auto-detects Tesseract on Windows, Mac, and Linux.
"""

import logging
import platform
import shutil
from pathlib import Path
from typing import Any

from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


def _configure_tesseract() -> None:
    """
    Auto-detect and configure Tesseract path for the current OS.

    Priority:
      1. TESSERACT_CMD environment variable (user override)
      2. System PATH (works on Linux / Mac after `apt install` or `brew install`)
      3. Known Windows default install location
    
    Raises:
        EnvironmentError: If Tesseract cannot be found on this system.
    """
    import os

    # 1. Explicit env override wins
    env_path = os.getenv("TESSERACT_CMD")
    if env_path:
        pytesseract.pytesseract.tesseract_cmd = env_path
        logger.debug("Tesseract configured from TESSERACT_CMD env: %s", env_path)
        return

    # 2. Available on PATH (Linux / Mac standard installs)
    path_result = shutil.which("tesseract")
    if path_result:
        pytesseract.pytesseract.tesseract_cmd = path_result
        logger.debug("Tesseract found on PATH: %s", path_result)
        return

    # 3. Windows default install paths
    if platform.system() == "Windows":
        windows_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(
                os.getenv("USERNAME", "")
            ),
        ]
        for candidate in windows_candidates:
            if Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                logger.debug("Tesseract found at Windows path: %s", candidate)
                return

    # 4. Mac Homebrew fallback
    if platform.system() == "Darwin":
        brew_path = "/usr/local/bin/tesseract"
        if Path(brew_path).exists():
            pytesseract.pytesseract.tesseract_cmd = brew_path
            return
        brew_arm_path = "/opt/homebrew/bin/tesseract"
        if Path(brew_arm_path).exists():
            pytesseract.pytesseract.tesseract_cmd = brew_arm_path
            return

    raise EnvironmentError(
        "Tesseract not found. Install it for your OS:\n"
        "  Linux:   sudo apt install tesseract-ocr\n"
        "  Mac:     brew install tesseract\n"
        "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "Or set TESSERACT_CMD=/path/to/tesseract in your .env file."
    )


# Configure once at import time
try:
    _configure_tesseract()
except EnvironmentError as _e:
    logger.warning("OCR unavailable: %s", _e)


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from a scanned legal document image using Tesseract OCR.

    Args:
        image_path: Path to the image file (PNG, JPEG, TIFF, etc.).

    Returns:
        Extracted text from the image. Empty string if extraction fails.
    """
    path = Path(image_path)
    if not path.exists():
        msg = f"Image file not found: {path}"
        raise FileNotFoundError(msg)

    image = Image.open(path)
    try:
        text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as e:
        raise EnvironmentError(
            "Tesseract not installed or not on PATH. "
            "See install instructions in ocr.py."
        ) from e

    return text.strip() if text else ""


def run_ocr(file_path: Path | str) -> str:
    """
    Run OCR on an image or PDF to extract text.

    For image files, delegates to extract_text_from_image.
    PDFs require pdf2image (pip install pdf2image) for page conversion.

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
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}:
        return extract_text_from_image(str(path))

    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_path  # pip install pdf2image
        except ImportError:
            logger.warning("pdf2image not installed. Run: pip install pdf2image")
            return ""
        pages = convert_from_path(str(path))
        page_texts = []
        for page_img in pages:
            text = pytesseract.image_to_string(page_img)
            if text and text.strip():
                page_texts.append(text.strip())
        return "\n\n".join(page_texts)

    logger.warning("Unsupported file type for OCR: %s", suffix)
    return ""


def run_ocr_with_confidence(file_path: Path | str) -> dict[str, Any]:
    """
    Run OCR and return text with per-region confidence scores.

    Uses Tesseract's data output to calculate mean word confidence.

    Args:
        file_path: Path to the image or PDF file.

    Returns:
        Dict with 'text' (str), 'confidence' (float 0-1), and 'regions' (list).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
        image = Image.open(path)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        confidences = [
            int(c) for c in data["conf"]
            if str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

        text = pytesseract.image_to_string(image).strip()
        regions = [
            {
                "text": data["text"][i],
                "confidence": int(data["conf"][i]) / 100.0,
                "left": data["left"][i],
                "top": data["top"][i],
            }
            for i in range(len(data["text"]))
            if data["text"][i].strip()
        ]

        return {"text": text, "confidence": round(mean_conf, 3), "regions": regions}

    # Fallback for PDFs and other types
    text = run_ocr(file_path)
    return {"text": text, "confidence": 0.0, "regions": []}