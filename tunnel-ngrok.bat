@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "NGROK=C:\Users\daniil\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
if not exist "%NGROK%" set "NGROK=ngrok"

echo ============================================================
echo   Публикация через ngrok
echo ============================================================
echo.
echo VPN vykluchite! Server start.bat dolzhen rabotat na :5000
echo.

if "%~1"=="" (
  echo Vstavte token s https://dashboard.ngrok.com/get-started/your-authtoken
  set /p TOKEN=Token ngrok: 
) else (
  set "TOKEN=%~1"
)

"%NGROK%" config add-authtoken %TOKEN%
echo.
echo Zapuskayu tunnel...
echo Ne zakryvayte eto okno!
echo.
"%NGROK%" http 5000
pause
