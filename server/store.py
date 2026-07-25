"""Простое потокобезопасное хранилище заявок в JSON-файле.

Без базы данных, чтобы запускалось где угодно без лишних установок.
"""
import json
import os
import random
import threading
import time
from datetime import datetime, timezone, timedelta

import config

# Алфавит без похожих символов (0/O, 1/I), чтобы код было удобно диктовать по телефону
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LEN = 5

_lock = threading.Lock()

# Статусы заявки и их «человеческие» подписи для клиента
STATUS_LABELS = {
    "new": "🆕 Принята, скоро свяжемся",
    "confirmed": "✅ Подтверждена",
    "in_progress": "🔧 В работе",
    "done": "🏁 Готово",
    "cancelled": "❌ Отменена",
}

SERVICES = [
    "Шиномонтаж",
    "Продажа шин",
    "Виброконтроль Hunter",
    "Правка дисков",
    "Аргонная сварка",
    "Порошковая покраска",
    "Хранение шин",
]

# Москва (UTC+3) — для времени в заявках
_MSK = timezone(timedelta(hours=3))
_VISIT_FMT = "%Y-%m-%d %H:%M"


def _now() -> datetime:
    return datetime.now(_MSK)


def _now_iso() -> str:
    return _now().strftime(_VISIT_FMT)


def parse_visit_at(value: str):
    """Разобрать строку визита 'YYYY-MM-DD HH:MM' → datetime (МСК) или None."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, _VISIT_FMT)
    except ValueError:
        return None
    return dt.replace(tzinfo=_MSK)


def format_visit_at(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_MSK)
    return dt.astimezone(_MSK).strftime(_VISIT_FMT)


def format_visit_human(value: str) -> str:
    dt = parse_visit_at(value)
    if not dt:
        return value or ""
    weekdays = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
    return f"{dt.strftime('%d.%m.%Y')} ({weekdays[dt.weekday()]}) в {dt.strftime('%H:%M')}"


def _read():
    if not os.path.exists(config.DATA_FILE):
        return {"seq": 0, "bookings": []}
    try:
        with open(config.DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"seq": 0, "bookings": []}


def _write(data):
    tmp = config.DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.DATA_FILE)


def _gen_code(existing_codes):
    for _ in range(50):
        code = "".join(random.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))
        if code not in existing_codes:
            return code
    return "".join(random.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN)) + str(int(time.time()))[-2:]


def add_booking(
    name: str,
    phone: str,
    service: str,
    comment: str = "",
    ip: str = "",
    source: str = "site",
    visit_at: str = "",
) -> dict:
    with _lock:
        data = _read()
        existing = {b["code"] for b in data["bookings"]}
        data["seq"] += 1
        visit = (visit_at or "").strip()
        status = "confirmed" if visit else "new"
        booking = {
            "id": data["seq"],
            "code": _gen_code(existing),
            "name": (name or "").strip() or "Не указано",
            "phone": (phone or "").strip(),
            "service": (service or "").strip() or "Шиномонтаж",
            "comment": (comment or "").strip(),
            "status": status,
            "source": (source or "site").strip() or "site",
            "visit_at": visit,
            "reminder_sent": False,
            "created_at": _now_iso(),
            "ts": time.time(),
            "ip": (ip or "").strip(),
        }
        data["bookings"].append(booking)
        _write(data)
        return booking


def rate_limit_check(phone: str, ip: str, min_interval: int = 300, daily_max: int = 5):
    """Проверка лимитов по телефону и IP.

    Возвращает (reason, retry_after_seconds):
    - (None, 0)        — можно создавать заявку;
    - ("interval", n)  — слишком рано, осталось n секунд;
    - ("daily", 0)     — превышен дневной лимит.
    """
    now = time.time()
    target_phone = _digits(phone)[-10:]
    with _lock:
        data = _read()
        bookings = list(data["bookings"])

    phone_items = [
        b for b in bookings
        if len(target_phone) == 10 and _digits(b.get("phone", ""))[-10:] == target_phone
    ]
    ip_items = [b for b in bookings if ip and b.get("ip") == ip]
    related = phone_items + ip_items
    if not related:
        return None, 0

    last = max((b.get("ts", 0) for b in related), default=0)
    if last and (now - last) < min_interval:
        return "interval", int(min_interval - (now - last))

    day_ago = now - 86400
    phone_today = sum(1 for b in phone_items if b.get("ts", 0) >= day_ago)
    ip_today = sum(1 for b in ip_items if b.get("ts", 0) >= day_ago)
    if max(phone_today, ip_today) >= daily_max:
        return "daily", 0

    return None, 0


def get_by_code(code: str):
    code = (code or "").strip().upper()
    if not code:
        return None
    with _lock:
        data = _read()
        for b in data["bookings"]:
            if b["code"] == code:
                return b
    return None


def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def find_by_phone(phone: str):
    """Поиск последней заявки по телефону (сравниваем последние 10 цифр)."""
    target = _digits(phone)[-10:]
    if len(target) < 10:
        return None
    with _lock:
        data = _read()
        matches = [b for b in data["bookings"] if _digits(b["phone"])[-10:] == target]
    return matches[-1] if matches else None


def update_status(code: str, status: str):
    if status not in STATUS_LABELS:
        return None
    code = (code or "").strip().upper()
    with _lock:
        data = _read()
        for b in data["bookings"]:
            if b["code"] == code:
                b["status"] = status
                _write(data)
                return b
    return None


def set_visit(code: str, visit_at: str):
    """Назначить или перенести визит. Сбрасывает флаг напоминания."""
    dt = parse_visit_at(visit_at)
    if not dt:
        return None
    code = (code or "").strip().upper()
    with _lock:
        data = _read()
        for b in data["bookings"]:
            if b["code"] == code:
                b["visit_at"] = format_visit_at(dt)
                b["reminder_sent"] = False
                if b.get("status") in ("new", "cancelled"):
                    b["status"] = "confirmed"
                _write(data)
                return b
    return None


def mark_reminder_sent(code: str):
    code = (code or "").strip().upper()
    with _lock:
        data = _read()
        for b in data["bookings"]:
            if b["code"] == code:
                b["reminder_sent"] = True
                _write(data)
                return b
    return None


def due_for_reminder(hours_before: int = 5):
    """Заявки, которым пора напомнить (за hours_before до визита, ещё не отправляли)."""
    now = _now()
    result = []
    with _lock:
        data = _read()
        bookings = list(data["bookings"])
    for b in bookings:
        if b.get("reminder_sent"):
            continue
        if b.get("status") in ("cancelled", "done"):
            continue
        visit = parse_visit_at(b.get("visit_at", ""))
        if not visit:
            continue
        remind_from = visit - timedelta(hours=hours_before)
        if remind_from <= now < visit:
            result.append(b)
    return result


def recent(limit: int = 10):
    with _lock:
        data = _read()
        return list(reversed(data["bookings"][-limit:]))


def active_for_visit(limit: int = 15):
    """Заявки, которым ещё можно назначить/перенести визит."""
    skip = {"cancelled", "done"}
    with _lock:
        data = _read()
        items = [b for b in reversed(data["bookings"]) if b.get("status") not in skip]
    return items[:limit]


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)
