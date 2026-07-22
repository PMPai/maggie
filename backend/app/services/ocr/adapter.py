"""OCR adapter — graceful degradation when no OCR engine available.
Phase 3: stub implementation. Real OCR (Tesseract/cloud) can be plugged in later."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int
    bbox_data: list  # list of {text, bbox, page} dicts


class OCRAdapter:
    """Stub OCR adapter — returns empty result.
    Replace with Tesseract/PaddleOCR/cloud API when available."""

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        return OCRResult(text="", confidence=0.0, pages=0, bbox_data=[])

    def is_available(self) -> bool:
        return False


# Singleton
ocr_adapter = OCRAdapter()
