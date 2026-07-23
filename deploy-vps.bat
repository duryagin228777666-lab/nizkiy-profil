@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   Загрузка сайта на VPS (российский сервер)
echo ============================================================
echo.

if not exist ".env" (
  echo [ERROR] Нет файла .env — заполните BOT_TOKEN и другие поля.
  pause
  exit /b 1
)

where scp >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Не найден scp. В Windows: Параметры -^> Приложения -^> Доп. компоненты -^> OpenSSH Client.
  pause
  exit /b 1
)

set /p VPS_HOST="IP или домен сервера: "
set /p VPS_USER="Логин SSH (обычно root): "
if "%VPS_USER%"=="" set VPS_USER=root
set /p VPS_DOMAIN="Ваш домен (например nizkiyprofil.ru): "

set REMOTE_DIR=/opt/nizkiy-profil

echo.
echo Загружаю файлы на %VPS_USER%@%VPS_HOST%:%REMOTE_DIR% ...
echo Пароль SSH спросит один или несколько раз.
echo.

ssh %VPS_USER%@%VPS_HOST% "mkdir -p %REMOTE_DIR%"

scp -r ^
  assets ^
  index.html about.html services.html gallery.html price.html contacts.html ^
  faq.html privacy.html recommendations.html shinomontazh.html prodazha-shin.html ^
  vibrocontrol.html balansirovka.html pravka-diskov.html argonnaya-svarka.html ^
  pokraska-diskov.html hranenie-shin.html ^
  styles.css script.js robots.txt requirements.txt Dockerfile docker-compose.yml ^
  .env .env.example .dockerignore ^
  server deploy ^
  %VPS_USER%@%VPS_HOST%:%REMOTE_DIR%/

if errorlevel 1 (
  echo.
  echo [ERROR] Ошибка загрузки. Проверьте IP, логин и что SSH открыт на сервере.
  pause
  exit /b 1
)

echo.
echo Настраиваю сервер и запускаю сайт...
ssh %VPS_USER%@%VPS_HOST% "cd %REMOTE_DIR% && chmod +x deploy/deploy.sh deploy/setup-server.sh && sudo bash deploy/setup-server.sh %VPS_DOMAIN% && sudo bash deploy/deploy.sh"

echo.
echo ============================================================
echo   Готово.
echo   Сайт на сервере: http://%VPS_HOST%:8080 (внутренний)
echo   После привязки DNS включите HTTPS на сервере:
echo     sudo certbot --nginx -d %VPS_DOMAIN% -d www.%VPS_DOMAIN%
echo   Подробнее: ИНСТРУКЦИЯ-VPS.md
echo ============================================================
echo.
pause
