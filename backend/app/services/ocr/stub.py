"""Stub OCR adapter — returns empty result when OCR is unavailable."""
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class StubOCRAdapter:
    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        return OCRResult(text="", confidence=0.0, pages=0, bbox_data=[])

    def is_available(self) -> bool:
        return False
