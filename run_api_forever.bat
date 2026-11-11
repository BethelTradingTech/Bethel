@echo off
setlocal
cd /d C:\BethelTradingTech
set BETHEL_ENVIRONMENT=PRODUCTION
:restart
REM Fail closed: never launch the API against a schema known to be incompatible.
C:\BethelTradingTech\.venv\Scripts\python.exe C:\BethelTradingTech\local_api_migrate.py
if errorlevel 1 (
  echo [BETHEL] Database preflight failed. API launch blocked.
  timeout /t 30 /nobreak >nul
  goto restart
)
C:\BethelTradingTech\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
echo [BETHEL] API process exited. Restarting after delay.
timeout /t 10 /nobreak >nul
goto restart
