from .common import basic_clean

def normalize_excel(text: str) -> str:
    # Excel extractor already gives semantic summaries
    return basic_clean(text)
