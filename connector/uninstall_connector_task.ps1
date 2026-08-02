$taskName = "Bethel Read-Only MT5 Connector"
$taskRoot = Join-Path $env:LOCALAPPDATA "BethelConnector"
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item (Join-Path $taskRoot "connector-secret.dpapi") -Force -ErrorAction SilentlyContinue
Write-Host "Bethel connector startup task removed." -ForegroundColor Yellow
