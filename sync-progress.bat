@echo off
setlocal EnableExtensions

REM Bidirectional SRS progress sync (card-level merge, latest review wins)

if exist credentials.txt (
    for /f "delims=" %%x in (credentials.txt) do set "%%x"
) else (
    echo Error: credentials.txt not found! Please create it.
    pause
    exit /b 1
)

if not "%~1"=="" set "DEVICE_IP=%~1"

set "REMOTE=%DEVICE_USER%@%DEVICE_IP%"
set "GAME_DIR=/mnt/mmc/ports/shilin-trainer"
set "REMOTE_BPM=%TEMP%\shilin-remote-bopomofo_srs_data.json"
set "REMOTE_FC=%TEMP%\shilin-remote-flashcard_srs_data.json"

cd /d "%~dp0"

where scp >nul 2>&1 || (
    echo ERROR: scp not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)
where ssh >nul 2>&1 || (
    echo ERROR: ssh not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)
where python >nul 2>&1 || (
    echo ERROR: python not found.
    exit /b 1
)

echo.
echo Syncing PROGRESS with %REMOTE% (both ways)
echo   merge rule: per card, latest review wins
echo   code/UI is not deployed - use sync-anbernic.bat for that
echo.

echo [1/4] Fetch progress from device...
scp "%REMOTE%:%GAME_DIR%/bopomofo_srs_data.json" "%REMOTE_BPM%" >nul 2>&1
if errorlevel 1 (
    echo       no remote bopomofo_srs_data.json yet - treating as empty
    del "%REMOTE_BPM%" >nul 2>&1
)
scp "%REMOTE%:%GAME_DIR%/flashcard_srs_data.json" "%REMOTE_FC%" >nul 2>&1
if errorlevel 1 (
    echo       no remote flashcard_srs_data.json yet - treating as empty
    del "%REMOTE_FC%" >nul 2>&1
)

echo [2/4] Merge card progress (PC + device)...
python "%~dp0scripts\sync-progress.py" --remote-bpm "%REMOTE_BPM%" --remote-fc "%REMOTE_FC%" || goto :fail

echo [3/4] Push merged progress to device...
scp "%~dp0bopomofo_srs_data.json" "%REMOTE%:%GAME_DIR%/" || goto :fail
scp "%~dp0flashcard_srs_data.json" "%REMOTE%:%GAME_DIR%/" || goto :fail

echo [4/4] Cleanup temp files...
del "%REMOTE_BPM%" >nul 2>&1
del "%REMOTE_FC%" >nul 2>&1

echo.
echo Done. Both PC and device now share the merged progress.
echo Close Shilin Trainer on both sides before syncing next time.
echo.
exit /b 0

:fail
echo.
echo SYNC FAILED. Check Wi-Fi, SSH, and that the game is closed on both devices.
exit /b 1
