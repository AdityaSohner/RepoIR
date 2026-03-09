import re

def basic_clean(text: str) -> str:
    # normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # remove repeated OCR junk
    text = re.sub(r"(.)\1{4,}", "", text)

    # remove urls
    text = re.sub(r"http\S+", "", text)

    return text.strip()


def remove_code_like_lines(text: str) -> str:
    lines = text.split(". ")
    cleaned = []

    for line in lines:
        if any(tok in line for tok in [
            "{", "}", "elif", "print(", "def ", "class ", "==", "=>"
        ]):
            continue
        if len(line.strip()) < 10:
            continue
        cleaned.append(line)

    return ". ".join(cleaned)
