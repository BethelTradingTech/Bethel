$ErrorActionPreference = "Stop"
$taskName = "Bethel Subscriber MT5 Copier"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelSubscriberCopier"
$tokenFile = Join-Path $taskRoot "receiver-token.dpapi"
$settingsFile = Join-Path $taskRoot "settings.json"
$runner = Join-Path $PSScriptRoot "run_subscriber_copier.ps1"
New-Item -ItemType Directory -Force -Path $taskRoot | Out-Null

$account = Read-Host "Subscriber MT5 account number"
if ($account -eq "49617874") { throw "Safety stop: master account cannot be configured as a subscriber." }
$mode = (Read-Host "Account mode (DEMO or LIVE)").ToUpperInvariant()
if ($mode -notin @("DEMO", "LIVE")) { throw "Mode must be DEMO or LIVE." }
$terminalPath = Read-Host "Full path to the SUBSCRIBER terminal64.exe"
if (-not (Test-Path $terminalPath)) { throw "Subscriber terminal executable was not found." }
$allowLive = $false
if ($mode -eq "LIVE") {
    $confirmation = Read-Host "Type ENABLE LIVE COPYING $account"
    if ($confirmation -ne "ENABLE LIVE COPYING $account") { throw "Live-copy confirmation did not match." }
    $allowLive = $true
}
$token = Read-Host "Paste the one-time Bethel receiver token" -AsSecureString
Set-Content -Path $tokenFile -Value (ConvertFrom-SecureString $token) -Encoding UTF8 -NoNewline
@{ account = $account; mode = $mode; terminal_path = $terminalPath; allow_live = $allowLive } | ConvertTo-Json | Set-Content -Path $settingsFile -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Bethel subscriber copier installed. It remains controlled by the server pause and activation gates." -ForegroundColor Green
