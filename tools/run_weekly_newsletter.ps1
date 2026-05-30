$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runId = "weekly-ai-news-$timestamp"
$logDir = Join-Path $ProjectRoot ".tmp\scheduler"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir "$runId.log"

py tools/run_newsletter_pipeline.py --weekly --live --run-id $runId *> $logPath
