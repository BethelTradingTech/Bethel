$ErrorActionPreference = "Stop"
$taskName = "Bethel Read-Only Master Events"
$runner = Join-Path $PSScriptRoot "run_master_events.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Bethel master event publisher installed and started (read-only)." -ForegroundColor Green
