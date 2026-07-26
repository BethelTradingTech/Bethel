@echo off

cd /d C:\BethelTradingTech

call .venv\Scripts\activate

uvicorn main:app --host 0.0.0.0 --port 8000
