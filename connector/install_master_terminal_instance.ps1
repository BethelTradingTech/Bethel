param(
    [Parameter(Mandatory=$true)]
    [string]$AccountNumber,

    [Parameter(Mandatory=$true)]
    [string]$ConnectorId,

    [Parameter(Mandatory=$true)]
    [string]$TerminalPath,

    [string]$ApiUrl = "https://bethel-api.onrender.com"
)

$ErrorActionPreference = "Stop"

if ($AccountNumber -notmatch '^[0-9]{5,32}$') { throw "AccountNumber must contain 5-32 digits." }
if ($ConnectorId -notmatch '^[A-Za-z0-9._-]{3,100}$') { throw "ConnectorId contains unsupported characters." }
if (-not (Test-Path $TerminalPath)) { throw "MT5 terminal executable was not found: $TerminalPath" }
if ((Split-Path $TerminalPath -Leaf) -ne "terminal64.exe") { throw "TerminalPath must point to terminal64.exe" }

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$runner = Join-Path $PSScriptRoot "run_master_terminal_instance.ps1"
if (-not (Test-Path $python)) { throw "Bethel virtual environment is missing: $python" }
if (-not (Test-Path $runner)) { throw "Multi-master runner is missing: $runner" }

$root = Join-Path $env:LOCALAPPDATA "BethelConnector\Masters"
$instanceRoot = Join-Path $root $AccountNumber
$configFile = Join-Path $instanceRoot "config.json"
$secretFile = Join-Path $instanceRoot "connector-secret.dpapi"
New-Item -ItemType Directory -Force -Path $instanceRoot | Out-Null

$config = [ordered]@{
    account_number = $AccountNumber
    connector_id = $ConnectorId
    terminal_path = (Resolve-Path $TerminalPath).Path
    api_url = $ApiUrl.TrimEnd('/')
}
$config | ConvertTo-Json | Set-Content -Path $configFile -Encoding UTF8

$secret = Read-Host "Paste MT5_CONNECTOR_SECRET (input is hidden)" -AsSecureString
$encrypted = ConvertFrom-SecureString $secret
if ($encrypted.Length -lt 64) { throw "The connector secret was not captured correctly." }
Set-Content -Path $secretFile -Value $encrypted -Encoding UTF8 -NoNewline

$telemetryTask = "Bethel MT5 Master $AccountNumber Telemetry"
$eventsTask = "Bethel MT5 Master $AccountNumber Events"
$user = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

function Install-BethelTask([string]$TaskName, [string]$Mode) {
    $arguments = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Mode $Mode -ConfigPath `"$configFile`""
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}

Install-BethelTask -TaskName $telemetryTask -Mode "Telemetry"
Install-BethelTask -TaskName $eventsTask -Mode "Events"

Write-Host "Master terminal instance installed safely." -ForegroundColor Green
Write-Host "Account: $AccountNumber"
Write-Host "Connector: $ConnectorId"
Write-Host "MT5: $($config.terminal_path)"
Write-Host "Telemetry task: $telemetryTask"
Write-Host "Events task: $eventsTask"
Write-Host "Config: $configFile"
Write-Host "The tasks start paused at the CopyHub package layer until Super Admin maps and resumes a package channel." -ForegroundColor Yellow
