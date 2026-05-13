@echo off
setlocal

py -3 -m pip install -r requirements-build.txt
if errorlevel 1 exit /b %errorlevel%

py -3 -m PyInstaller --clean --noconfirm ChessStudio.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Built dist\ChessStudio.exe
