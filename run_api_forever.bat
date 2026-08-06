@echo off
setlocal
cd /d C:\BethelTradingTech
set BETHEL_ENVIRONMENT=PRODUCTION
:restart
C:\BethelTradingTech\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
timeout /t 10 /nobreak >nul
goto restart
