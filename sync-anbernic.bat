@echo off
setlocal EnableExtensions

REM Sync Bopomofo to Anbernic RG34XXSP (muOS)

if exist credentials.txt (
    for /f "delims=" %%x in (credentials.txt) do set "%%x"
) else (
    echo Error: credentials.txt not found! Please create it.
    pause
    exit /b
)

if not "%~1"=="" set "DEVICE_IP=%~1"

set "REMOTE=%DEVICE_USER%@%DEVICE_IP%"
set "GAME_DIR=/mnt/mmc/ports/bopomofo"
set "LAUNCHER=/mnt/mmc/ROMS/Ports/Bopomofo.sh"

cd /d "%~dp0"

where scp >nul 2>&1 || (
    echo ERROR: scp not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)
where ssh >nul 2>&1 || (
    echo ERROR: ssh not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)

echo.
echo Syncing to %REMOTE%
echo   game files  -^> %GAME_DIR%/
echo   launcher    -^> %LAUNCHER%
echo.

python -c "import pathlib; root=pathlib.Path('port'); [p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n').replace(b'\r',b'\n')) for p in root.glob('*.sh')]" 2>nul
if errorlevel 1 (
    echo WARN: could not normalize .sh line endings via python
)

ssh "%REMOTE%" "mkdir -p '%GAME_DIR%/port' '%GAME_DIR%/game' '%GAME_DIR%/fonts'"

echo [1/5] main.py
scp "%~dp0main.py" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [2/5] game/
scp -r "%~dp0game" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [3/5] requirements.txt
scp "%~dp0requirements.txt" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [4/5] port/bopomofo.gptk
scp "%~dp0port\bopomofo.gptk" "%REMOTE%:%GAME_DIR%/port/" || goto :fail

echo [5/5] Bopomofo.sh launcher
scp "%~dp0port\bopomofo.sh" "%REMOTE%:%LAUNCHER%" || goto :fail

ssh "%REMOTE%" "chmod +x '%LAUNCHER%'" || goto :fail

echo.
echo Done. Launch from Explore Content -^> Ports -^> Bopomofo
echo Logs: ssh %REMOTE% "cat %GAME_DIR%/log.txt"
echo.
exit /b 0

:fail
echo.
echo SYNC FAILED. Check Wi-Fi, SSH enabled, and password ^(default: root^).
exit /b 1
