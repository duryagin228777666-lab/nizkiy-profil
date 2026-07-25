"""Напоминания о визите.

Сейчас SMS не подключено: при срабатывании пишем в лог и уведомляем владельца в Telegram.
Когда будет SMS.ru — реализуйте отправку в send_client_reminder().
"""
import html
import threading
import time

import config
import store

_stop = threading.Event()


def reminder_text(b: dict) -> str:
    service = (b.get("service") or "услугу").strip()
    when = store.format_visit_human(b.get("visit_at", "")) or b.get("visit_at", "") or "указанное время"
    phone = config.SERVICE_PHONE
    return (
        f"Здравствуйте! Это шиномонтаж «{config.SERVICE_NAME}». "
        f"Напоминаем: вы записаны на {service} в {when}. "
        f"Если нужно перенести или изменить запись — звоните: {phone}"
    )


def _mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return "***" + digits[-4:]


def _e(value) -> str:
    return html.escape(str(value or ""))


def send_client_reminder(b: dict) -> bool:
    """Отправить напоминание клиенту.

    Заглушка до подключения SMS: возвращает True, чтобы пометить заявку
    как «напоминание обработано», и пишет в консоль факт отправки.
    """
    # TODO: SMS.ru — отправка по API (SMS_API_ID в .env)
    print(f"[reminder] SMS stub → {b.get('code')} ({_mask_phone(b.get('phone'))})")
    return True


def notify_owners_reminder(bot, b: dict):
    if not bot or not config.OWNER_CHAT_IDS:
        return
    when = store.format_visit_human(b.get("visit_at", ""))
    text = (
        f"⏰ <b>Напоминание клиенту (заглушка SMS)</b>\n\n"
        f"Код <code>{_e(b.get('code'))}</code> · {_e(b.get('name'))}\n"
        f"📞 {_e(b.get('phone'))}\n"
        f"🕒 Визит: {_e(when)}\n\n"
        f"Текст: {_e(reminder_text(b))}"
    )
    for chat_id in config.OWNER_CHAT_IDS:
        try:
            bot.send_message(chat_id, text)
        except Exception as exc:  # noqa: BLE001
            print(f"[reminder] Не удалось уведомить владельца {chat_id}: {exc}")


def process_due(bot=None):
    hours = getattr(config, "REMINDER_HOURS", 5)
    for b in store.due_for_reminder(hours):
        try:
            ok = send_client_reminder(b)
            if ok:
                store.mark_reminder_sent(b["code"])
                notify_owners_reminder(bot, b)
        except Exception as exc:  # noqa: BLE001
            print(f"[reminder] Ошибка по {b.get('code')}: {exc}")


def _loop(bot):
    interval = max(30, int(getattr(config, "REMINDER_CHECK_SEC", 60)))
    print(f"[reminder] Фоновая проверка каждые {interval} с (за {config.REMINDER_HOURS} ч до визита)")
    while not _stop.wait(interval):
        try:
            process_due(bot)
        except Exception as exc:  # noqa: BLE001
            print(f"[reminder] Сбой цикла: {exc}")


def start_background(bot=None):
    _stop.clear()
    thread = threading.Thread(target=_loop, args=(bot,), daemon=True, name="reminders")
    thread.start()
    return thread
