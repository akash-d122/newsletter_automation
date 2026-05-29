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

Required live credentials live in `.env`: `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GMAIL_SENDER_EMAIL`, `NEWSLETTER_DEFAULT_RECIPIENTS`, and `NEWSLETTER_FROM_NAME`. `TAVILY_API_KEY` is only required when `NEWSLETTER_RESEARCH_PROVIDER=tavily`.

The default research provider is Tavily, reserving Gemini quota for `gemini-3.5-flash` newsletter copy and infographic prompt generation. Gmail delivery stays on Gmail API OAuth because Google recommends Sign in with Google instead of app passwords for account security.
