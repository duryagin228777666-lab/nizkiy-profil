"""Веб-сервер сервиса «Низкий профиль».

Делает три вещи в одном процессе:
1. Отдаёт статический сайт (index.html и т.д.).
2. Принимает заявки с формы по адресу POST /api/booking.
3. Запускает Telegram-бота (в фоновом потоке).
"""
import ipaddress
import os
import threading

from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory
from flask_cors import CORS

import bot as bot_module
import config
import seo
import store

# static_folder=None: корень проекта НЕ отдаётся целиком, иначе по HTTP были бы
# доступны server/bookings.json, .env, логи и внутренние документы.
app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

# Единственные файлы в корне проекта, которые можно отдавать наружу
PUBLIC_ROOT_FILES = ("styles.css", "script.js", "favicon.ico")
ASSETS_DIR = os.path.join(config.SITE_DIR, "assets")

# Защита от спама
ANTIBOT_MIN_MS = 1500       # форму нельзя отправить быстрее, чем за 1.5 сек
RL_MIN_INTERVAL = 300       # не чаще 1 заявки в 5 минут (с номера/IP)
RL_DAILY_MAX = 5            # не больше 5 заявок в сутки (с номера/IP)


def _is_local_proxy(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private


def _client_ip():
    """IP клиента для лимитов.

    Заголовкам доверяем только если запрос пришёл от локального nginx: клиент
    может прислать любой X-Forwarded-For и так обойти лимиты на заявки.
    """
    remote = request.remote_addr or ""
    if _is_local_proxy(remote):
        real = request.headers.get("X-Real-IP", "").strip()
        if real:
            return real
    return remote


def _base_url() -> str:
    if config.SITE_URL:
        return config.SITE_URL
    return request.host_url.rstrip("/")


def _serve_html(page_name: str):
    path = os.path.join(config.SITE_DIR, page_name)
    if not os.path.isfile(path):
        abort(404)
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    if page_name in seo.PAGES:
        seo.set_base_url(_base_url())
        html = seo.enhance(html, page_name)
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/")
def index():
    return _serve_html("index.html")


@app.route("/index.html")
def index_html():
    # В меню сайта ссылка «Главная» ведёт на index.html — уводим на канонический /
    return redirect("/", code=301)


@app.route("/robots.txt")
def robots():
    seo.set_base_url(_base_url())
    return Response(seo.robots_txt(), mimetype="text/plain; charset=utf-8")


@app.route("/sitemap.xml")
def sitemap():
    seo.set_base_url(_base_url())
    return Response(seo.sitemap_xml(), mimetype="application/xml; charset=utf-8")


@app.route("/assets/<path:filename>")
def assets(filename):
    # send_from_directory сам блокирует выход за пределы папки (../)
    return send_from_directory(ASSETS_DIR, filename)


def _register_static_routes():
    for page_name in seo.HTML_PAGES:
        if page_name == "index.html":
            continue
        app.add_url_rule(
            f"/{page_name}",
            endpoint=f"page_{page_name.replace('.', '_')}",
            view_func=lambda pn=page_name: _serve_html(pn),
        )
    for file_name in PUBLIC_ROOT_FILES:
        app.add_url_rule(
            f"/{file_name}",
            endpoint=f"file_{file_name.replace('.', '_')}",
            view_func=lambda fn=file_name: send_from_directory(config.SITE_DIR, fn),
        )


_register_static_routes()


@app.route("/api/booking", methods=["POST"])
def api_booking():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    comment = (data.get("comment") or "").strip()
    honeypot = (data.get("website") or "").strip()
    try:
        elapsed = float(data.get("elapsed") or 0)
    except (TypeError, ValueError):
        elapsed = 0

    # Анти-бот: скрытое поле заполнено или форма отправлена слишком быстро
    if honeypot or (0 < elapsed < ANTIBOT_MIN_MS):
        return jsonify(ok=False, error="Заявка отклонена. Обновите страницу и попробуйте снова."), 400

    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return jsonify(ok=False, error="Укажите корректный номер телефона"), 400

    ip = _client_ip()
    reason, retry = store.rate_limit_check(phone, ip, RL_MIN_INTERVAL, RL_DAILY_MAX)
    if reason == "interval":
        minutes = max(1, (retry + 59) // 60)
        return jsonify(
            ok=False,
            error=f"Вы недавно уже оставили заявку. Попробуйте через {minutes} мин или позвоните нам.",
        ), 429
    if reason == "daily":
        return jsonify(
            ok=False,
            error="Слишком много заявок за сегодня. Позвоните нам: +7 965 435-72-72.",
        ), 429

    booking = store.add_booking(name, phone, service, comment, ip=ip)

    try:
        bot_module.notify_owners(booking)
    except Exception as exc:  # noqa: BLE001
        print(f"[app] Ошибка отправки в Telegram: {exc}")

    return jsonify(ok=True, code=booking["code"], bot=config.bot_link(booking["code"]))


@app.route("/api/health")
def health():
    # Только признак «сервер жив»: состав настроек наружу не показываем
    return jsonify(ok=True)


def _start_bot():
    if not config.BOT_TOKEN:
        print("=" * 60)
        print("ВНИМАНИЕ: BOT_TOKEN не задан в .env — бот выключен.")
        print("Сайт и приём заявок работают, но сообщения в Telegram не уходят.")
        print("=" * 60)
        return
    thread = threading.Thread(target=bot_module.run_polling, daemon=True)
    thread.start()
    print("[app] Telegram-бот запущен.")


# Запуск бота при старте через gunicorn / облачный хостинг (один воркер).
if os.environ.get("START_BOT", "1") == "1":
    _start_bot()


if __name__ == "__main__":
    print(f"[app] Сайт и API: http://localhost:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, threaded=True)
