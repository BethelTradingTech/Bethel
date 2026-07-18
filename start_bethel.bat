@echo off 
title Bethel Trading Technologies Quant Platform 
cd /d C:\BethelTradingTech 
call .venv\Scripts\activate 
echo Starting Bethel Trading Technologies API... 
uvicorn api.main:app --reload 
pause 
