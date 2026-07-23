@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PATH=%PATH%;%USERPROFILE%\.fly\bin"

echo ============================================================
echo   Публикация сайта на Fly.io
echo ============================================================
echo.

flyctl auth whoami >nul 2>nul
if errorlevel 1 (
  echo Откроется браузер для входа в Fly.io...
  flyctl auth login
)

if not exist ".env" (
  echo [ERROR] Нет файла .env
  pause
  exit /b 1
)

echo Загружаю BOT_TOKEN и другие настройки...
flyctl secrets import < .env

echo.
echo Деплой на сервер (подождите 3-5 минут)...
flyctl deploy --ha=false

echo.
echo Ваш сайт:
flyctl open
pause
