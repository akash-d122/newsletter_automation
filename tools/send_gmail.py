from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.config import ConfigError, load_settings, parse_recipients
from tools.common.file_io import read_json, write_json
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error, utc_now_iso
from tools.common.text_cleaning import clean_data


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _request_json(url: str, data: bytes, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:500]}") from exc


def _access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    response = _request_json(GOOGLE_TOKEN_URL, payload, {"Content-Type": "application/x-www-form-urlencoded"})
    token = response.get("access_token")
    if not token:
        raise RuntimeError("Google OAuth token response did not include access_token.")
    return token


def _plain_text(newsletter: dict[str, Any]) -> str:
    lines = [
        newsletter.get("headline", newsletter.get("subject", "Newsletter")),
        "",
        newsletter.get("intro", ""),
        "",
        "Executive Takeaway",
        newsletter.get("takeaway", ""),
        "",
    ]
    for section in newsletter.get("sections", []):
        lines.extend([section.get("title", ""), "", section.get("body", "")])
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    if newsletter.get("cta"):
        lines.extend(["Next Step", newsletter["cta"], ""])
    if newsletter.get("sources"):
        lines.append("Sources")
        for source in newsletter["sources"]:
            lines.append(f"- {source.get('title', 'Source')}: {source.get('url', '')}")
    return "\n".join(line for line in lines if line is not None).strip()


def _add_related_image(message: EmailMessage, path: Path, cid: str) -> bool:
    if not path.exists():
        return False
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type or not mime_type.startswith("image/"):
        return False
    maintype, subtype = mime_type.split("/", 1)
    html_part = message.get_payload()[-1]
    html_part.add_related(path.read_bytes(), maintype=maintype, subtype=subtype, cid=f"<{cid}>")
    return True


def _message_raw(
    sender: str,
    from_name: str,
    recipients: list[str],
    subject: str,
    html_body: str,
    newsletter: dict[str, Any],
    run_dir: Path,
) -> tuple[str, list[str]]:
    message = EmailMessage()
    message["From"] = f"{from_name} <{sender}>"
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(_plain_text(newsletter))
    message.add_alternative(html_body, subtype="html")
    inline_images: list[str] = []
    logo_path = Path(__file__).resolve().parents[1] / "agentic-brief-logo.jpg"
    if _add_related_image(message, logo_path, "agentic-brief-logo"):
        inline_images.append("agentic-brief-logo.jpg")
    for image_path in [run_dir / "infographic.png", run_dir / "infographic.jpg", run_dir / "infographic.webp"]:
        if _add_related_image(message, image_path, "newsletter-infographic"):
            inline_images.append(image_path.name)
            break
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return encoded.rstrip("="), inline_images


def send_gmail(run_id: str, recipients: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    context = get_run_context(run_id)
    logger = setup_logger("send_gmail", context.log_path)
    settings = load_settings(require_gmail=not dry_run)
    newsletter_path = context.run_dir / "newsletter.json"
    html_path = context.run_dir / "newsletter.html"
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Missing newsletter artifact: {newsletter_path}")
    if not html_path.exists():
        raise FileNotFoundError(f"Missing HTML artifact: {html_path}")

    newsletter = clean_data(read_json(newsletter_path))
    html_body = html_path.read_text(encoding="utf-8")
    resolved_recipients = recipients or settings.newsletter_default_recipients
    if not resolved_recipients:
        raise ConfigError("No recipients provided and NEWSLETTER_DEFAULT_RECIPIENTS is empty.")

    subject = newsletter.get("subject") or newsletter.get("headline") or "Newsletter"
    logger.info("Preparing Gmail send dry_run=%s recipients=%s", dry_run, len(resolved_recipients))

    if dry_run:
        result = {
            "status": "dry_run",
            "sent": False,
            "subject": subject,
            "recipients": resolved_recipients,
            "html_bytes": len(html_body.encode("utf-8")),
            "timestamp": utc_now_iso(),
        }
    else:
        token = _access_token(settings.google_client_id, settings.google_client_secret, settings.google_refresh_token)
        raw_message, inline_images = _message_raw(
            settings.gmail_sender_email,
            settings.newsletter_from_name,
            resolved_recipients,
            subject,
            html_body,
            newsletter,
            context.run_dir,
        )
        response = _request_json(
            GMAIL_SEND_URL,
            json.dumps({"raw": raw_message}).encode("utf-8"),
            {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        result = {
            "status": "sent",
            "sent": True,
            "subject": subject,
            "recipients": resolved_recipients,
            "inline_images": inline_images,
            "gmail_response": response,
            "timestamp": utc_now_iso(),
        }

    write_json(context.run_dir / "send_result.json", result)
    logger.info("Wrote send_result.json status=%s", result["status"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Send newsletter HTML through Gmail API.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--recipients", help="Comma-separated recipients. Defaults to NEWSLETTER_DEFAULT_RECIPIENTS.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    context = get_run_context(args.run_id)
    try:
        recipients = parse_recipients(args.recipients or "") or None
        send_gmail(context.run_id, recipients, args.dry_run)
        print(context.run_dir)
        return 0
    except (ConfigError, Exception) as exc:
        record_error(context, "send_gmail", exc, "Check Gmail OAuth env vars, recipients, and Gmail API permissions.")
        print(f"send_gmail failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
