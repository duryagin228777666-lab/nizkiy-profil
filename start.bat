@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo   Nizkiy Profil - server + Telegram bot
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python ne nayden. Ustanovite Python s https://python.org
  echo         pri ustanovke postavte galochku "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Sozdayu okruzhenie Python, podozhdite 1-2 minuty...
  py -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo [setup] Sozdan fayl .env. Otkroyte ego i vpishite BOT_TOKEN i OWNER_CHAT_ID.
  )
)

echo.
echo Server zapuskaetsya. Sayt: http://localhost:5000
echo Eto okno NE zakryvayte - poka ono otkryto, server rabotaet.
echo Chtoby ostanovit - zakroyte okno ili nazhmite Ctrl+C.
echo.

start "" cmd /c "timeout /t 3 >nul & start "" http://localhost:5000"

".venv\Scripts\python.exe" server\app.py

echo.
echo [!] Server ostanovlen ili proizoshla oshibka. Smotrite soobshcheniya vyshe.
pause
