@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe was not found.
    exit /b 1
)
echo.
echo Bethel Trading Technologies Automated Validation
echo The API must already be running on port 8000.
echo No payment, KYC approval, MT5 connection, trade, or withdrawal will be executed.
echo.
".venv\Scripts\python.exe" "tools\run_system_tests.py" --email "test@example.com"
set "TEST_EXIT=%ERRORLEVEL%"
echo.
if "%TEST_EXIT%"=="0" (
    echo AUTOMATED SYSTEM VALIDATION PASSED
) else (
    echo AUTOMATED SYSTEM VALIDATION FOUND A FAILURE
)
exit /b %TEST_EXIT%
