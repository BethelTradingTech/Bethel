$ErrorActionPreference = "Stop"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelConnector"
$secretFile = Join-Path $taskRoot "connector-secret.dpapi"
$logFile = Join-Path $taskRoot "connector.log"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$connector = Join-Path $PSScriptRoot "mt5_readonly_connector.py"

if (-not (Test-Path $secretFile)) { throw "Encrypted connector secret is missing. Run install_connector_task.ps1." }
if (-not (Test-Path $python)) { throw "Bethel virtual environment is missing: $python" }

$secureSecret = Get-Content $secretFile -Raw | ConvertTo-SecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
    $env:MT5_CONNECTOR_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:BETHEL_API_URL = "https://bethel-api.onrender.com"
    $env:BETHEL_CONNECTOR_LOG = $logFile
    Set-Location $projectRoot
    & $python -u $connector
} finally {
    $env:MT5_CONNECTOR_SECRET = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
