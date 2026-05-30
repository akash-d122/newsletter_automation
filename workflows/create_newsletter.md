# Create Newsletter Workflow

## Objective

Create a professional newsletter from a user-provided topic using deterministic tools for research, drafting, infographic prompt generation, HTML rendering, Gmail delivery, and local artifact logging.

## Required Input

- `topic`: The newsletter topic.
- Optional `recipients`: Comma-separated email recipients. If omitted, use `NEWSLETTER_DEFAULT_RECIPIENTS`.
- Optional `run_id`: Stable run identifier. If omitted, the pipeline creates one.
- Optional `dry_run`: When true, tools avoid paid/external API calls and email sending.
- Optional `weekly`: When true, research the top AI news from the last 7 days and produce a ranked weekly digest.

## Required Tools

Run tools in this sequence:

1. `tools/research_topic.py`
2. `tools/generate_newsletter.py`
3. `tools/generate_infographic_prompt.py`
4. `tools/generate_infographic_image.py`
5. `tools/render_html_newsletter.py`
6. `tools/send_gmail.py`

Use `tools/run_newsletter_pipeline.py` to run the full workflow.

## Expected Outputs

All artifacts are saved under `.tmp/runs/<run_id>/`:

- `input.json`
- `research.json`
- `newsletter.json`
- `draft.md`
- `infographic_prompt.txt`
- `infographic.png`
- `infographic_image.json`
- `newsletter.html`
- `send_result.json`
- `run.log`
- `errors.json` when failures occur

## Environment Variables

Required for live mode:

- `GEMINI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GMAIL_SENDER_EMAIL`
- `NEWSLETTER_DEFAULT_RECIPIENTS`
- `NEWSLETTER_FROM_NAME`

Optional:

- `TAVILY_API_KEY`, required only when `NEWSLETTER_RESEARCH_PROVIDER=tavily`
- `NEWSLETTER_RESEARCH_PROVIDER`, defaults to `tavily`
- `GEMINI_RESEARCH_MODEL`, defaults to `gemini-3.5-flash`
- `GEMINI_TEXT_MODEL`, defaults to `gemini-3.5-flash`
- `GEMINI_IMAGE_MODEL`, defaults to `gemini-3.1-flash-image`
- `GEMINI_THINKING_LEVEL`, defaults to `low`
- `NEWSLETTER_SEARCH_DEPTH`, defaults to `basic`
- `NEWSLETTER_MAX_RESULTS`, defaults to `5`
- `WEEKLY_NEWS_TOPIC`, defaults to `AI weekly news digest`
- `WEEKLY_NEWS_DAYS`, defaults to `7`
- `WEEKLY_NEWS_MAX_RESULTS`, defaults to `12`

## Operating Notes

- Start with `--dry-run` until artifacts look correct.
- Live research and generation call Gemini/Tavily APIs and may incur cost.
- Use Tavily for research by default to reserve Gemini quota for newsletter writing and infographic prompts.
- Weekly mode uses Tavily `topic: news` with a 7-day window, then Gemini writes a 6-8 story digest intended for a 5-10 minute read.
- Generate the infographic image with Gemini Nano Banana 2 (`gemini-3.1-flash-image`) after prompt generation.
- Image generation is non-blocking: if Gemini image quota is unavailable, keep the prompt artifact, record the error, and send the newsletter without the image.
- The HTML email embeds the project logo and generated infographic as inline Gmail images.
- Live Gmail delivery must only be run after explicit approval.
- Gmail API OAuth remains the default because Google recommends Sign in with Google over Gmail app passwords for account security.
- If a tool fails, read `run.log` and `errors.json`, fix the deterministic tool, rerun the failed stage, and update this workflow if a reusable lesson was learned.

## Edge Cases

- Missing topic: stop with a clear validation error.
- Missing live credentials: stop before making external calls.
- Empty research results: generate a structured error and do not draft unsupported claims.
- Gmail API failure: save the API status/body summary to `send_result.json` or `errors.json`.

## Weekly Scheduling

Register the Windows scheduled task once:

```powershell
powershell -ExecutionPolicy Bypass -File tools/register_weekly_newsletter_task.ps1
```

The task runs every Sunday at 10:00 AM and executes:

```powershell
py tools/run_newsletter_pipeline.py --weekly --live
```
