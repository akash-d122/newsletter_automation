# Create Newsletter Workflow

## Objective

Create a professional newsletter from a user-provided topic using deterministic tools for research, drafting, infographic prompt generation, HTML rendering, Gmail delivery, and local artifact logging.

## Required Input

- `topic`: The newsletter topic.
- Optional `recipients`: Comma-separated email recipients. If omitted, use `NEWSLETTER_DEFAULT_RECIPIENTS`.
- Optional `run_id`: Stable run identifier. If omitted, the pipeline creates one.
- Optional `dry_run`: When true, tools avoid paid/external API calls and email sending.

## Required Tools

Run tools in this sequence:

1. `tools/research_topic.py`
2. `tools/generate_newsletter.py`
3. `tools/generate_infographic_prompt.py`
4. `tools/render_html_newsletter.py`
5. `tools/send_gmail.py`

Use `tools/run_newsletter_pipeline.py` to run the full workflow.

## Expected Outputs

All artifacts are saved under `.tmp/runs/<run_id>/`:

- `input.json`
- `research.json`
- `newsletter.json`
- `draft.md`
- `infographic_prompt.txt`
- `newsletter.html`
- `send_result.json`
- `run.log`
- `errors.json` when failures occur

## Environment Variables

Required for live mode:

- `TAVILY_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GMAIL_SENDER_EMAIL`
- `NEWSLETTER_DEFAULT_RECIPIENTS`
- `NEWSLETTER_FROM_NAME`

Optional:

- `OPENAI_TEXT_MODEL`, defaults to `gpt-4.1-mini`
- `NEWSLETTER_SEARCH_DEPTH`, defaults to `basic`
- `NEWSLETTER_MAX_RESULTS`, defaults to `5`

## Operating Notes

- Start with `--dry-run` until artifacts look correct.
- Live research and generation call external APIs and may incur cost.
- Live Gmail delivery must only be run after explicit approval.
- If a tool fails, read `run.log` and `errors.json`, fix the deterministic tool, rerun the failed stage, and update this workflow if a reusable lesson was learned.

## Edge Cases

- Missing topic: stop with a clear validation error.
- Missing live credentials: stop before making external calls.
- Empty research results: generate a structured error and do not draft unsupported claims.
- Gmail API failure: save the API status/body summary to `send_result.json` or `errors.json`.
