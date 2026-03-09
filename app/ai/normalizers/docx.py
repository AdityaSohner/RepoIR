from .common import basic_clean

def normalize_docx(text: str) -> str:
    text = basic_clean(text)

    return text
