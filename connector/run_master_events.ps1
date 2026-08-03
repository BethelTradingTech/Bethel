$ErrorActionPreference = "Stop"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelConnector"
$secretFile = Join-Path $taskRoot "connector-secret.dpapi"
$logFile = Join-Path $taskRoot "master-events.log"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$publisher = Join-Path $PSScriptRoot "mt5_master_event_publisher.py"

if (-not (Test-Path $secretFile)) { throw "Install the read-only connector first; its encrypted secret is required." }
$secureSecret = ConvertTo-SecureString ((Get-Content $secretFile -Raw).Trim())
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
    $env:MT5_CONNECTOR_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:BETHEL_API_URL = "https://bethel-api.onrender.com"
    $env:BETHEL_MASTER_ACCOUNT = "49617874"
    $env:BETHEL_MASTER_EVENT_LOG = $logFile
    Set-Location $projectRoot
    & $python -u $publisher
} finally {
    $env:MT5_CONNECTOR_SECRET = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
