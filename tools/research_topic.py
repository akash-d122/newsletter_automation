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
from tools.common.gemini import extract_text, grounding_sources, post_generate_content, thinking_config
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


def _normalize_tavily_sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for item in results:
        content = item.get("content") or item.get("snippet") or ""
        sources.append(
            {
                "title": item.get("title", "Untitled source"),
                "url": item.get("url", ""),
                "snippet": content,
                "key_points": [content[:420]] if content else [],
                "published_date": item.get("published_date", ""),
                "score": item.get("score", 0),
            }
        )
    return sources


def _tavily_research(topic: str, settings: Any) -> dict[str, Any]:
    if not settings.tavily_api_key:
        raise ConfigError("TAVILY_API_KEY is required when Tavily research is used.")
    payload = {
        "api_key": settings.tavily_api_key,
        "query": topic,
        "search_depth": settings.newsletter_search_depth,
        "max_results": settings.newsletter_max_results,
        "include_answer": True,
        "include_raw_content": False,
    }
    response = _post_json(TAVILY_URL, payload, {"Content-Type": "application/json"})
    sources = _normalize_tavily_sources(response.get("results", []))
    if not sources:
        raise RuntimeError("Tavily returned no research results.")
    return {
        "topic": topic,
        "provider": "tavily",
        "retrieved_at": utc_now_iso(),
        "query": topic,
        "answer": response.get("answer", ""),
        "sources": sources,
    }


def _weekly_tavily_research(topic: str, settings: Any) -> dict[str, Any]:
    if not settings.tavily_api_key:
        raise ConfigError("TAVILY_API_KEY is required for weekly news research.")
    queries = [
        topic,
        "top artificial intelligence news this week",
        "AI model releases funding regulation enterprise news this week",
        "AI agents automation products startups news this week",
    ]
    seen_urls: set[str] = set()
    sources: list[dict[str, Any]] = []
    answers: list[str] = []
    for query in queries:
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": settings.newsletter_search_depth,
            "topic": "news",
            "days": settings.weekly_news_days,
            "time_range": "week",
            "max_results": max(4, min(settings.weekly_news_max_results, 10)),
            "include_answer": True,
            "include_raw_content": False,
        }
        response = _post_json(TAVILY_URL, payload, {"Content-Type": "application/json"})
        if response.get("answer"):
            answers.append(response["answer"])
        for source in _normalize_tavily_sources(response.get("results", [])):
            url = source.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(source)

    sources.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    sources = sources[: settings.weekly_news_max_results]
    if not sources:
        raise RuntimeError("Tavily returned no weekly news results.")
    return {
        "topic": topic,
        "provider": "tavily",
        "research_mode": "weekly_digest",
        "retrieved_at": utc_now_iso(),
        "query": topic,
        "days": settings.weekly_news_days,
        "answer": "\n\n".join(answers),
        "sources": sources,
    }


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


def research_topic(topic: str, run_id: str | None = None, dry_run: bool = False, weekly: bool = False) -> dict[str, Any]:
    if not topic.strip():
        raise ValueError("Topic is required.")

    context = get_run_context(run_id, topic)
    logger = setup_logger("research_topic", context.log_path)
    settings = load_settings(require_live=not dry_run)
    provider = settings.newsletter_research_provider.lower()
    logger.info(
        "Starting research for run_id=%s topic=%s dry_run=%s provider=%s",
        context.run_id,
        topic,
        dry_run,
        provider,
    )

    if dry_run:
        result = _sample_research(topic, settings.weekly_news_max_results if weekly else settings.newsletter_max_results)
        if weekly:
            result["research_mode"] = "weekly_digest"
            result["days"] = settings.weekly_news_days
    elif provider == "gemini_grounded":
        prompt = (
            "Research this newsletter topic using current web information. "
            "Return a concise research brief with the most important facts, trends, tensions, and sources. "
            "Focus on what a professional audience needs to know this week.\n\n"
            f"Topic: {topic}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": thinking_config(settings.gemini_thinking_level),
        }
        try:
            response = post_generate_content(settings.gemini_api_key, settings.gemini_research_model, payload)
            answer = extract_text(response)
            sources = [
                {
                    "title": source["title"],
                    "url": source["url"],
                    "snippet": answer[:600],
                    "key_points": [answer[:280]] if answer else [],
                }
                for source in grounding_sources(response)
            ][: settings.newsletter_max_results]
            if not answer:
                raise RuntimeError("Gemini returned an empty grounded research brief.")
            if not sources:
                raise RuntimeError("Gemini grounded research returned no source metadata.")
            result = {
                "topic": topic,
                "provider": "gemini_grounded",
                "model": settings.gemini_research_model,
                "retrieved_at": utc_now_iso(),
                "query": topic,
                "answer": answer,
                "sources": sources,
            }
        except Exception as exc:
            if not settings.tavily_api_key:
                raise
            logger.warning("Gemini grounded research failed; falling back to Tavily: %s", exc)
            result = _tavily_research(topic, settings)
            result["fallback_from"] = "gemini_grounded"
            result["fallback_reason"] = str(exc)[:500]
    else:
        result = _weekly_tavily_research(topic, settings) if weekly else _tavily_research(topic, settings)

    write_json(context.run_dir / "research.json", result)
    logger.info("Wrote research.json with %s sources", len(result.get("sources", [])))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Research a newsletter topic.")
    parser.add_argument("topic")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id, args.topic)
    try:
        research_topic(args.topic, context.run_id, args.dry_run, args.weekly)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "research_topic", exc, "Check topic, Tavily credentials, network access, and rate limits.")
        print(f"research_topic failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
