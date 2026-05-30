from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.config import ConfigError, load_settings
from tools.common.file_io import read_json, write_json
from tools.common.gemini import extract_inline_images, post_generate_content
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error, utc_now_iso
from tools.common.text_cleaning import clean_text


def _extension(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def generate_infographic_image(run_id: str, dry_run: bool = False) -> Path:
    context = get_run_context(run_id)
    logger = setup_logger("generate_infographic_image", context.log_path)
    settings = load_settings(require_live=not dry_run)
    prompt_path = context.run_dir / "infographic_prompt.txt"
    newsletter_path = context.run_dir / "newsletter.json"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Missing infographic prompt artifact: {prompt_path}")
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Missing newsletter artifact: {newsletter_path}")

    prompt = clean_text(prompt_path.read_text(encoding="utf-8")).strip()
    newsletter = read_json(newsletter_path)
    logger.info("Generating infographic image dry_run=%s", dry_run)

    if dry_run:
        image_path = context.run_dir / "infographic_placeholder.txt"
        image_path.write_text(
            "Dry-run placeholder. Live mode writes infographic.png from Gemini image generation.\n",
            encoding="utf-8",
        )
        write_json(
            context.run_dir / "infographic_image.json",
            {
                "status": "dry_run",
                "model": settings.gemini_image_model,
                "path": str(image_path),
                "timestamp": utc_now_iso(),
            },
        )
        logger.info("Wrote dry-run infographic placeholder")
        return image_path

    image_prompt = (
        "Create a polished editorial newsletter infographic image. "
        "It must work inside an email newsletter: clean composition, strong contrast, no tiny text, "
        "no fake data labels, and no clutter. Use the following art direction exactly as guidance.\n\n"
        f"Newsletter subject: {newsletter.get('subject', '')}\n\n"
        f"Art direction:\n{prompt}"
    )
    payload = {
        "contents": [{"parts": [{"text": image_prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    last_error: Exception | None = None
    selected_model = ""
    images = []
    candidate_models = [settings.gemini_image_model, *settings.gemini_image_fallback_models]
    for model in dict.fromkeys(candidate_models):
        selected_model = model
        try:
            logger.info("Trying Gemini image model %s", model)
            response = post_generate_content(settings.gemini_api_key, model, payload, timeout=180)
            images = extract_inline_images(response)
            if images:
                break
            last_error = RuntimeError(f"{model} returned no inline image data.")
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini image model %s failed: %s", model, exc)
    if not images and last_error:
        raise last_error
    if not images:
        raise RuntimeError("Gemini image generation returned no inline image data.")

    image = images[0]
    image_bytes = base64.b64decode(image["data"])
    image_path = context.run_dir / f"infographic{_extension(image['mime_type'])}"
    image_path.write_bytes(image_bytes)
    write_json(
        context.run_dir / "infographic_image.json",
        {
            "status": "generated",
            "model": selected_model,
            "mime_type": image["mime_type"],
            "path": str(image_path),
            "bytes": len(image_bytes),
            "timestamp": utc_now_iso(),
        },
    )
    logger.info("Wrote %s bytes to %s", len(image_bytes), image_path.name)
    return image_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate infographic image from infographic_prompt.txt.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id)
    try:
        generate_infographic_image(context.run_id, args.dry_run)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "generate_infographic_image", exc, "Check Gemini API key, image model access, quota, and prompt safety.")
        print(f"generate_infographic_image failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
