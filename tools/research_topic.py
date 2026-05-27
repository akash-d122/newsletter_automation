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
from tools.common.file_io import write_json
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error, utc_now_iso


TAVILY_URL = "https://api.tavily.com/search"


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tavily request failed with HTTP {exc.code}: {body[:500]}") from exc


def _sample_research(topic: str, max_results: int) -> dict[str, Any]:
    sources = [
        {
            "title": f"Strategic overview of {topic}",
            "url": "https://example.com/strategic-overview",
            "snippet": f"A dry-run source summarizing market context, operational implications, and emerging questions around {topic}.",
            "key_points": [
                f"{topic} is creating new decisions for leaders and operators.",
                "Teams need a practical view of risks, opportunities, and next steps.",
            ],
        },
        {
            "title": f"Implementation signals for {topic}",
            "url": "https://example.com/implementation-signals",
            "snippet": f"A dry-run source focused on adoption patterns, constraints, and evidence to watch for {topic}.",
            "key_points": [
                "Adoption depends on workflow fit, cost, reliability, and governance.",
                "The strongest newsletter angle should connect news to concrete action.",
            ],
        },
    ]
    return {
        "topic": topic,
        "provider": "dry_run",
        "retrieved_at": utc_now_iso(),
        "query": topic,
        "sources": sources[:max_results],
        "notes": "Dry-run research uses deterministic sample sources and does not call Tavily.",
    }


def research_topic(topic: str, run_id: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    if not topic.strip():
        raise ValueError("Topic is required.")

    context = get_run_context(run_id, topic)
    logger = setup_logger("research_topic", context.log_path)
    settings = load_settings(require_live=not dry_run)
    logger.info("Starting research for run_id=%s topic=%s dry_run=%s", context.run_id, topic, dry_run)

    if dry_run:
        result = _sample_research(topic, settings.newsletter_max_results)
    else:
        payload = {
            "api_key": settings.tavily_api_key,
            "query": topic,
            "search_depth": settings.newsletter_search_depth,
            "max_results": settings.newsletter_max_results,
            "include_answer": True,
            "include_raw_content": False,
        }
        response = _post_json(TAVILY_URL, payload, {"Content-Type": "application/json"})
        sources = []
        for item in response.get("results", []):
            content = item.get("content") or item.get("snippet") or ""
            sources.append(
                {
                    "title": item.get("title", "Untitled source"),
                    "url": item.get("url", ""),
                    "snippet": content,
                    "key_points": [content[:280]] if content else [],
                }
            )
        if not sources:
            raise RuntimeError("Tavily returned no research results.")
        result = {
            "topic": topic,
            "provider": "tavily",
            "retrieved_at": utc_now_iso(),
            "query": topic,
            "answer": response.get("answer", ""),
            "sources": sources,
        }

    write_json(context.run_dir / "research.json", result)
    logger.info("Wrote research.json with %s sources", len(result.get("sources", [])))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Research a newsletter topic.")
    parser.add_argument("topic")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id, args.topic)
    try:
        research_topic(args.topic, context.run_id, args.dry_run)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "research_topic", exc, "Check topic, Tavily credentials, network access, and rate limits.")
        print(f"research_topic failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
