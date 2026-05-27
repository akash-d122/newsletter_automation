from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.config import ConfigError, load_settings
from tools.common.file_io import read_json, write_text
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def _post_openai(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed with HTTP {exc.code}: {body[:500]}") from exc


def _extract_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return response["output_text"].strip()
    chunks: list[str] = []
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _fallback_prompt(newsletter: dict[str, Any]) -> str:
    title = newsletter.get("headline", newsletter.get("topic", "Newsletter brief"))
    return (
        f"Create a clean editorial infographic for a professional newsletter titled '{title}'. "
        "Use a 16:9 horizontal layout with a strong headline band, three concise insight blocks, "
        "simple line icons, restrained brand colors, high contrast text, and generous spacing. "
        "Visualize the core message as a practical decision map: context, implications, and next actions. "
        "Avoid tiny text, photorealism, clutter, exaggerated gradients, and fictional charts. "
        "Style: premium business publication, modern, crisp, accessible."
    )


def generate_infographic_prompt(run_id: str, dry_run: bool = False) -> str:
    context = get_run_context(run_id)
    logger = setup_logger("generate_infographic_prompt", context.log_path)
    settings = load_settings(require_live=not dry_run)
    newsletter_path = context.run_dir / "newsletter.json"
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Missing newsletter artifact: {newsletter_path}")
    newsletter = read_json(newsletter_path)
    logger.info("Generating infographic prompt dry_run=%s", dry_run)

    if dry_run:
        prompt = _fallback_prompt(newsletter)
    else:
        request_prompt = (
            "Write one detailed production-ready prompt for an infographic image generator. "
            "Include layout, visual hierarchy, labels, color guidance, aspect ratio, and exclusions. "
            "Do not include markdown fences.\n\n"
            f"Newsletter JSON:\n{json.dumps(newsletter, ensure_ascii=False)}"
        )
        response = _post_openai(
            settings.openai_api_key,
            {"model": settings.openai_text_model, "input": request_prompt, "temperature": 0.5},
        )
        prompt = _extract_text(response)
        if not prompt:
            raise RuntimeError("OpenAI returned an empty infographic prompt.")

    write_text(context.run_dir / "infographic_prompt.txt", prompt)
    logger.info("Wrote infographic_prompt.txt")
    return prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate infographic prompt from newsletter.json.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id)
    try:
        generate_infographic_prompt(context.run_id, args.dry_run)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "generate_infographic_prompt", exc, "Check newsletter.json and OpenAI credentials.")
        print(f"generate_infographic_prompt failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
