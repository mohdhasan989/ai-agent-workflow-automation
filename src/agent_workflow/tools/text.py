import re
from difflib import SequenceMatcher


def normalize_text(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def text_similarity(a, b) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()