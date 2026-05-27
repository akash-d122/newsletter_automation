from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        if content and not content.endswith("\n"):
            handle.write("\n")


def append_json_error(path: Path, error: dict[str, Any]) -> None:
    errors: list[dict[str, Any]]
    if path.exists():
        existing = read_json(path)
        errors = existing if isinstance(existing, list) else [existing]
    else:
        errors = []
    errors.append(error)
    write_json(path, errors)
