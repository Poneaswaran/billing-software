@echo off
setlocal
echo ==============================================================================
echo   Building ToyPop POS & Billing Windows Installation Wizard
echo ==============================================================================

where pipenv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [*] Running build pipeline inside pipenv environment...
    pipenv run python build_installer.py
) else (
    echo [*] Running build pipeline with system Python...
    python build_installer.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUCCESS] Build completed! Installer is located in dist\installer\
pause
