# Daily Alpha Vantage pull, run by Windows Task Scheduler (task "sp500-momentum-av-pull").
# Appends each run's output to logs/av_pull.log. Safe to run by hand too.
# Register the task with scripts/register_av_task.ps1.

param([int]$MaxCalls = 23)  # -MaxCalls 0 tests the setup without using any API calls

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "av_pull.log"

$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uv)) { $uv = "uv" }

Set-Location $repo
$env:NO_COLOR = "1"
"===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File -Append -Encoding utf8 $log
& $uv run python -m sp500_momentum.dataset av-pull --max-calls $MaxCalls 2>&1 | ForEach-Object { "$_" } | Out-File -Append -Encoding utf8 $log
"exit code: $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
exit $LASTEXITCODE
