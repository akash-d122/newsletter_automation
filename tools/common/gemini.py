from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


def post_generate_content(api_key: str, model: str, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    encoded_model = urllib.parse.quote(model.replace("models/", ""), safe="")
    url = f"{GEMINI_API_ROOT}/models/{encoded_model}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed with HTTP {exc.code}: {body[:700]}") from exc


def extract_text(response: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in response.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            if part.get("text"):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def extract_inline_images(response: dict[str, Any]) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for candidate in response.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            inline_data = part.get("inlineData") or part.get("inline_data")
            if inline_data and inline_data.get("data"):
                images.append(
                    {
                        "mime_type": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png",
                        "data": inline_data["data"],
                    }
                )
    return images


def grounding_sources(response: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in response.get("candidates", []):
        metadata = candidate.get("groundingMetadata", {})
        for chunk in metadata.get("groundingChunks", []):
            web = chunk.get("web", {})
            uri = web.get("uri", "")
            if not uri or uri in seen:
                continue
            seen.add(uri)
            sources.append({"title": web.get("title", "Grounded source"), "url": uri})
    return sources


def thinking_config(level: str) -> dict[str, Any]:
    level = (level or "low").strip().lower()
    if level not in {"minimal", "low", "medium", "high"}:
        level = "low"
    return {"thinkingConfig": {"thinkingLevel": level}}
