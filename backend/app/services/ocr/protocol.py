"""OCR adapter protocol and result dataclass."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int
    bbox_data: list[dict]


class OCRAdapter(Protocol):
    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult: ...
    def is_available(self) -> bool: ...
