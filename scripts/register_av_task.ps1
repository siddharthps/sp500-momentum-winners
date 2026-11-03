# Registers the daily Alpha Vantage pull with Windows Task Scheduler.
#   Runs every day at 21:00 (PC local time) while you're logged on. If the PC was off or asleep
#   at 21:00, it runs as soon as possible afterwards.
#   Moved from 09:00 on 3 Nov 2026: the free tier's 25-call limit looked like a rolling 24 hours,
#   and the PC was usually off at 09:00 but on in the evening.
# Remove it when the queue is empty:
#   Unregister-ScheduledTask -TaskName sp500-momentum-av-pull -Confirm:$false

$name = "sp500-momentum-av-pull"
$script = Join-Path $PSScriptRoot "av_pull_daily.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00pm
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "Daily Alpha Vantage pull of delisted S&P 500 members (sp500-momentum-winners)" -Force
