@echo off
title Bethel Trading Technologies - Database Reset

cd /d C:\BethelTradingTech

echo ======================================
echo Bethel Trading Technologies
echo Database Reset Tool
echo ======================================

echo.
echo Stopping FastAPI server...
taskkill /F /IM python.exe >nul 2>&1

echo.
echo Deleting database...
if exist bethel_trading.db del bethel_trading.db

echo.
echo Starting FastAPI...

call .venv\Scripts\activate

uvicorn api.main:app --reload