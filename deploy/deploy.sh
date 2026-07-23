#!/bin/bash
# Сборка и запуск на VPS. Запуск: cd /opt/nizkiy-profil && sudo bash deploy/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f ".env" ]; then
  echo "[ERROR] Нет файла .env — скопируйте .env.example и заполните."
  exit 1
fi

if ! grep -q '^BOT_TOKEN=.\+' .env 2>/dev/null; then
  echo "[WARN] BOT_TOKEN пустой — бот не будет работать."
fi

if ! grep -q '^SITE_URL=https\?://' .env 2>/dev/null; then
  echo "[WARN] SITE_URL не задан — для SEO укажите https://ваш-домен.ru в .env"
fi

mkdir -p server
if [ ! -f server/bookings.json ]; then
  echo '{"seq":0,"bookings":[]}' > server/bookings.json
fi

echo "==> Сборка Docker-образа..."
docker compose build

echo "==> Запуск контейнера..."
docker compose up -d

echo "==> Проверка..."
sleep 2
if curl -fsS http://127.0.0.1:8080/api/health >/dev/null; then
  echo "OK: приложение отвечает на порту 8080"
  curl -s http://127.0.0.1:8080/api/health
  echo ""
else
  echo "[ERROR] Приложение не отвечает. Логи:"
  docker compose logs --tail=50
  exit 1
fi

echo ""
echo "Готово. Если nginx настроен — откройте сайт в браузере."
