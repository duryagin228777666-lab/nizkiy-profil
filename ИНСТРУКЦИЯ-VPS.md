# Публикация сайта на российском VPS

Пошаговая инструкция для Timeweb, Beget, Reg.ru, Selectel и других VPS на **Ubuntu 22.04 / 24.04**.

Сервер отдаёт сайт, принимает заявки и запускает Telegram-бота в одном Docker-контейнере. Снаружи стоит **nginx** с бесплатным SSL (Let's Encrypt).

---

## Что понадобится

| Что | Примерная цена |
|-----|----------------|
| VPS 1 GB RAM, 1 CPU | 300–600 ₽/мес |
| Домен `.ru` | 200–400 ₽/год |
| SSL-сертификат | бесплатно (Let's Encrypt) |

Рекомендуемые тарифы: **Timeweb VPS**, **Beget VPS**, **Reg.ru VPS** — Ubuntu 22.04, минимум 1 GB RAM.

---

## Шаг 1. Арендовать VPS

1. Закажите VPS с **Ubuntu 22.04** (или 24.04).
2. Запишите **IP-адрес** сервера.
3. Запишите **логин и пароль** (обычно `root`).

---

## Шаг 2. Привязать домен

В панели регистратора домена (Reg.ru, Timeweb и т.д.) добавьте DNS-записи:

| Тип | Имя | Значение |
|-----|-----|----------|
| A | `@` | IP вашего VPS |
| A | `www` | IP вашего VPS |

Подождите 15–60 минут, пока DNS обновится.

---

## Шаг 3. Подготовить `.env` на компьютере

Откройте файл `.env` в папке проекта и заполните:

```env
BOT_TOKEN=токен_от_BotFather
BOT_USERNAME=nizkiyprofil_bot
OWNER_CHAT_ID=ваш_telegram_id
PORT=8080
SITE_URL=https://nizkiyprofil.ru
YANDEX_METRIKA_ID=
```

`SITE_URL` — ваш реальный домен с `https://`. Это важно для SEO (sitemap, canonical).

Подробнее про бота — в файле `ИНСТРУКЦИЯ-БОТ.md`.

---

## Шаг 4. Первичная настройка сервера (один раз)

### Вариант А — с Windows (проще)

1. Дважды щёлкните **`deploy-vps.bat`** — он загрузит файлы и запустит сайт.
2. Подключитесь по SSH и выполните настройку nginx (один раз):

```bash
ssh root@ВАШ_IP
cd /opt/nizkiy-profil
sudo bash deploy/setup-server.sh nizkiyprofil.ru
sudo bash deploy/deploy.sh
```

### Вариант Б — вручную через SSH

Подключитесь к серверу (PuTTY, Windows Terminal или `ssh root@ВАШ_IP`).

Скопируйте проект в `/opt/nizkiy-profil` через **WinSCP** или `scp`, затем:

```bash
cd /opt/nizkiy-profil
sudo bash deploy/setup-server.sh nizkiyprofil.ru
sudo bash deploy/deploy.sh
```

Скрипт `setup-server.sh` установит Docker, nginx, certbot и настроит файрвол.

---

## Шаг 5. Включить HTTPS (SSL)

Когда DNS уже указывает на сервер:

```bash
sudo certbot --nginx -d nizkiyprofil.ru -d www.nizkiyprofil.ru
```

Certbot сам выпустит сертификат и настроит редирект на HTTPS. Продление — автоматически.

Проверьте в браузере: `https://nizkiyprofil.ru`

---

## Шаг 6. Проверка работы

1. Сайт открывается по HTTPS.
2. Форма записи отправляет заявку — приходит в Telegram.
3. Бот отвечает на команду `/id` и на код заявки.
4. `https://nizkiyprofil.ru/api/health` — ответ `{"ok":true,...}`.
5. `https://nizkiyprofil.ru/sitemap.xml` — карта сайта для поисковиков.

---

## Шаг 7. Регистрация в поисковиках

После публикации:

1. **[Яндекс.Вебмастер](https://webmaster.yandex.ru)** — добавьте сайт, подтвердите владение, отправьте sitemap: `https://nizkiyprofil.ru/sitemap.xml`
2. **[Google Search Console](https://search.google.com/search-console)** — то же самое
3. Карточка в **Яндекс.Бизнесе** и **2ГИС** (адрес: Москва, ул. Привольная, 70к1)

---

## Обновление сайта после правок

Снова запустите **`deploy-vps.bat`** на компьютере — он перезальёт файлы и пересоберёт контейнер.

Или на сервере:

```bash
cd /opt/nizkiy-profil
# обновите файлы (WinSCP / scp)
sudo bash deploy/deploy.sh
```

---

## Полезные команды на сервере

```bash
cd /opt/nizkiy-profil

# Логи приложения
docker compose logs -f

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Статус
docker compose ps
curl http://127.0.0.1:8080/api/health
```

---

## Структура деплоя

```
/opt/nizkiy-profil/
├── docker-compose.yml    # запуск контейнера
├── Dockerfile
├── .env                  # секреты (не выкладывать в интернет)
├── deploy/
│   ├── setup-server.sh   # первичная настройка VPS
│   ├── deploy.sh         # сборка и запуск
│   └── nginx-site.conf   # шаблон nginx
└── server/bookings.json  # заявки (сохраняются на диске)
```

---

## Частые проблемы

**Сайт не открывается**
- Проверьте DNS: `ping nizkiyprofil.ru` должен показать IP сервера.
- `sudo systemctl status nginx`
- `docker compose logs` в `/opt/nizkiy-profil`

**Заявки не приходят в Telegram**
- Проверьте `BOT_TOKEN` и `OWNER_CHAT_ID` в `.env`
- После изменения `.env`: `sudo bash deploy/deploy.sh`

**Certbot не выдаёт сертификат**
- DNS ещё не обновился — подождите час.
- Порт 80 должен быть открыт: `sudo ufw status`

**502 Bad Gateway**
- Контейнер не запущен: `cd /opt/nizkiy-profil && sudo bash deploy/deploy.sh`

---

## Стоимость в месяц (ориентир)

| Статья | ₽/мес |
|--------|-------|
| VPS 1 GB | 300–500 |
| Домен `.ru` | ~25 (в пересчёте на год) |
| SSL | 0 |
| **Итого** | **~350–550 ₽** |

---

Если что-то не получается — напишите, на каком шаге застряли и какой хостинг выбрали.
