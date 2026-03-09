from .common import basic_clean

def normalize_pdf(text: str) -> str:
    text = basic_clean(text)

    return text
