$ErrorActionPreference = "Stop"
$taskName = "Bethel Read-Only MT5 Connector"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelConnector"
$secretFile = Join-Path $taskRoot "connector-secret.dpapi"
$runner = Join-Path $PSScriptRoot "run_connector.ps1"
$python = Join-Path (Split-Path -Parent $PSScriptRoot) ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) { throw "Run .venv setup before installing the connector task." }
New-Item -ItemType Directory -Force -Path $taskRoot | Out-Null

$secret = Read-Host "Paste MT5_CONNECTOR_SECRET (input is hidden)" -AsSecureString
$encrypted = ConvertFrom-SecureString $secret
if ($encrypted.Length -lt 64) { throw "The connector secret was not captured correctly." }
Set-Content -Path $secretFile -Value $encrypted -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Bethel connector startup task installed and started." -ForegroundColor Green
Write-Host "Status: Get-ScheduledTask -TaskName '$taskName'"
Write-Host "Log: Get-Content '$taskRoot\connector.log' -Tail 20"
