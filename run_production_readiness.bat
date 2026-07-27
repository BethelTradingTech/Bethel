@echo off
setlocal
cd /d "%~dp0"
set "BETHEL_ENVIRONMENT=PRODUCTION"
".venv\Scripts\python.exe" "tools\production_readiness.py"
exit /b %ERRORLEVEL%
