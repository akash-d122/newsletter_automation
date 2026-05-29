from __future__ import annotations

from typing import Any


REPLACEMENTS = {
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00c2": "",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u009d": "-",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u0153": "-",
    "\u00c3\u201a": "",
    "tireles ": "tireless ",
}


def clean_text(value: str) -> str:
    cleaned = value
    for bad, good in REPLACEMENTS.items():
        cleaned = cleaned.replace(bad, good)
    return cleaned


def clean_data(value: Any) -> Any:
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean_data(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_data(item) for key, item in value.items()}
    return value
