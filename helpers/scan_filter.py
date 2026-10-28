from __future__ import annotations

import re

_KEYWORD_SEPARATORS = re.compile(r"[,，;；、\n\r]+")
_MAX_KEYWORDS = 32


def parse_name_keywords(text: str) -> list[str]:
    """Split user input into unique, case-insensitive name keywords."""
    keywords: list[str] = []
    seen: set[str] = set()
    for token in _KEYWORD_SEPARATORS.split(text):
        keyword = token.strip()
        if not keyword:
            continue
        key = keyword.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(keyword)
        if len(keywords) >= _MAX_KEYWORDS:
            break
    return keywords


def name_matches_keywords(name: str | None, keywords: list[str]) -> bool:
    """True when the device name contains any keyword, or no keyword is set."""
    if not keywords:
        return True
    folded_name = (name or "").casefold()
    return any(keyword.casefold() in folded_name for keyword in keywords)
