"""Cloud OCR adapter — stub for future cloud OCR API integration (Google Vision, Azure, etc.)."""
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class CloudOCRAdapter:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        import httpx

        if not self.is_available():
            return OCRResult(text="", confidence=0.0, pages=0, bbox_data=[])

        with open(file_path, "rb") as f:
            file_data = f.read()

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.endpoint}/ocr",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (file_path.name, file_data, mime_type)},
            )
            resp.raise_for_status()
            data = resp.json()

        return OCRResult(
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            pages=int(data.get("pages", 0)),
            bbox_data=data.get("bbox_data", []),
        )

    def is_available(self) -> bool:
        return bool(self.endpoint and self.api_key)
