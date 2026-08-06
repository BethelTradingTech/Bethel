$project = "C:\BethelTradingTech"
$python = "$project\.venv\Scripts\python.exe"
$log = "$project\api-watchdog.log"

Set-Location $project

while ($true) {
    try {
        $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue

        if (-not $listener) {
            Add-Content $log "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Bethel API"

            $process = Start-Process `
                -FilePath $python `
                -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" `
                -WorkingDirectory $project `
                -RedirectStandardOutput "$project\uvicorn-output.log" `
                -RedirectStandardError "$project\uvicorn-error.log" `
                -PassThru `
                -WindowStyle Hidden

            $process.WaitForExit()

            Add-Content $log "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] API stopped. Restarting."
        }
    }
    catch {
        Add-Content $log "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Error: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 5
}
