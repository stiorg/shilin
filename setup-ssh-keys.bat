@echo off
setlocal EnableExtensions

REM One-time setup: passwordless SSH to Anbernic (muOS)

if exist credentials.txt (
    for /f "delims=" %%x in (credentials.txt) do set "%%x"
) else (
    echo Error: credentials.txt not found! Please create it.
    pause
    exit /b
)
if not "%~1"=="" set "DEVICE_IP=%~1"

set "REMOTE=%DEVICE_USER%@%DEVICE_IP%"
set "KEY=%USERPROFILE%\.ssh\id_ed25519"
set "PUB=%KEY%.pub"

where ssh >nul 2>&1 || (
    echo ERROR: ssh not found. Install OpenSSH Client in Windows Optional Features.
    exit /b 1
)

if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"

if not exist "%KEY%" (
    echo Creating SSH key at %KEY%
    ssh-keygen -t ed25519 -f "%KEY%" -N "" -C "bopomofo-sync"
    if errorlevel 1 exit /b 1
) else (
    echo Using existing key: %KEY%
)

echo.
echo Copying public key to %REMOTE% ^(enter root password one last time^)...
type "%PUB%" | ssh "%REMOTE%" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
if errorlevel 1 (
    echo FAILED. Check IP, SSH enabled on device, and password.
    exit /b 1
)

echo.
echo Testing passwordless login...
ssh -o BatchMode=yes -o ConnectTimeout=5 "%REMOTE%" "echo OK"
if errorlevel 1 (
    echo WARN: key login failed — muOS may need sshd config change.
    echo Try manually: ssh %REMOTE%
    exit /b 1
)

echo.
echo Done. sync-anbernic.bat should no longer ask for a password.
exit /b 0
