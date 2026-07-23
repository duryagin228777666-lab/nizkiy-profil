"""Telegram-бот сервиса «Низкий профиль».

Делает две вещи:
1. Присылает владельцу новые заявки с сайта.
2. Позволяет клиенту узнать статус своей заявки по коду (или телефону).

Управление статусами для владельца сделано опционально — кнопками под заявкой.
Если они не нужны, их можно просто игнорировать.
"""
import html

import telebot
from telebot import types

import config
import store

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML") if config.BOT_TOKEN else None


def _e(text: str) -> str:
    return html.escape(str(text or ""))


def _is_owner(chat_id: int) -> bool:
    return chat_id in config.OWNER_CHAT_IDS


def _call_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопка «Позвонить»: по нажатию бот пришлёт контакт для быстрого набора."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📞 Позвонить", callback_data="call"))
    return markup


def _send_call_contact(chat_id: int):
    """Карточка контакта — у неё на телефоне есть кнопка вызова (сразу идёт набор)."""
    bot.send_contact(chat_id, config.SERVICE_PHONE, first_name=config.SERVICE_NAME)


def _normalize_phone(phone: str) -> str:
    """Приводим телефон клиента к формату +7XXXXXXXXXX для звонка."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return phone or ""


def _owner_call_keyboard(code: str) -> types.InlineKeyboardMarkup:
    """Кнопка под заявкой: позвонить клиенту."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📞 Позвонить клиенту", callback_data=f"callc:{code}"))
    return markup


def _owner_text(b: dict) -> str:
    lines = [
        "🛞 <b>Новая заявка с сайта «Низкий профиль»</b>",
        "",
        f"№ <b>{b['id']}</b> · код <code>{_e(b['code'])}</code>",
        f"👤 Имя: {_e(b['name'])}",
        f"📞 Телефон: <code>{_e(b['phone'])}</code>",
        f"🔧 Услуга: {_e(b['service'])}",
    ]
    if b.get("comment"):
        lines.append(f"💬 Комментарий: {_e(b['comment'])}")
    lines.append(f"🕒 {_e(b['created_at'])} (МСК)")
    return "\n".join(lines)


def _client_text(b: dict) -> str:
    lines = [
        "🛞 <b>Ваша заявка «Низкий профиль»</b>",
        "",
        f"Код: <code>{_e(b['code'])}</code>",
        f"🔧 Услуга: {_e(b['service'])}",
    ]
    if b.get("comment"):
        lines.append(f"💬 Комментарий: {_e(b['comment'])}")
    lines.append(f"🕒 Создана: {_e(b['created_at'])} (МСК)")
    lines.append("")
    lines.append("Спасибо! Мы свяжемся с вами в ближайшее время.")
    return "\n".join(lines)


def notify_owners(b: dict):
    """Отправить новую заявку всем владельцам."""
    if not bot:
        print("[bot] BOT_TOKEN не задан — заявка не отправлена в Telegram:", b.get("code"))
        return
    if not config.OWNER_CHAT_IDS:
        print("[bot] OWNER_CHAT_ID не задан — некому отправлять заявку:", b.get("code"))
        return
    text = _owner_text(b)
    markup = _owner_call_keyboard(b["code"])
    for chat_id in config.OWNER_CHAT_IDS:
        try:
            bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить владельцу {chat_id}: {exc}")


def _register_handlers():
    @bot.message_handler(commands=["start"])
    def on_start(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            _send_status(message.chat.id, parts[1].strip())
            return
        bot.send_message(
            message.chat.id,
            "Здравствуйте! Это бот сервиса «Низкий профиль» 🛞\n\n"
            "Чтобы узнать статус своей заявки, отправьте <b>код</b>, "
            "который вы получили при записи на сайте (например <code>K7QF2</code>),\n"
            "или номер телефона, который указывали в заявке.\n\n"
            "А чтобы позвонить нам — нажмите кнопку ниже.",
            reply_markup=_call_keyboard(),
        )

    @bot.message_handler(commands=["id"])
    def on_id(message):
        bot.reply_to(
            message,
            f"Ваш chat_id: <code>{message.chat.id}</code>\n\n"
            "Впишите его в файл <code>.env</code> в строку <b>OWNER_CHAT_ID</b>, "
            "чтобы получать сюда заявки с сайта.",
        )

    @bot.message_handler(commands=["list"])
    def on_list(message):
        if not _is_owner(message.chat.id):
            bot.reply_to(message, "Эта команда доступна только владельцу сервиса.")
            return
        items = store.recent(10)
        if not items:
            bot.reply_to(message, "Заявок пока нет.")
            return
        chunks = []
        for b in items:
            chunks.append(
                f"№{b['id']} <code>{_e(b['code'])}</code> · {_e(b['phone'])}\n"
                f"{_e(b['service'])} — {_e(store.status_label(b['status']))} · {_e(b['created_at'])}"
            )
        bot.send_message(message.chat.id, "📋 <b>Последние заявки:</b>\n\n" + "\n\n".join(chunks))

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def on_text(message):
        _send_status(message.chat.id, message.text.strip())

    @bot.callback_query_handler(func=lambda c: c.data == "call")
    def on_call(call):
        bot.answer_callback_query(call.id, "Отправляю контакт для звонка")
        try:
            _send_call_contact(call.message.chat.id)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить контакт: {exc}")
            bot.send_message(call.message.chat.id, f"Наш телефон: {config.SERVICE_PHONE}")

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("callc:"))
    def on_call_client(call):
        if not _is_owner(call.message.chat.id):
            bot.answer_callback_query(call.id, "Только для владельца")
            return
        code = call.data.split(":", 1)[1]
        b = store.get_by_code(code)
        if not b:
            bot.answer_callback_query(call.id, "Заявка не найдена")
            return
        bot.answer_callback_query(call.id, "Отправляю контакт клиента")
        phone = _normalize_phone(b["phone"])
        try:
            bot.send_contact(call.message.chat.id, phone, first_name=b["name"])
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить контакт клиента: {exc}")
            bot.send_message(call.message.chat.id, f"Телефон клиента: {phone}")


def _send_status(chat_id: int, query: str):
    query = (query or "").strip()
    if not query:
        bot.send_message(chat_id, "Отправьте код заявки или номер телефона.")
        return
    b = store.get_by_code(query)
    if not b:
        b = store.find_by_phone(query)
    if not b:
        bot.send_message(
            chat_id,
            "Заявка не найдена 🤔\n"
            "Проверьте код (5 символов с сайта) или отправьте номер телефона из заявки.\n\n"
            "Если что-то не так — позвоните нам.",
            reply_markup=_call_keyboard(),
        )
        return
    bot.send_message(chat_id, _client_text(b), reply_markup=_call_keyboard())


def run_polling():
    if not bot:
        return
    _register_handlers()
    try:
        bot.infinity_polling(skip_pending=True, timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"[bot] Ошибка polling: {exc}")
