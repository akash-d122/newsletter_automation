from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.config import ConfigError, load_settings
from tools.common.file_io import read_json, write_text
from tools.common.gemini import extract_text, post_generate_content, thinking_config
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error
from tools.common.text_cleaning import clean_text


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
            "Write one production-ready prompt for an infographic image generator. "
            "Outcome: an art-directable prompt that turns the newsletter's core idea into a "
            "clear editorial visual. Include layout, visual hierarchy, labels, color guidance, "
            "aspect ratio, and exclusions. Do not include markdown fences.\n\n"
            f"Newsletter JSON:\n{json.dumps(newsletter, ensure_ascii=False)}"
        )
        response = post_generate_content(
            settings.gemini_api_key,
            settings.gemini_text_model,
            {
                "contents": [{"parts": [{"text": request_prompt}]}],
                "generationConfig": thinking_config(settings.gemini_thinking_level),
            },
        )
        prompt = extract_text(response)
        if not prompt:
            raise RuntimeError("Gemini returned an empty infographic prompt.")

    prompt = clean_text(prompt)
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
