@echo off
REM Start the EasyHire development server.
REM
REM Prefers the project virtual environment (.venv), which carries the
REM Python 3.12 + pinned packages the project was built and tested
REM against. Falls back to whatever "python" is on PATH so the script
REM still works on a machine that has not created the venv yet.

REM Run from the folder this script lives in, so double-clicking works
REM no matter what the current directory happens to be.
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage.py runserver %*
) else (
    echo [run.bat] No .venv found - using "python" from PATH instead.
    echo [run.bat] To create it:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    echo.
    python manage.py runserver %*
)

pause
