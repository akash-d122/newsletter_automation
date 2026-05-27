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
from tools.common.file_io import read_json, write_json, write_text
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error, utc_now_iso


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
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed with HTTP {exc.code}: {body[:500]}") from exc


def _extract_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return response["output_text"]
    chunks: list[str] = []
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _fallback_newsletter(research: dict[str, Any]) -> dict[str, Any]:
    topic = research["topic"]
    sources = research.get("sources", [])
    return {
        "topic": topic,
        "subject": f"{topic}: what matters now",
        "preheader": f"A concise briefing on {topic}, with signals, implications, and next steps.",
        "headline": f"{topic}: the practical brief",
        "intro": f"This edition looks at {topic} through the lens of practical decisions: what is changing, why it matters, and what to watch next.",
        "sections": [
            {
                "title": "Why it matters",
                "body": "The strongest signal is not novelty alone. It is whether the topic changes decisions, budgets, workflows, or customer expectations.",
                "bullets": [point for source in sources for point in source.get("key_points", [])][:3],
            },
            {
                "title": "What to watch",
                "body": "Watch for evidence of adoption, constraints, governance pressure, and credible examples that move beyond announcement value.",
                "bullets": [
                    "Who is adopting it and why now?",
                    "Which constraints slow implementation?",
                    "What measurable outcomes are being reported?",
                ],
            },
        ],
        "takeaway": f"For {topic}, the useful question is how it changes concrete work, not just how much attention it receives.",
        "cta": "Use this brief to decide what to monitor, test, or explain to your audience this week.",
        "sources": [{"title": item.get("title"), "url": item.get("url")} for item in sources],
        "generated_at": utc_now_iso(),
        "generation_mode": "dry_run",
    }


def _markdown(newsletter: dict[str, Any]) -> str:
    lines = [
        f"# {newsletter['headline']}",
        "",
        f"**Subject:** {newsletter['subject']}",
        f"**Preheader:** {newsletter['preheader']}",
        "",
        newsletter["intro"],
        "",
    ]
    for section in newsletter.get("sections", []):
        lines.extend([f"## {section['title']}", "", section.get("body", ""), ""])
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    lines.extend(["## Takeaway", "", newsletter.get("takeaway", ""), "", newsletter.get("cta", ""), ""])
    if newsletter.get("sources"):
        lines.extend(["## Sources", ""])
        for source in newsletter["sources"]:
            lines.append(f"- [{source.get('title', 'Source')}]({source.get('url', '')})")
    return "\n".join(lines).strip()


def _parse_newsletter_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    data = json.loads(cleaned)
    required = ["subject", "preheader", "headline", "intro", "sections", "takeaway", "cta"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Newsletter JSON is missing required keys: {', '.join(missing)}")
    return data


def generate_newsletter(run_id: str, dry_run: bool = False) -> dict[str, Any]:
    context = get_run_context(run_id)
    logger = setup_logger("generate_newsletter", context.log_path)
    settings = load_settings(require_live=not dry_run)
    research_path = context.run_dir / "research.json"
    if not research_path.exists():
        raise FileNotFoundError(f"Missing research artifact: {research_path}")
    research = read_json(research_path)
    logger.info("Generating newsletter dry_run=%s", dry_run)

    if dry_run:
        newsletter = _fallback_newsletter(research)
    else:
        prompt = (
            "Create a professional newsletter as strict JSON with keys: "
            "topic, subject, preheader, headline, intro, sections, takeaway, cta, sources. "
            "Each section must have title, body, and bullets. Use only the provided research.\n\n"
            f"Research:\n{json.dumps(research, ensure_ascii=False)}"
        )
        response = _post_openai(
            settings.openai_api_key,
            {"model": settings.openai_text_model, "input": prompt, "temperature": 0.4},
        )
        newsletter = _parse_newsletter_json(_extract_text(response))
        newsletter["generated_at"] = utc_now_iso()
        newsletter["generation_mode"] = "openai"

    write_json(context.run_dir / "newsletter.json", newsletter)
    write_text(context.run_dir / "draft.md", _markdown(newsletter))
    logger.info("Wrote newsletter.json and draft.md")
    return newsletter


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate newsletter draft from research.json.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id)
    try:
        generate_newsletter(context.run_id, args.dry_run)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "generate_newsletter", exc, "Check research.json and OpenAI credentials/output format.")
        print(f"generate_newsletter failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
