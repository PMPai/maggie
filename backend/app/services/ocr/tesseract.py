"""Tesseract OCR adapter — self-hosted OCR using pytesseract."""
import shutil
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class TesseractAdapter:
    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        import pytesseract
        from PIL import Image

        pages_text = []
        bbox_data = []

        if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path
            images = convert_from_path(str(file_path))
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img, lang=self.lang)
                data = pytesseract.image_to_data(img, lang=self.lang, output_type=pytesseract.Output.DICT)
                pages_text.append(text)
                for j in range(len(data["text"])):
                    if data["text"][j].strip():
                        bbox_data.append({
                            "text": data["text"][j],
                            "bbox": (data["left"][j], data["top"][j], data["width"][j], data["height"][j]),
                            "page": i,
                            "confidence": data["conf"][j],
                        })
            full_text = "\n".join(pages_text)
            pages = len(images)
        else:
            img = Image.open(file_path)
            full_text = pytesseract.image_to_string(img, lang=self.lang)
            data = pytesseract.image_to_data(img, lang=self.lang, output_type=pytesseract.Output.DICT)
            for j in range(len(data["text"])):
                if data["text"][j].strip():
                    bbox_data.append({
                        "text": data["text"][j],
                        "bbox": (data["left"][j], data["top"][j], data["width"][j], data["height"][j]),
                        "page": 0,
                        "confidence": data["conf"][j],
                    })
            pages = 1

        confidences = [b["confidence"] for b in bbox_data if b["confidence"] > 0]
        avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        return OCRResult(text=full_text.strip(), confidence=avg_conf, pages=pages, bbox_data=bbox_data)

    def is_available(self) -> bool:
        return shutil.which("tesseract") is not None
