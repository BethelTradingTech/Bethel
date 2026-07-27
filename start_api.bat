@echo off
setlocal
cd /d C:\BethelTradingTech
set "BETHEL_ENVIRONMENT=PRODUCTION"
call .venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
