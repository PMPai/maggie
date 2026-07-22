import unicodedata
import re


def normalize_text(text: str) -> str:
    """Normalize item description for matching.
    - NFKC: full-width to half-width
    - Strip whitespace, collapse spaces
    - Lowercase
    - Remove brackets, parentheses content
    - Strip common unit suffixes
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\(\)（）【】\[\]「」]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip().lower()
    text = re.sub(r"[（(].*?[)）]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
