import pytesseract
from PIL import Image
from pdf2image import convert_from_path

def ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)

def ocr_pdf(pdf_path: str) -> str:
    pages = convert_from_path(pdf_path)
    return "\n".join(ocr_image(p) for p in pages)
