from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.config import ConfigError, parse_recipients
from tools.common.config import load_settings
from tools.common.file_io import write_json
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error, utc_now_iso
from tools.generate_infographic_prompt import generate_infographic_prompt
from tools.generate_infographic_image import generate_infographic_image
from tools.generate_newsletter import generate_newsletter
from tools.render_html_newsletter import render_html
from tools.research_topic import research_topic
from tools.send_gmail import send_gmail


def run_pipeline(
    topic: str,
    recipients: list[str] | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    weekly: bool = False,
) -> Path:
    if not topic.strip():
        raise ValueError("Topic is required.")

    context = get_run_context(run_id, topic)
    logger = setup_logger("run_newsletter_pipeline", context.log_path)
    write_json(
        context.run_dir / "input.json",
        {
            "topic": topic,
            "recipients": recipients or [],
            "run_id": context.run_id,
            "dry_run": dry_run,
            "weekly": weekly,
            "created_at": utc_now_iso(),
        },
    )

    logger.info("Pipeline started run_id=%s dry_run=%s", context.run_id, dry_run)
    try:
        research_topic(topic, context.run_id, dry_run, weekly)
        generate_newsletter(context.run_id, dry_run)
        generate_infographic_prompt(context.run_id, dry_run)
        try:
            generate_infographic_image(context.run_id, dry_run)
        except Exception as exc:
            record_error(
                context,
                "generate_infographic_image",
                exc,
                "Image generation is non-blocking. Check Gemini image model quota/access, then rerun this stage.",
            )
            logger.warning("Continuing without generated infographic image: %s", exc)
        render_html(context.run_id)
        send_gmail(context.run_id, recipients, dry_run)
    except Exception as exc:
        record_error(context, "run_newsletter_pipeline", exc, "Review stage-specific logs, fix the failing tool, then rerun.")
        logger.exception("Pipeline failed")
        raise

    logger.info("Pipeline completed successfully")
    return context.run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full WAT newsletter automation pipeline.")
    parser.add_argument("topic", nargs="?", help="Newsletter topic. If omitted, you will be prompted.")
    parser.add_argument("--run-id")
    parser.add_argument("--recipients", help="Comma-separated recipients. Defaults to NEWSLETTER_DEFAULT_RECIPIENTS.")
    parser.add_argument("--live", action="store_true", help="Call live APIs and send through Gmail. Default is dry-run.")
    parser.add_argument("--weekly", action="store_true", help="Create a ranked weekly news digest from the last 7 days.")
    args = parser.parse_args()

    if args.weekly and not args.topic:
        topic = load_settings().weekly_news_topic
    else:
        topic = args.topic or input("Topic: ").strip()
    recipients = parse_recipients(args.recipients or "") or None
    dry_run = not args.live
    try:
        run_dir = run_pipeline(topic, recipients=recipients, run_id=args.run_id, dry_run=dry_run, weekly=args.weekly)
        print(run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        print(f"run_newsletter_pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
