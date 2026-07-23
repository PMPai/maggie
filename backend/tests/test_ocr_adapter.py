"""OCR adapter tests — protocol, stub, factory."""
import pytest
from pathlib import Path
from app.services.ocr.protocol import OCRResult
from app.services.ocr.stub import StubOCRAdapter


def test_ocr_result_dataclass():
    result = OCRResult(text="hello", confidence=0.9, pages=1, bbox_data=[])
    assert result.text == "hello"
    assert result.confidence == 0.9
    assert result.pages == 1
    assert result.bbox_data == []


@pytest.mark.asyncio
async def test_stub_adapter_returns_empty():
    adapter = StubOCRAdapter()
    result = await adapter.extract(Path("/tmp/fake.pdf"))
    assert result.text == ""
    assert result.confidence == 0.0
    assert result.pages == 0
    assert result.bbox_data == []


def test_stub_adapter_not_available():
    adapter = StubOCRAdapter()
    assert adapter.is_available() is False


def test_get_ocr_adapter_returns_stub_by_default():
    from app.services.ocr import get_ocr_adapter
    from app.config import get_settings
    settings = get_settings()
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, StubOCRAdapter)


def test_get_ocr_adapter_returns_tesseract_when_configured():
    from app.services.ocr import get_ocr_adapter
    from app.services.ocr.tesseract import TesseractAdapter
    from app.config import Settings
    settings = Settings(OCR_PROVIDER="tesseract")
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, TesseractAdapter)


def test_get_ocr_adapter_returns_cloud_when_configured():
    from app.services.ocr import get_ocr_adapter
    from app.services.ocr.cloud import CloudOCRAdapter
    from app.config import Settings
    settings = Settings(OCR_PROVIDER="cloud", OCR_CLOUD_ENDPOINT="https://ocr.example.com", OCR_CLOUD_API_KEY="key")
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, CloudOCRAdapter)

