from __future__ import annotations

import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .file_io import append_json_error, ensure_dir


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, fallback: str = "newsletter") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:60] or fallback


def create_run_id(topic: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{slugify(topic)}"


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    log_path: Path
    errors_path: Path


def get_run_context(run_id: str | None, topic: str | None = None) -> RunContext:
    resolved_run_id = run_id or create_run_id(topic or "newsletter")
    run_dir = ensure_dir(PROJECT_ROOT / ".tmp" / "runs" / resolved_run_id)
    return RunContext(
        run_id=resolved_run_id,
        run_dir=run_dir,
        log_path=run_dir / "run.log",
        errors_path=run_dir / "errors.json",
    )


def error_payload(stage: str, exc: BaseException, guidance: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(limit=6),
        "guidance": guidance,
        "timestamp": utc_now_iso(),
    }


def record_error(context: RunContext, stage: str, exc: BaseException, guidance: str) -> None:
    append_json_error(context.errors_path, error_payload(stage, exc, guidance))
