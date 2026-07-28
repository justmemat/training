@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo -----------------------------------------
echo  Task Tracker Upgrade
echo -----------------------------------------

echo Performing installation...
taskkill /IM MAT.exe /F >nul 2>&1
taskkill /IM flet.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

set "TARGET=C:\\OSFTOOLS\\MAT\\MAT.exe"
set "SOURCE_DIR=T:\\File Dump\\BZ\\MAT"
set "SOURCE_FILE=MAT.exe"
set "VERSION_FILE=%SOURCE_DIR%\\verchek.txt"
set "INSTALL_VERSION="
set "TARGET_DIR=C:\\OSFTOOLS\\MAT"
set "STAGING_FILE=MAT.new.exe"
set "STAGING_PATH=%TARGET_DIR%\\%STAGING_FILE%"
set "BACKUP_FILE=MAT.old.exe"
set "BACKUP_PATH=%TARGET_DIR%\\%BACKUP_FILE%"

if not exist "%SOURCE_DIR%" (
    echo ERROR: Source directory not found at "%SOURCE_DIR%".
    echo Please confirm the network drive is mapped and accessible.
    pause
    exit /b 1
)

if exist "%SOURCE_DIR%\\%SOURCE_FILE%" (
    if exist "%VERSION_FILE%" (
        set /p INSTALL_VERSION=<"%VERSION_FILE%"
    )
    if defined INSTALL_VERSION (
        echo Installing Version !INSTALL_VERSION!...
        echo Downloading version !INSTALL_VERSION!...
    ) else (
        echo Installing Version unknown...
        echo Downloading Task Tracker update...
    )
    echo Please be patient...

    if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

    robocopy "%SOURCE_DIR%" "%TARGET_DIR%" "%SOURCE_FILE%" /R:2 /W:1 /NJH /NJS /TEE /ETA /XF "%STAGING_FILE%" "%BACKUP_FILE%"

    if %ERRORLEVEL% GEQ 8 (
        echo ERROR: File copy failed. ErrorLevel %ERRORLEVEL%.
        pause
        exit /b 1
    )

    move /Y "%TARGET_DIR%\\%SOURCE_FILE%" "%STAGING_PATH%" >nul
    if not exist "%STAGING_PATH%" (
        echo ERROR: Staging file not created at "%STAGING_PATH%".
        pause
        exit /b 1
    )
) else (
    echo ERROR: Source Task Tracker not found at "%SOURCE_DIR%\\%SOURCE_FILE%"
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo Checking current version...
    if exist "%BACKUP_PATH%" del "%BACKUP_PATH%"
    move /Y "%TARGET%" "%BACKUP_PATH%" >nul
)

move /Y "%STAGING_PATH%" "%TARGET%" >nul
if not exist "%TARGET%" (
    echo ERROR: Failed to place new Task Tracker executable.
    if exist "%BACKUP_PATH%" move /Y "%BACKUP_PATH%" "%TARGET%" >nul
    pause
    exit /b 1
)

echo Creating desktop shortcut...

for /f "usebackq tokens=*" %%D in (`powershell -command "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')"`) do (
    set "DESKTOP_PATH=%%D"
)

set "SHORTCUT_PATH=%DESKTOP_PATH%\\MAT.lnk"
set "SHORTCUT_TARGET=C:\\OSFTOOLS\\MAT\\MAT.exe"

if exist "%SHORTCUT_PATH%" (
    echo Shortcut already exists at "%SHORTCUT_PATH%".
) else (
    echo Creating shortcut at "%SHORTCUT_PATH%"...
    powershell -command ^
      "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');" ^
      "$s.TargetPath='%SHORTCUT_TARGET%';" ^
      "$s.WorkingDirectory='C:\\OSFTOOLS\\MAT';" ^
      "$s.WindowStyle=1;" ^
      "$s.Save()"
)

echo -----------------------------------------
echo  Update Complete...
echo -----------------------------------------

pause
