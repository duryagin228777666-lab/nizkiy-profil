"""Конфигурация сервера и бота. Все секреты берутся из .env / переменных окружения."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

# Папка со статическим сайтом (корень проекта, где лежит index.html)
SITE_DIR = str(Path(__file__).resolve().parent.parent)

# Файл, в котором хранятся заявки
DATA_FILE = str(Path(__file__).resolve().parent / "bookings.json")

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Username бота без @ (например: nizkiyprofil_bot) — нужен для ссылки отслеживания
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")


def _parse_owner_ids(raw: str):
    # Допускаем разделители: запятая, точка с запятой, пробел
    normalized = raw.replace(";", ",").replace(" ", ",")
    ids = []
    for part in normalized.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value not in ids:
            ids.append(value)
    return ids


# Один или несколько chat_id владельцев (через запятую), куда приходят заявки
OWNER_CHAT_IDS = _parse_owner_ids(os.getenv("OWNER_CHAT_ID", ""))

# Порт веб-сервера
PORT = int(os.getenv("PORT", "5000"))

# Телефон сервиса для кнопки «Позвонить» в боте (в международном формате)
SERVICE_PHONE = os.getenv("SERVICE_PHONE", "+79654357272").strip()

# Название сервиса (показывается на карточке контакта)
SERVICE_NAME = os.getenv("SERVICE_NAME", "Низкий профиль").strip()

# Публичный адрес сайта (для canonical, Open Graph и sitemap)
SITE_URL = os.getenv("SITE_URL", "").strip().rstrip("/")

# Яндекс.Метрика (номер счётчика). Подключается только после согласия на cookie.
YANDEX_METRIKA_ID = os.getenv("YANDEX_METRIKA_ID", "").strip()


def bot_link(code: str) -> str:
    """Ссылка для клиента: открыть бота и сразу проверить статус по коду."""
    if not BOT_USERNAME:
        return ""
    return f"https://t.me/{BOT_USERNAME}?start={code}"
