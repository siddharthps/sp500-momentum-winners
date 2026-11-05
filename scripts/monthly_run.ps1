# The monthly run (#17), started every morning at 07:00 by Windows Task Scheduler
# (task "sp500-momentum-monthly-run"), but it only does anything on a weekday when last month's
# picks don't exist yet. In practice that's the first weekday of each month, or the first
# weekday the PC is on after that (catch-up). Appends to logs/monthly_run.log. Safe to run by hand.
# Register the task with scripts/register_monthly_task.ps1.

param([switch]$Force)  # -Force: run now even if this month's picks exist (redoes them)

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
$today = Get-Date
$decisionMonth = $today.AddMonths(-1).ToString("yyyy-MM")
$picks = Join-Path $repo "reports\picks\picks_$decisionMonth.csv"

if (-not $Force) {
    if ($today.DayOfWeek -in @("Saturday", "Sunday")) { exit 0 }  # wait for a weekday
    if (Test-Path $picks) { exit 0 }  # already done this month
}

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "monthly_run.log"
$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uv)) { $uv = "uv" }

Set-Location $repo
$env:NO_COLOR = "1"
"===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (picks for decisions at the end of $decisionMonth) =====" |
    Out-File -Append -Encoding utf8 $log
$extra = @()
if ($Force) { $extra = @("--force") }
& $uv run python -m sp500_momentum.modeling.predict run @extra 2>&1 | ForEach-Object { "$_" } |
    Out-File -Append -Encoding utf8 $log
"exit code: $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
exit $LASTEXITCODE
