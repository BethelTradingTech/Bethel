$ErrorActionPreference = "Stop"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelSubscriberCopier"
$tokenFile = Join-Path $taskRoot "receiver-token.dpapi"
$settingsFile = Join-Path $taskRoot "settings.json"
$logFile = Join-Path $taskRoot "subscriber-copier.log"
$stateFile = Join-Path $taskRoot "subscriber-state.json"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$copier = Join-Path $PSScriptRoot "mt5_subscriber_copier.py"

if (-not (Test-Path $tokenFile)) { throw "Encrypted receiver token is missing." }
if (-not (Test-Path $settingsFile)) { throw "Subscriber copier settings are missing." }
$settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
$secureToken = ConvertTo-SecureString ((Get-Content $tokenFile -Raw).Trim())
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $env:BETHEL_RECEIVER_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:BETHEL_API_URL = "https://bethel-api.onrender.com"
    $env:BETHEL_SUBSCRIBER_ACCOUNT = $settings.account
    $env:BETHEL_SUBSCRIBER_MODE = $settings.mode
    $env:BETHEL_SUBSCRIBER_TERMINAL_PATH = $settings.terminal_path
    $env:BETHEL_ALLOW_LIVE = if ($settings.allow_live) { "true" } else { "false" }
    $env:BETHEL_COPIER_LOG = $logFile
    $env:BETHEL_COPIER_STATE = $stateFile
    Set-Location $projectRoot
    & $python -u $copier
} finally {
    $env:BETHEL_RECEIVER_TOKEN = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
