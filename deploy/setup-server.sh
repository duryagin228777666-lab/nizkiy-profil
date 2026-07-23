#!/bin/bash
# Первичная настройка VPS (Ubuntu 22.04 / 24.04).
# Запуск на сервере: sudo bash deploy/setup-server.sh

set -euo pipefail

APP_DIR="/opt/nizkiy-profil"
DOMAIN="${1:-nizkiyprofil.ru}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Запустите от root: sudo bash deploy/setup-server.sh [домен]"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Обновление пакетов..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg nginx certbot python3-certbot-nginx ufw

echo "==> Установка Docker..."
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

systemctl enable docker
systemctl start docker

echo "==> Файрвол (SSH, HTTP, HTTPS)..."
ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Папка проекта: ${APP_DIR}"
mkdir -p "${APP_DIR}"

if [ ! -f "${APP_DIR}/docker-compose.yml" ]; then
  echo "    Скопируйте файлы проекта в ${APP_DIR} (WinSCP или deploy-vps.bat)."
fi

if [ -f "${APP_DIR}/deploy/nginx-site.conf" ]; then
  sed "s/nizkiyprofil.ru/${DOMAIN}/g; s/www.nizkiyprofil.ru/www.${DOMAIN}/g" \
    "${APP_DIR}/deploy/nginx-site.conf" > /etc/nginx/sites-available/nizkiy-profil
  ln -sf /etc/nginx/sites-available/nizkiy-profil /etc/nginx/sites-enabled/nizkiy-profil
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable nginx
  systemctl reload nginx
fi

echo ""
echo "============================================================"
echo "  Сервер готов."
echo "  1) Загрузите проект в ${APP_DIR}"
echo "  2) Создайте ${APP_DIR}/.env (см. .env.example)"
echo "  3) В DNS домена укажите A-запись на IP этого сервера"
echo "  4) Запустите: cd ${APP_DIR} && sudo bash deploy/deploy.sh"
echo "  5) SSL: sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "============================================================"
