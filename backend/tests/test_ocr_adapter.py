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


def test_cloud_adapter_not_available_without_config():
    from app.services.ocr.cloud import CloudOCRAdapter
    adapter = CloudOCRAdapter(endpoint="", api_key="")
    assert adapter.is_available() is False


def test_cloud_adapter_available_with_config():
    from app.services.ocr.cloud import CloudOCRAdapter
    adapter = CloudOCRAdapter(endpoint="https://ocr.example.com", api_key="key123")
    assert adapter.is_available() is True


def test_get_ocr_adapter_returns_cloud_when_configured():
    from app.services.ocr import get_ocr_adapter
    from app.services.ocr.cloud import CloudOCRAdapter
    from app.config import Settings
    settings = Settings(OCR_PROVIDER="cloud", OCR_CLOUD_ENDPOINT="https://ocr.example.com", OCR_CLOUD_API_KEY="key")
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, CloudOCRAdapter)


def test_tesseract_adapter_available_check():
    """TesseractAdapter.is_available() checks for tesseract binary."""
    from app.services.ocr.tesseract import TesseractAdapter
    adapter = TesseractAdapter(lang="chi_sim+eng")
    assert isinstance(adapter.is_available(), bool)


@pytest.mark.skipif(
    not __import__("shutil").which("tesseract"),
    reason="tesseract not installed",
)
@pytest.mark.asyncio
async def test_tesseract_extract_from_image(tmp_path):
    """Real OCR test — only runs when tesseract is available."""
    from PIL import Image, ImageDraw
    from app.services.ocr.tesseract import TesseractAdapter

    img = Image.new("RGB", (200, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Hello 123", fill="black")
    img_path = tmp_path / "test.png"
    img.save(img_path)

    adapter = TesseractAdapter(lang="eng")
    result = await adapter.extract(img_path, mime_type="image/png")
    assert result.pages == 1
    assert "Hello" in result.text or "123" in result.text

