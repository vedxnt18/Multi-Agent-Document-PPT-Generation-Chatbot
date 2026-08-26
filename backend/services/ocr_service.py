"""
backend/services/ocr_service.py

OCR service using Tesseract (via pytesseract). Handles:
- image files (PNG/JPG/JPEG)
- individual rendered pages from a scanned PDF (passed in as PIL Images
  by document_service.py)

Design principle: never crash the whole pipeline if Tesseract isn't
installed. Instead, return a clearly-flagged failure that callers can
surface as a warning (per the assignment's error-handling requirement:
"Unable to extract text from this page.").
"""
import logging
from dataclasses import dataclass
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    text: str
    success: bool
    confidence: Optional[float] = None  # average word confidence, 0-1
    error: Optional[str] = None


class OCRService:
    """
    Wraps pytesseract. Checks Tesseract availability once and caches the
    result so we don't repeatedly attempt (and log) a failing call.
    """

    def __init__(self):
        self._checked = False
        self._available = False
        self._check_error: Optional[str] = None

    def _ensure_checked(self) -> None:
        if self._checked:
            return
        self._checked = True
        try:
            import pytesseract  # noqa: F401
            pytesseract.get_tesseract_version()
            self._available = True
        except Exception as e:  # pytesseract raises TesseractNotFoundError or similar
            self._available = False
            self._check_error = (
                "Tesseract OCR engine not found on this system. "
                "Install it (see README OCR setup section) and ensure it's on PATH, "
                f"or set pytesseract.pytesseract.tesseract_cmd manually. Details: {e}"
            )
            logger.warning(self._check_error)

    @property
    def available(self) -> bool:
        self._ensure_checked()
        return self._available

    def extract_text_from_image(self, image: Image.Image) -> OCRResult:
        """Run OCR on a single PIL Image. Returns text + word-level average confidence."""
        self._ensure_checked()
        if not self._available:
            return OCRResult(text="", success=False, error=self._check_error)

        import pytesseract
        from pytesseract import Output

        try:
            data = pytesseract.image_to_data(image, output_type=Output.DICT)
            words = []
            confidences = []
            for i, word in enumerate(data["text"]):
                if word.strip():
                    words.append(word)
                    conf = data["conf"][i]
                    # pytesseract returns -1 for non-text regions; ignore those
                    if isinstance(conf, (int, float)) and conf >= 0:
                        confidences.append(float(conf))

            text = " ".join(words)
            avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else None

            if not text.strip():
                return OCRResult(
                    text="",
                    success=False,
                    error="OCR ran but found no text in this image/page.",
                )

            return OCRResult(text=text, success=True, confidence=avg_conf)

        except Exception as e:
            logger.exception("OCR extraction failed")
            return OCRResult(text="", success=False, error=f"OCR extraction failed: {e}")


# Single shared instance — availability check is cached after first call.
ocr_service = OCRService()
