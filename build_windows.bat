@echo off
setlocal

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo Python was not found.
        echo Install Python from https://www.python.org/downloads/windows/
        echo During install, check "Add python.exe to PATH", then reopen PowerShell.
        exit /b 1
    )
)

%PYTHON_CMD% -m pip install -r requirements-build.txt
if errorlevel 1 exit /b %errorlevel%

%PYTHON_CMD% -m PyInstaller --clean --noconfirm ChessStudio.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Built dist\ChessStudio.exe
