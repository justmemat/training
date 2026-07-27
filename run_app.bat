@echo off
setlocal

rem Always work beside this file, even when the folder name contains spaces.
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto install

echo Creating a private Python environment in .venv ...
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 goto no_python

:install
echo Installing or checking application dependencies ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto install_failed

echo Starting Training Tracker ...
".venv\Scripts\python.exe" -m streamlit run main.py
goto end

:no_python
echo.
echo Python 3 was not found. Install it from https://www.python.org/downloads/
echo Select "Add Python to PATH" during installation, then run this file again.
pause
exit /b 1

:install_failed
echo.
echo Streamlit could not be installed. Check your internet or proxy connection.
echo If your organization manages software, ask IT to permit Python packages from pypi.org.
pause
exit /b 1

:end
endlocal
