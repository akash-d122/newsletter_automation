# Newsletter Automation

This project follows the WAT framework described in [AGENTS.md](AGENTS.md):

- `workflows/` contains markdown SOPs.
- `tools/` contains deterministic Python execution scripts.
- `.tmp/` contains disposable intermediate files.
- `.env`, `credentials.json`, and `token.json` are local secret/auth files and should not be committed.

Local files are for processing. Final deliverables should live in the relevant cloud service.

## Run The Newsletter Pipeline

Dry-run mode is the default and does not call Gemini, Tavily, or Gmail:

```powershell
python tools/run_newsletter_pipeline.py "AI agents for small businesses" --recipients you@example.com
```

Artifacts are written to `.tmp/runs/<run_id>/`.

Live mode calls external APIs and sends email through Gmail API OAuth:

```powershell
python tools/run_newsletter_pipeline.py "AI agents for small businesses" --recipients you@example.com --live
```

Weekly AI digest mode researches top AI news from the last 7 days and targets a 5-10 minute read:

```powershell
python tools/run_newsletter_pipeline.py --weekly --live
```

Register the weekly Sunday 10:00 AM Windows scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File tools/register_weekly_newsletter_task.ps1
```

Required live credentials live in `.env`: `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GMAIL_SENDER_EMAIL`, `NEWSLETTER_DEFAULT_RECIPIENTS`, and `NEWSLETTER_FROM_NAME`. `TAVILY_API_KEY` is only required when `NEWSLETTER_RESEARCH_PROVIDER=tavily`.

The default research provider is Tavily, reserving Gemini quota for `gemini-3.5-flash` newsletter copy and `gemini-3.1-flash-image` infographic generation. Gmail delivery embeds the project logo and generated infographic as inline images through Gmail API OAuth.
