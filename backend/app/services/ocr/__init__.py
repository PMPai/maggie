"""OCR adapter factory."""
from app.services.ocr.protocol import OCRResult, OCRAdapter
from app.services.ocr.stub import StubOCRAdapter


def get_ocr_adapter(settings) -> OCRAdapter:
    provider = settings.OCR_PROVIDER
    if provider == "tesseract":
        from app.services.ocr.tesseract import TesseractAdapter
        return TesseractAdapter(lang=settings.OCR_TESSERACT_LANG)
    elif provider == "cloud":
        from app.services.ocr.cloud import CloudOCRAdapter
        return CloudOCRAdapter(
            endpoint=settings.OCR_CLOUD_ENDPOINT,
            api_key=settings.OCR_CLOUD_API_KEY,
        )
    return StubOCRAdapter()


__all__ = ["OCRResult", "OCRAdapter", "StubOCRAdapter", "get_ocr_adapter"]
