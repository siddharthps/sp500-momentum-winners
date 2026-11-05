# Registers the monthly run (#17) with Windows Task Scheduler.
#   Starts every day at 07:00 (PC local time, before the 08:30 Central US open); the script itself
#   only works on a weekday when last month's picks are missing, so in practice it runs once, on
#   the first weekday of the month (or the first weekday the PC is on after that).
#   If the PC is off or asleep at 07:00, it starts as soon as possible afterwards.
# Remove it with:
#   Unregister-ScheduledTask -TaskName sp500-momentum-monthly-run -Confirm:$false

$name = "sp500-momentum-monthly-run"
$script = Join-Path $PSScriptRoot "monthly_run.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "Monthly S&P 500 momentum picks: fresh data, refit, picks (sp500-momentum-winners)" -Force
