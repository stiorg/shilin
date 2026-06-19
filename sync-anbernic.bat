@echo off
setlocal EnableExtensions

REM Sync Shilin Trainer to Anbernic RG34XXSP (muOS)

if exist credentials.txt (
    for /f "delims=" %%x in (credentials.txt) do set "%%x"
) else (
    echo Error: credentials.txt not found! Please create it.
    pause
    exit /b
)

if not "%~1"=="" set "DEVICE_IP=%~1"

set "REMOTE=%DEVICE_USER%@%DEVICE_IP%"
set "GAME_DIR=/mnt/mmc/ports/shilin-trainer"
set "LAUNCHER=/mnt/mmc/ROMS/Ports/ShilinTrainer.sh"

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
echo Syncing Shilin Trainer to %REMOTE%
echo   game files  -^> %GAME_DIR%/
echo   launcher    -^> %LAUNCHER%
echo.

python -c "import pathlib; root=pathlib.Path('port'); [p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n').replace(b'\r',b'\n')) for p in root.glob('*.sh')]" 2>nul
if errorlevel 1 (
    echo WARN: could not normalize .sh line endings via python
)

ssh "%REMOTE%" "mkdir -p '%GAME_DIR%/port' '%GAME_DIR%/game' '%GAME_DIR%/fonts' '%GAME_DIR%/decks'"

echo [1/6] main.py
scp "%~dp0main.py" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [2/6] game/
scp -r "%~dp0game" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [3/6] decks/
if exist "%~dp0decks" (
    scp -r "%~dp0decks" "%REMOTE%:%GAME_DIR%/" || goto :fail
) else (
    echo       skip — no decks folder
)

echo [4/7] fonts/
if exist "%~dp0fonts\NotoSansCJKtc-Regular.otf" (
    scp "%~dp0fonts\NotoSansCJKtc-Regular.otf" "%REMOTE%:%GAME_DIR%/fonts/" || goto :fail
) else if exist "%~dp0fonts\NotoSansTC-Regular.otf" (
    scp "%~dp0fonts\NotoSansTC-Regular.otf" "%REMOTE%:%GAME_DIR%/fonts/" || goto :fail
) else (
    echo       WARN — no CJK font in fonts/. Run: python scripts/download-fonts.py
)

if exist "%~dp0fonts\NotoSans-Regular.ttf" (
    scp "%~dp0fonts\NotoSans-Regular.ttf" "%REMOTE%:%GAME_DIR%/fonts/" || goto :fail
) else (
    echo       WARN — no Latin font in fonts/. Run: python scripts/download-fonts.py
)

echo [5/7] requirements.txt
scp "%~dp0requirements.txt" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [6/7] port/shilin-trainer.gptk
scp "%~dp0port\shilin-trainer.gptk" "%REMOTE%:%GAME_DIR%/port/" || goto :fail

echo [7/7] ShilinTrainer.sh launcher
scp "%~dp0port\shilin-trainer.sh" "%REMOTE%:%LAUNCHER%" || goto :fail

ssh "%REMOTE%" "chmod +x '%LAUNCHER%'" || goto :fail

echo.
echo Done. Launch from Explore Content -^> Ports -^> Shilin Trainer
echo Logs: ssh %REMOTE% "cat %GAME_DIR%/log.txt"
echo.
exit /b 0

:fail
echo.
echo SYNC FAILED. Check Wi-Fi, SSH enabled, and password ^(default: root^).
exit /b 1
