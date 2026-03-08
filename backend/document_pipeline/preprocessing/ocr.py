"""
OCR for LexIntel document pipeline. Cross-platform Tesseract detection.

If you have a local tesseract.exe, set this in your .env:
    TESSERACT_CMD=C:/path/to/tesseract.exe

Otherwise it auto-detects from PATH or known install locations.
"""

import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


def _configure_tesseract() -> None:
    """
    Auto-detect Tesseract. Priority:
      1. TESSERACT_CMD env var  (set this in .env for your local .exe)
      2. System PATH
      3. Windows default install locations
      4. Mac Homebrew locations
    """
    # 1. Env override — use this for your local tesseract.exe
    env_path = os.getenv("TESSERACT_CMD")
    if env_path:
        pytesseract.pytesseract.tesseract_cmd = env_path
        logger.debug("Tesseract configured from TESSERACT_CMD: %s", env_path)
        return

    # 2. System PATH (Linux/Mac standard)
    path_result = shutil.which("tesseract")
    if path_result:
        pytesseract.pytesseract.tesseract_cmd = path_result
        logger.debug("Tesseract found on PATH: %s", path_result)
        return

    # 3. Windows known locations
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(
                os.getenv("LOCALAPPDATA", ""),
                r"Programs\Tesseract-OCR\tesseract.exe"
            ),
            # Check same folder as this file (if user dropped tesseract.exe nearby)
            str(Path(__file__).resolve().parent.parent.parent / "tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                logger.debug("Tesseract found at: %s", candidate)
                return

    # 4. Mac Homebrew
    if platform.system() == "Darwin":
        for brew_path in ["/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract"]:
            if Path(brew_path).exists():
                pytesseract.pytesseract.tesseract_cmd = brew_path
                return

    raise EnvironmentError(
        "Tesseract not found.\n"
        "Option 1 — Add to .env:  TESSERACT_CMD=C:/full/path/to/tesseract.exe\n"
        "Option 2 — Install it:\n"
        "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "  Mac:     brew install tesseract\n"
        "  Linux:   sudo apt install tesseract-ocr"
    )


try:
    _configure_tesseract()
except EnvironmentError as _e:
    logger.warning("OCR unavailable: %s", _e)


def extract_text_from_image(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    image = Image.open(path)
    try:
        text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as e:
        raise EnvironmentError(
            "Tesseract not found. Set TESSERACT_CMD in .env to your tesseract.exe path."
        ) from e
    return text.strip() if text else ""


def run_ocr(file_path: Path | str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}:
        return extract_text_from_image(str(path))
    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.warning("pdf2image not installed: pip install pdf2image")
            return ""
        pages = convert_from_path(str(path))
        return "\n\n".join(
            pytesseract.image_to_string(p).strip()
            for p in pages
            if pytesseract.image_to_string(p).strip()
        )
    return ""


def run_ocr_with_confidence(file_path: Path | str) -> dict[str, Any]:
    path = Path(file_path)
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
        image = Image.open(path)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidences = [
            int(c) for c in data["conf"]
            if str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        text = pytesseract.image_to_string(image).strip()
        return {"text": text, "confidence": round(mean_conf, 3), "regions": []}
    return {"text": run_ocr(file_path), "confidence": 0.0, "regions": []}