import re
import html
from bs4 import BeautifulSoup

def strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ")

def normalize_spaces(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    t = strip_html(raw_text)
    t = normalize_spaces(t)
    return t