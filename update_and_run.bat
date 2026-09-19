@echo off
REM Double-click this file to: pull the latest code, then launch JARVIS.
REM Works from wherever it's double-clicked from - always operates on the
REM folder this .bat file itself lives in, not whatever folder was open.

cd /d "%~dp0"

echo ============================================
echo  Updating...
echo ============================================
git pull origin claude/bold-shannon-s2myjt
if errorlevel 1 (
    echo.
    echo [!] Update failed - see the error above.
    echo     Common causes: git is not installed, this folder is not a
    echo     git clone of the repo, or there are uncommitted local changes
    echo     blocking the pull.
    echo     Continuing to launch with whatever code is already here...
    echo.
)

echo.
echo ============================================
echo  Starting JARVIS...
echo ============================================

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

python run.py

echo.
echo JARVIS closed. Press any key to close this window.
pause >nul
