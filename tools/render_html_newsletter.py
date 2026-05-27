from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.file_io import read_json, write_text
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error


def _esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _render_sections(sections: list[dict]) -> str:
    rendered = []
    for section in sections:
        bullets = "".join(
            f"<li style=\"margin:0 0 8px 0;\">{_esc(bullet)}</li>"
            for bullet in section.get("bullets", [])
        )
        rendered.append(
            f"""
            <tr>
              <td style="padding:22px 28px;border-top:1px solid #e6e8ec;">
                <h2 style="margin:0 0 10px 0;font-size:20px;line-height:1.3;color:#172033;">{_esc(section.get("title"))}</h2>
                <p style="margin:0 0 12px 0;font-size:15px;line-height:1.65;color:#354154;">{_esc(section.get("body"))}</p>
                <ul style="margin:0;padding-left:20px;font-size:15px;line-height:1.55;color:#354154;">{bullets}</ul>
              </td>
            </tr>
            """
        )
    return "\n".join(rendered)


def _render_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    rows = []
    for source in sources:
        title = _esc(source.get("title", "Source"))
        url = _esc(source.get("url", ""))
        rows.append(f"<li style=\"margin:0 0 6px 0;\"><a href=\"{url}\" style=\"color:#2364aa;text-decoration:none;\">{title}</a></li>")
    return (
        "<tr><td style=\"padding:20px 28px;border-top:1px solid #e6e8ec;\">"
        "<h2 style=\"margin:0 0 10px 0;font-size:16px;color:#172033;\">Sources</h2>"
        f"<ul style=\"margin:0;padding-left:20px;font-size:13px;line-height:1.5;color:#5b6575;\">{''.join(rows)}</ul>"
        "</td></tr>"
    )


def render_html(run_id: str) -> str:
    context = get_run_context(run_id)
    logger = setup_logger("render_html_newsletter", context.log_path)
    newsletter_path = context.run_dir / "newsletter.json"
    prompt_path = context.run_dir / "infographic_prompt.txt"
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Missing newsletter artifact: {newsletter_path}")
    newsletter = read_json(newsletter_path)
    infographic_prompt = prompt_path.read_text(encoding="utf-8").strip() if prompt_path.exists() else ""
    logger.info("Rendering HTML newsletter")

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_esc(newsletter.get("subject"))}</title>
    <style>
      @media only screen and (max-width: 640px) {{
        .container {{ width: 100% !important; }}
        .content-pad {{ padding-left: 18px !important; padding-right: 18px !important; }}
      }}
    </style>
  </head>
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#172033;">
    <div style="display:none;max-height:0;overflow:hidden;">{_esc(newsletter.get("preheader"))}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;margin:0;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" class="container" width="640" cellspacing="0" cellpadding="0" style="width:640px;max-width:100%;background:#ffffff;border:1px solid #dfe3e8;">
            <tr>
              <td class="content-pad" style="padding:26px 28px;background:#172033;">
                <div style="font-size:13px;letter-spacing:0;color:#b9d6ff;margin-bottom:12px;">Agentic Brief</div>
                <h1 style="margin:0;font-size:30px;line-height:1.18;color:#ffffff;">{_esc(newsletter.get("headline"))}</h1>
              </td>
            </tr>
            <tr>
              <td class="content-pad" style="padding:24px 28px;">
                <p style="margin:0;font-size:16px;line-height:1.65;color:#354154;">{_esc(newsletter.get("intro"))}</p>
              </td>
            </tr>
            {_render_sections(newsletter.get("sections", []))}
            <tr>
              <td style="padding:22px 28px;border-top:1px solid #e6e8ec;background:#f9fafb;">
                <h2 style="margin:0 0 10px 0;font-size:18px;color:#172033;">Takeaway</h2>
                <p style="margin:0 0 12px 0;font-size:15px;line-height:1.65;color:#354154;">{_esc(newsletter.get("takeaway"))}</p>
                <p style="margin:0;font-size:15px;line-height:1.55;color:#172033;font-weight:bold;">{_esc(newsletter.get("cta"))}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 28px;border-top:1px solid #e6e8ec;">
                <h2 style="margin:0 0 10px 0;font-size:16px;color:#172033;">Infographic Prompt</h2>
                <p style="margin:0;font-size:13px;line-height:1.55;color:#5b6575;">{_esc(infographic_prompt)}</p>
              </td>
            </tr>
            {_render_sources(newsletter.get("sources", []))}
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
    write_text(context.run_dir / "newsletter.html", html_doc)
    logger.info("Wrote newsletter.html")
    return html_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Render responsive HTML newsletter.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    context = get_run_context(args.run_id)
    try:
        render_html(context.run_id)
        print(context.run_dir)
        return 0
    except Exception as exc:
        record_error(context, "render_html_newsletter", exc, "Check newsletter.json and infographic_prompt.txt.")
        print(f"render_html_newsletter failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
