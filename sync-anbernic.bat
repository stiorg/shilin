@echo off
setlocal EnableExtensions

REM Incremental code sync to Anbernic (only changed files are uploaded)

cd /d "%~dp0"

where python >nul 2>&1 || (
    echo ERROR: python not found.
    exit /b 1
)
where ssh >nul 2>&1 || (
    echo ERROR: ssh not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)
where scp >nul 2>&1 || (
    echo ERROR: scp not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)

set "ARGS="
if /I "%~1"=="--force" set "ARGS=--force"
if not "%~1"=="" if /I not "%~1"=="--force" set "ARGS=--ip %~1"
if /I "%~2"=="--force" set "ARGS=%ARGS% --force"

python "%~dp0scripts\sync-anbernic.py" %ARGS% || (
    echo.
    echo SYNC FAILED. Check Wi-Fi, SSH enabled, and credentials.txt.
    exit /b 1
)
exit /b 0
