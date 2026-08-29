param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Telemetry", "Events")]
    [string]$Mode,

    [Parameter(Mandatory=$true)]
    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ConfigPath)) { throw "Master terminal config not found: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$instanceRoot = Split-Path -Parent $ConfigPath
$secretFile = Join-Path $instanceRoot "connector-secret.dpapi"
if (-not (Test-Path $secretFile)) { throw "Encrypted connector secret is missing: $secretFile" }

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Bethel virtual environment is missing: $python" }

$secureSecret = ConvertTo-SecureString ((Get-Content $secretFile -Raw).Trim())
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
    $env:MT5_CONNECTOR_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:BETHEL_API_URL = [string]$config.api_url
    $env:MT5_CONNECTOR_ID = [string]$config.connector_id
    $env:MT5_EVENT_CONNECTOR_ID = [string]$config.connector_id
    $env:BETHEL_MASTER_ACCOUNT = [string]$config.account_number
    $env:BETHEL_MT5_TERMINAL_PATH = [string]$config.terminal_path

    Set-Location $projectRoot

    if ($Mode -eq "Telemetry") {
        $env:BETHEL_CONNECTOR_LOG = Join-Path $instanceRoot "telemetry.log"
        $script = Join-Path $PSScriptRoot "mt5_readonly_connector.py"
    } else {
        $env:BETHEL_MASTER_EVENT_LOG = Join-Path $instanceRoot "master-events.log"
        $env:BETHEL_MASTER_EVENT_STATE = Join-Path $instanceRoot "master-events-state.json"
        $script = Join-Path $PSScriptRoot "mt5_master_event_publisher.py"
    }

    & $python -u $script
} finally {
    $env:MT5_CONNECTOR_SECRET = $null
    $env:BETHEL_API_URL = $null
    $env:MT5_CONNECTOR_ID = $null
    $env:MT5_EVENT_CONNECTOR_ID = $null
    $env:BETHEL_MASTER_ACCOUNT = $null
    $env:BETHEL_MT5_TERMINAL_PATH = $null
    $env:BETHEL_CONNECTOR_LOG = $null
    $env:BETHEL_MASTER_EVENT_LOG = $null
    $env:BETHEL_MASTER_EVENT_STATE = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
