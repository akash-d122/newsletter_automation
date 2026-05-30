from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.common.file_io import read_json, write_text
from tools.common.logging_setup import setup_logger
from tools.common.run_context import get_run_context, record_error
from tools.common.text_cleaning import clean_data


def _esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _issue_date() -> str:
    return datetime.now(timezone.utc).strftime("%b %d, %Y")


def _render_bullets(bullets: list[str]) -> str:
    rows = []
    for bullet in bullets:
        rows.append(
            f"""
            <tr>
              <td width="18" valign="top" style="padding:2px 0 9px 0;">
                <span style="display:inline-block;width:7px;height:7px;background:#0f766e;border-radius:7px;"></span>
              </td>
              <td style="padding:0 0 9px 0;font-size:15px;line-height:1.55;color:#344054;">
                {_esc(bullet)}
              </td>
            </tr>
            """
        )
    return "\n".join(rows)


def _render_sections(sections: list[dict]) -> str:
    rendered = []
    accents = ["#0f766e", "#6d4674", "#b7791f"]
    for index, section in enumerate(sections, start=1):
        accent = accents[(index - 1) % len(accents)]
        rendered.append(
            f"""
            <tr>
              <td style="padding:0 30px 24px 30px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;border:1px solid #e6e1d8;background:#fffdf9;">
                  <tr>
                    <td width="5" style="background:{accent};font-size:1px;line-height:1px;">&nbsp;</td>
                    <td style="padding:22px 22px 18px 22px;">
                      <div style="font-size:12px;line-height:1;color:{accent};font-weight:bold;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">Signal {index}</div>
                      <h2 style="margin:0 0 10px 0;font-family:Georgia,'Times New Roman',serif;font-size:23px;line-height:1.25;color:#1f2933;font-weight:normal;">
                        {_esc(section.get("title"))}
                      </h2>
                      <p style="margin:0 0 16px 0;font-size:16px;line-height:1.65;color:#344054;">
                        {_esc(section.get("body"))}
                      </p>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                        {_render_bullets(section.get("bullets", []))}
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """
        )
    return "\n".join(rendered)


def _render_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    rows = []
    for index, source in enumerate(sources, start=1):
        title = _esc(source.get("title", "Source"))
        url = _esc(source.get("url", ""))
        rows.append(
            f"""
            <tr>
              <td width="26" valign="top" style="padding:0 0 8px 0;font-size:12px;line-height:1.45;color:#8a6f3d;">{index}.</td>
              <td style="padding:0 0 8px 0;font-size:12px;line-height:1.45;color:#667085;">
                <a href="{url}" style="color:#365c7d;text-decoration:underline;">{title}</a>
              </td>
            </tr>
            """
        )
    return "\n".join(rows)


def _infographic_block(context) -> str:
    image_paths = list(context.run_dir.glob("infographic.png")) + list(context.run_dir.glob("infographic.jpg")) + list(context.run_dir.glob("infographic.webp"))
    if not image_paths:
        return ""
    return """
            <tr>
              <td style="padding:0 30px 28px 30px;">
                <img src="cid:newsletter-infographic" width="620" alt="Newsletter infographic" style="display:block;width:100%;max-width:620px;height:auto;border:1px solid #e6e1d8;">
              </td>
            </tr>
            """


def render_html(run_id: str) -> str:
    context = get_run_context(run_id)
    logger = setup_logger("render_html_newsletter", context.log_path)
    newsletter_path = context.run_dir / "newsletter.json"
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Missing newsletter artifact: {newsletter_path}")
    newsletter = clean_data(read_json(newsletter_path))
    logger.info("Rendering HTML newsletter")

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light only">
    <title>{_esc(newsletter.get("subject"))}</title>
    <style>
      @media only screen and (max-width: 640px) {{
        .outer-pad {{ padding: 0 !important; }}
        .container {{ width: 100% !important; border-left: 0 !important; border-right: 0 !important; }}
        .px {{ padding-left: 20px !important; padding-right: 20px !important; }}
        .hero-title {{ font-size: 34px !important; line-height: 1.08 !important; }}
      }}
    </style>
  </head>
  <body style="margin:0;padding:0;background:#f3efe7;font-family:Arial,Helvetica,sans-serif;color:#1f2933;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      {_esc(newsletter.get("preheader"))}
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;background:#f3efe7;">
      <tr>
        <td class="outer-pad" align="center" style="padding:32px 16px;">
          <table role="presentation" class="container" width="680" cellspacing="0" cellpadding="0" style="width:680px;max-width:100%;border-collapse:collapse;background:#fffaf2;border:1px solid #ded7ca;">
            <tr>
              <td class="px" style="padding:26px 34px 18px 34px;border-bottom:1px solid #e7dfd2;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                  <tr>
                    <td style="font-size:13px;line-height:1.3;color:#0f766e;font-weight:bold;letter-spacing:0.12em;text-transform:uppercase;">
                      <img src="cid:agentic-brief-logo" width="132" alt="Agentic Brief" style="display:block;width:132px;max-width:132px;height:auto;border:0;">
                    </td>
                    <td align="right" style="font-size:13px;line-height:1.3;color:#8a6f3d;">
                      {_esc(_issue_date())}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td class="px" style="padding:36px 34px 26px 34px;background:#fffaf2;">
                <div style="display:inline-block;padding:6px 10px;background:#e7f4ef;color:#0f766e;font-size:12px;line-height:1;font-weight:bold;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:18px;">
                  Weekly Intelligence
                </div>
                <h1 class="hero-title" style="margin:0 0 18px 0;font-family:Georgia,'Times New Roman',serif;font-size:42px;line-height:1.05;color:#1f2933;font-weight:normal;">
                  {_esc(newsletter.get("headline"))}
                </h1>
                <p style="margin:0;font-size:18px;line-height:1.65;color:#344054;">
                  {_esc(newsletter.get("intro"))}
                </p>
              </td>
            </tr>
            {_infographic_block(context)}
            <tr>
              <td style="padding:0 30px 24px 30px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;background:#1f2933;">
                  <tr>
                    <td style="padding:20px 22px;">
                      <div style="font-size:12px;line-height:1;color:#f2b84b;font-weight:bold;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">Executive Takeaway</div>
                      <p style="margin:0;font-size:17px;line-height:1.55;color:#ffffff;font-family:Georgia,'Times New Roman',serif;">
                        {_esc(newsletter.get("takeaway"))}
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            {_render_sections(newsletter.get("sections", []))}
            <tr>
              <td style="padding:0 30px 30px 30px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;background:#f7ead7;border:1px solid #ead8bb;">
                  <tr>
                    <td style="padding:22px;">
                      <div style="font-size:12px;line-height:1;color:#9a5b1f;font-weight:bold;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">Next Step</div>
                      <p style="margin:0 0 16px 0;font-size:16px;line-height:1.6;color:#2d2a26;">
                        {_esc(newsletter.get("cta"))}
                      </p>
                      <div style="display:inline-block;background:#0f766e;color:#ffffff;font-size:14px;font-weight:bold;padding:11px 16px;">
                        Priority: review and decide
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td class="px" style="padding:24px 34px 30px 34px;background:#ffffff;border-top:1px solid #e7dfd2;">
                <div style="font-size:12px;line-height:1;color:#6d4674;font-weight:bold;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">Sources</div>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                  {_render_sources(newsletter.get("sources", []))}
                </table>
              </td>
            </tr>
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
        record_error(context, "render_html_newsletter", exc, "Check newsletter.json.")
        print(f"render_html_newsletter failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
