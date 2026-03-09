import os
import io
from PIL import Image
import pytesseract
from app.ai.extractors.base import BaseExtractor

class ImageExtractor(BaseExtractor):
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    def extract(self, source, extension=None) -> dict:
        if extension is None:
            if isinstance(source, str):
                extension = os.path.splitext(source)[1].lower()
            else:
                raise ValueError("Extension must be provided for stream sources")

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {extension}")

        image = Image.open(source)
        ocr_text = pytesseract.image_to_string(image)

        return {
            "raw_text": ocr_text.strip(),
            "metadata": {
                "file_type": "image",
                "extension": extension
            }
        }
