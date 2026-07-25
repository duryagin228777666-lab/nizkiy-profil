"""Telegram-бот сервиса «Низкий профиль».

1. Присылает владельцу новые заявки с сайта.
2. Даёт владельцу меню на кнопках: ручная запись, визит, статусы, отмена.
3. Клиенту — статус заявки по коду или телефону.
"""
from __future__ import annotations

import html
import re
import time
import traceback
from datetime import datetime, timedelta, timezone

import telebot
from telebot import apihelper, types

import config
import reminders
import store

if config.TELEGRAM_PROXY:
    apihelper.proxy = {"https": config.TELEGRAM_PROXY, "http": config.TELEGRAM_PROXY}
    print(f"[bot] Прокси Telegram: {config.TELEGRAM_PROXY}")

# Дольше ждём ответ Telegram — в РФ бывают таймауты
apihelper.CONNECT_TIMEOUT = 25
apihelper.READ_TIMEOUT = 60

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML") if config.BOT_TOKEN else None

_MSK = timezone(timedelta(hours=3))

# Состояния мастеров владельца: chat_id -> dict
_owner_state: dict[int, dict] = {}

# Подписи кнопок главного меню (ReplyKeyboard)
BTN_ADD = "➕ Новая запись"
BTN_LIST = "📋 Заявки"
BTN_VISIT = "📅 Назначить визит"
BTN_CANCEL = "❌ Отменить"
BTN_MENU = "🏠 Меню"

OWNER_MENU_BUTTONS = {BTN_ADD, BTN_LIST, BTN_VISIT, BTN_CANCEL, BTN_MENU}

# Кнопки клиента
BTN_CLIENT_PHONE = "📱 Моя заявка по номеру"
BTN_CLIENT_CALL = "📞 Позвонить"

# Ограничение перебора кодов заявок: попыток на чат за окно
_LOOKUP_MAX = 15
_LOOKUP_WINDOW = 600
_lookup_log: dict[int, list[float]] = {}

# Часы приёма для кнопок времени
_WORK_HOURS = list(range(9, 22))  # 9:00 … 21:00


def _e(text: str) -> str:
    return html.escape(str(text or ""))


def _is_owner(chat_id: int) -> bool:
    return chat_id in config.OWNER_CHAT_IDS


def _clear_state(chat_id: int):
    _owner_state.pop(chat_id, None)


def _set_state(chat_id: int, **kwargs):
    state = _owner_state.setdefault(chat_id, {})
    state.update(kwargs)
    return state


def _get_state(chat_id: int) -> dict:
    return _owner_state.get(chat_id) or {}


def _owner_menu_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(BTN_ADD, BTN_LIST)
    kb.row(BTN_VISIT, BTN_CANCEL)
    kb.row(BTN_MENU)
    return kb


def _call_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📞 Позвонить", callback_data="call"))
    return markup


def _client_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Меню клиента. Кнопка контакта — единственный способ проверить заявку по
    номеру: Telegram сам подтверждает, что номер принадлежит отправителю."""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton(BTN_CLIENT_PHONE, request_contact=True))
    kb.row(types.KeyboardButton(BTN_CLIENT_CALL))
    return kb


def _lookup_allowed(chat_id: int) -> bool:
    """Не даём перебирать 5-символьные коды чужих заявок."""
    now = time.time()
    hits = [t for t in _lookup_log.get(chat_id, []) if now - t < _LOOKUP_WINDOW]
    hits.append(now)
    _lookup_log[chat_id] = hits
    return len(hits) <= _LOOKUP_MAX


def _send_call_contact(chat_id: int):
    bot.send_contact(chat_id, config.SERVICE_PHONE, first_name=config.SERVICE_NAME)


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return phone or ""


def _phone_ok(phone: str) -> bool:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return len(digits) >= 10


def _owner_booking_keyboard(code: str) -> types.InlineKeyboardMarkup:
    """Кнопки под карточкой заявки."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📞 Позвонить", callback_data=f"callc:{code}"),
        types.InlineKeyboardButton("📅 Визит", callback_data=f"vis:{code}"),
    )
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"st:confirmed:{code}"),
        types.InlineKeyboardButton("🔧 В работу", callback_data=f"st:in_progress:{code}"),
    )
    markup.add(
        types.InlineKeyboardButton("🏁 Готово", callback_data=f"st:done:{code}"),
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"st:cancelled:{code}"),
    )
    return markup


def _owner_text(b: dict) -> str:
    source = "сайт" if b.get("source") == "site" else "вручную"
    lines = [
        "🛞 <b>Заявка «Низкий профиль»</b>",
        "",
        f"№ <b>{b['id']}</b> · код <code>{_e(b['code'])}</code> · {_e(source)}",
        f"👤 Имя: {_e(b['name'])}",
        f"📞 Телефон: <code>{_e(b['phone'])}</code>",
        f"🔧 Услуга: {_e(b['service'])}",
        f"📌 Статус: {_e(store.status_label(b.get('status', 'new')))}",
    ]
    if b.get("visit_at"):
        lines.append(f"🗓 Визит: <b>{_e(store.format_visit_human(b['visit_at']))}</b>")
    if b.get("comment"):
        lines.append(f"💬 Комментарий: {_e(b['comment'])}")
    lines.append(f"🕒 Создана: {_e(b['created_at'])} (МСК)")
    return "\n".join(lines)


def _client_text(b: dict) -> str:
    lines = [
        "🛞 <b>Ваша заявка «Низкий профиль»</b>",
        "",
        f"Код: <code>{_e(b['code'])}</code>",
        f"🔧 Услуга: {_e(b['service'])}",
        f"📌 Статус: {_e(store.status_label(b.get('status', 'new')))}",
    ]
    if b.get("visit_at"):
        lines.append(f"🗓 Визит: <b>{_e(store.format_visit_human(b['visit_at']))}</b>")
    if b.get("comment"):
        lines.append(f"💬 Комментарий: {_e(b['comment'])}")
    lines.append(f"🕒 Создана: {_e(b['created_at'])} (МСК)")
    lines.append("")
    if b.get("visit_at") and b.get("status") not in ("cancelled", "done"):
        lines.append("Ждём вас в сервисе!")
    else:
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
    if b.get("source") == "site":
        text = "🆕 <b>Новая заявка с сайта</b>\n\n" + text
    markup = _owner_booking_keyboard(b["code"])
    for chat_id in config.OWNER_CHAT_IDS:
        try:
            bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить владельцу {chat_id}: {exc}")


def _services_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, name in enumerate(store.SERVICES):
        markup.add(types.InlineKeyboardButton(name, callback_data=f"svc:{i}"))
    markup.add(types.InlineKeyboardButton("✖️ Отмена", callback_data="flow:abort"))
    return markup


def _day_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Сегодня", callback_data="day:0"))
    markup.add(types.InlineKeyboardButton("Завтра", callback_data="day:1"))
    markup.add(types.InlineKeyboardButton("Послезавтра", callback_data="day:2"))
    markup.add(types.InlineKeyboardButton("✍️ Ввести дату", callback_data="day:custom"))
    markup.add(types.InlineKeyboardButton("✖️ Отмена", callback_data="flow:abort"))
    return markup


def _time_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=4)
    buttons = [
        types.InlineKeyboardButton(f"{h:02d}:00", callback_data=f"tm:{h:02d}:00")
        for h in _WORK_HOURS
    ]
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i : i + 4])
    markup.add(types.InlineKeyboardButton("✍️ Ввести время", callback_data="tm:custom"))
    markup.add(types.InlineKeyboardButton("✖️ Отмена", callback_data="flow:abort"))
    return markup


def _visit_later_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📅 Назначить визит сейчас", callback_data="add:visit_now"))
    markup.add(types.InlineKeyboardButton("⏭ Позже", callback_data="add:visit_later"))
    markup.add(types.InlineKeyboardButton("✖️ Отмена", callback_data="flow:abort"))
    return markup


def _pick_bookings_keyboard(items: list, prefix: str) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in items:
        visit = ""
        if b.get("visit_at"):
            visit = " · " + store.format_visit_human(b["visit_at"])
        label = f"{b['code']} · {b['name']} · {b['phone']}{visit}"
        if len(label) > 60:
            label = label[:57] + "…"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"{prefix}:{b['code']}"))
    markup.add(types.InlineKeyboardButton("✖️ Отмена", callback_data="flow:abort"))
    return markup


def _send_owner_menu(chat_id: int, text: str | None = None):
    bot.send_message(
        chat_id,
        text
        or (
            "🛠 <b>Меню владельца</b>\n\n"
            "➕ Новая запись — клиент по телефону / с улицы\n"
            "📋 Заявки — последние записи\n"
            "📅 Назначить визит — дата и время после созвона\n"
            "❌ Отменить — отмена записи\n\n"
            f"Напоминание клиенту уйдёт за {config.REMINDER_HOURS} ч до визита "
            "(SMS подключим отдельно)."
        ),
        reply_markup=_owner_menu_keyboard(),
    )


def _start_add(chat_id: int):
    _set_state(chat_id, action="add_name", data={})
    bot.send_message(chat_id, "➕ <b>Новая запись</b>\n\nВведите имя клиента:", reply_markup=_owner_menu_keyboard())


def _start_visit_pick(chat_id: int):
    items = store.active_for_visit(15)
    if not items:
        bot.send_message(chat_id, "Нет активных заявок для назначения визита.")
        return
    _set_state(chat_id, action="visit_pick", data={})
    bot.send_message(
        chat_id,
        "📅 Выберите заявку:",
        reply_markup=_pick_bookings_keyboard(items, "vpick"),
    )


def _start_cancel_pick(chat_id: int):
    items = store.active_for_visit(15)
    if not items:
        bot.send_message(chat_id, "Нет активных заявок для отмены.")
        return
    _set_state(chat_id, action="cancel_pick", data={})
    bot.send_message(
        chat_id,
        "❌ Выберите заявку для отмены:",
        reply_markup=_pick_bookings_keyboard(items, "cpick"),
    )


def _send_list(chat_id: int):
    items = store.recent(10)
    if not items:
        bot.send_message(chat_id, "Заявок пока нет.")
        return
    chunks = []
    for b in items:
        visit = store.format_visit_human(b["visit_at"]) if b.get("visit_at") else "визит не назначен"
        chunks.append(
            f"№{b['id']} <code>{_e(b['code'])}</code> · {_e(b['phone'])}\n"
            f"{_e(b['name'])} · {_e(b['service'])}\n"
            f"{_e(store.status_label(b['status']))} · {_e(visit)}"
        )
    bot.send_message(chat_id, "📋 <b>Последние заявки:</b>\n\n" + "\n\n".join(chunks))


def _ask_day(chat_id: int):
    _set_state(chat_id, action="visit_day")
    bot.send_message(chat_id, "Выберите день визита:", reply_markup=_day_keyboard())


def _ask_time(chat_id: int):
    _set_state(chat_id, action="visit_time")
    bot.send_message(chat_id, "Выберите время:", reply_markup=_time_keyboard())


def _finish_visit(chat_id: int, time_str: str):
    state = _get_state(chat_id)
    data = state.get("data") or {}
    day_offset = data.get("day_offset")
    date_str = data.get("date")

    if date_str:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    elif day_offset is not None:
        day = (datetime.now(_MSK) + timedelta(days=int(day_offset))).date()
    else:
        bot.send_message(chat_id, "Сначала выберите день.")
        _ask_day(chat_id)
        return

    visit_at = f"{day.isoformat()} {time_str}"
    if not store.parse_visit_at(visit_at):
        bot.send_message(chat_id, "Некорректные дата или время. Попробуйте снова.")
        _ask_day(chat_id)
        return

    # Режим: новая запись или назначение на существующую
    if state.get("mode") == "add":
        name = data.get("name", "")
        phone = data.get("phone", "")
        service = data.get("service", "Шиномонтаж")
        booking = store.add_booking(
            name, phone, service, comment="", source="manual", visit_at=visit_at
        )
        _clear_state(chat_id)
        bot.send_message(
            chat_id,
            f"✅ Запись создана\n\n{_owner_text(booking)}",
            reply_markup=_owner_booking_keyboard(booking["code"]),
        )
        # Другим владельцам тоже (кроме текущего — уже видит)
        for oid in config.OWNER_CHAT_IDS:
            if oid != chat_id:
                try:
                    bot.send_message(
                        oid,
                        "🆕 <b>Запись вручную</b>\n\n" + _owner_text(booking),
                        reply_markup=_owner_booking_keyboard(booking["code"]),
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"[bot] notify other owner {oid}: {exc}")
        return

    code = data.get("code")
    booking = store.set_visit(code, visit_at)
    _clear_state(chat_id)
    if not booking:
        bot.send_message(chat_id, "Заявка не найдена.")
        return
    bot.send_message(
        chat_id,
        f"✅ Визит назначен\n\n{_owner_text(booking)}\n\n"
        f"Напоминание (SMS) — за {config.REMINDER_HOURS} ч до визита.",
        reply_markup=_owner_booking_keyboard(booking["code"]),
    )


def _save_add_without_visit(chat_id: int):
    state = _get_state(chat_id)
    data = state.get("data") or {}
    booking = store.add_booking(
        data.get("name", ""),
        data.get("phone", ""),
        data.get("service", "Шиномонтаж"),
        comment="",
        source="manual",
    )
    _clear_state(chat_id)
    bot.send_message(
        chat_id,
        f"✅ Запись создана (визит пока не назначен)\n\n{_owner_text(booking)}\n\n"
        "После созвона нажмите «📅 Назначить визит» или кнопку под заявкой.",
        reply_markup=_owner_booking_keyboard(booking["code"]),
    )
    for oid in config.OWNER_CHAT_IDS:
        if oid != chat_id:
            try:
                bot.send_message(
                    oid,
                    "🆕 <b>Запись вручную</b>\n\n" + _owner_text(booking),
                    reply_markup=_owner_booking_keyboard(booking["code"]),
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[bot] notify other owner {oid}: {exc}")


def _parse_custom_date(text: str):
    raw = (text or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_custom_time(text: str):
    raw = (text or "").strip().replace(".", ":")
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", raw)
    if not m:
        m = re.fullmatch(r"(\d{1,2})", raw)
        if m:
            h = int(m.group(1))
            if 0 <= h <= 23:
                return f"{h:02d}:00"
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def _normalize_menu_text(text: str) -> str:
    """Убираем вариации emoji/пробелов — Telegram иногда шлёт чуть другой символ."""
    t = (text or "").strip().lower().replace("ё", "е")
    for ch in ("➕", "📋", "📅", "❌", "🏠", "✖️", "✅", "🔧", "🏁", "📞", "⏭", "✍️"):
        t = t.replace(ch, " ")
    return " ".join(t.split())


_MENU_BY_NORM = {
    _normalize_menu_text(BTN_ADD): BTN_ADD,
    _normalize_menu_text(BTN_LIST): BTN_LIST,
    _normalize_menu_text(BTN_VISIT): BTN_VISIT,
    _normalize_menu_text(BTN_CANCEL): BTN_CANCEL,
    _normalize_menu_text(BTN_MENU): BTN_MENU,
    "новая запись": BTN_ADD,
    "заявки": BTN_LIST,
    "назначить визит": BTN_VISIT,
    "отменить": BTN_CANCEL,
    "меню": BTN_MENU,
}


def _resolve_menu_button(text: str) -> str | None:
    raw = (text or "").strip()
    if raw in OWNER_MENU_BUTTONS:
        return raw
    return _MENU_BY_NORM.get(_normalize_menu_text(raw))


def _handle_owner_menu_button(chat_id: int, text: str) -> bool:
    btn = _resolve_menu_button(text)
    if not btn:
        return False
    if btn == BTN_MENU:
        _clear_state(chat_id)
        _send_owner_menu(chat_id)
        return True
    if btn == BTN_ADD:
        _start_add(chat_id)
        return True
    if btn == BTN_LIST:
        _clear_state(chat_id)
        _send_list(chat_id)
        return True
    if btn == BTN_VISIT:
        _start_visit_pick(chat_id)
        return True
    if btn == BTN_CANCEL:
        _start_cancel_pick(chat_id)
        return True
    return False


def _handle_owner_text(message) -> bool:
    """Обработка текста владельца в мастере. True = обработано."""
    chat_id = message.chat.id
    text = (message.text or "").strip()
    if _resolve_menu_button(text):
        return _handle_owner_menu_button(chat_id, text)

    state = _get_state(chat_id)
    action = state.get("action")
    if not action:
        return False

    data = state.setdefault("data", {})

    if action == "add_name":
        data["name"] = text[:80] or "Не указано"
        _set_state(chat_id, action="add_phone", data=data)
        bot.send_message(chat_id, "Введите телефон клиента:")
        return True

    if action == "add_phone":
        if not _phone_ok(text):
            bot.send_message(chat_id, "Нужен номер минимум из 10 цифр. Пример: +7 965 435-72-72")
            return True
        data["phone"] = text
        _set_state(chat_id, action="add_service", data=data)
        bot.send_message(chat_id, "Выберите услугу:", reply_markup=_services_keyboard())
        return True

    if action == "visit_date_custom":
        day = _parse_custom_date(text)
        if not day:
            bot.send_message(chat_id, "Формат даты: ДД.ММ.ГГГГ (например 25.07.2026)")
            return True
        data["date"] = day.isoformat()
        data.pop("day_offset", None)
        _set_state(chat_id, data=data)
        _ask_time(chat_id)
        return True

    if action == "visit_time_custom":
        t = _parse_custom_time(text)
        if not t:
            bot.send_message(chat_id, "Формат времени: ЧЧ:ММ (например 15:00)")
            return True
        _finish_visit(chat_id, t)
        return True

    return False


def _register_handlers():
    @bot.message_handler(commands=["start", "menu"])
    def on_start(message):
        parts = message.text.split(maxsplit=1)
        # Клиентский deep-link: /start CODE
        if len(parts) > 1 and parts[1].strip() and not _is_owner(message.chat.id):
            _send_status(message.chat.id, parts[1].strip())
            return
        if _is_owner(message.chat.id):
            _clear_state(message.chat.id)
            # Если в /start передали код — покажем заявку владельцу
            if len(parts) > 1 and parts[1].strip():
                b = store.get_by_code(parts[1].strip())
                if b:
                    bot.send_message(
                        message.chat.id,
                        _owner_text(b),
                        reply_markup=_owner_booking_keyboard(b["code"]),
                    )
            _send_owner_menu(message.chat.id)
            return
        bot.send_message(
            message.chat.id,
            "Здравствуйте! Это бот сервиса «Низкий профиль» 🛞\n\n"
            "Чтобы узнать статус своей заявки, отправьте <b>код</b>, "
            "который вы получили при записи на сайте (например <code>K7QF2</code>).\n\n"
            f"Потеряли код — нажмите «{BTN_CLIENT_PHONE}»: Telegram подтвердит ваш номер, "
            "и мы покажем вашу заявку.",
            reply_markup=_client_menu_keyboard(),
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
        _send_list(message.chat.id)

    @bot.message_handler(commands=["cancel_flow"])
    def on_cancel_flow(message):
        if _is_owner(message.chat.id):
            _clear_state(message.chat.id)
            bot.send_message(message.chat.id, "Действие отменено.", reply_markup=_owner_menu_keyboard())

    @bot.message_handler(content_types=["contact"])
    def on_contact(message):
        contact = message.contact
        chat_id = message.chat.id
        if not contact:
            return
        if _is_owner(chat_id):
            b = store.find_by_phone(contact.phone_number)
            if b:
                bot.send_message(
                    chat_id,
                    _owner_text(b),
                    reply_markup=_owner_booking_keyboard(b["code"]),
                )
            else:
                bot.send_message(chat_id, "Заявок с этим номером нет.", reply_markup=_owner_menu_keyboard())
            return
        # Клиенту показываем заявку, только если Telegram подтвердил, что номер его:
        # пересланный или вручную созданный контакт содержит чужой user_id (или ни одного)
        if not contact.user_id or contact.user_id != message.from_user.id:
            bot.send_message(
                chat_id,
                "Это не ваш номер. Заявку показываем только владельцу номера — "
                f"нажмите кнопку «{BTN_CLIENT_PHONE}» внизу.",
                reply_markup=_client_menu_keyboard(),
            )
            return
        b = store.find_by_phone(contact.phone_number)
        if not b:
            bot.send_message(
                chat_id,
                "Заявок с вашим номером не нашлось 🤔\n"
                "Возможно, при записи был указан другой телефон — тогда отправьте код с сайта "
                "или позвоните нам.",
                reply_markup=_client_menu_keyboard(),
            )
            return
        bot.send_message(chat_id, _client_text(b), reply_markup=_call_keyboard())

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def on_text(message):
        try:
            print(f"[bot] text from {message.chat.id}: {len(message.text or '')} символов")
            if _is_owner(message.chat.id):
                if _handle_owner_text(message):
                    return
                text = (message.text or "").strip()
                if _resolve_menu_button(text):
                    _handle_owner_menu_button(message.chat.id, text)
                    return
                b = store.get_by_code(text) or store.find_by_phone(text)
                if b:
                    bot.send_message(
                        message.chat.id,
                        _owner_text(b),
                        reply_markup=_owner_booking_keyboard(b["code"]),
                    )
                    return
                bot.send_message(
                    message.chat.id,
                    "Не понял. Выберите действие в меню ниже или отправьте код / телефон заявки.",
                    reply_markup=_owner_menu_keyboard(),
                )
                return
            client_text = (message.text or "").strip()
            if client_text == BTN_CLIENT_CALL:
                _send_call_contact(message.chat.id)
                return
            _send_status(message.chat.id, client_text)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Ошибка on_text: {exc}")
            traceback.print_exc()
            try:
                bot.send_message(message.chat.id, "Произошла ошибка. Нажмите /start")
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda c: True)
    def on_callback(call):
        data = call.data or ""
        chat_id = call.message.chat.id if call.message else 0
        print(f"[bot] callback from {chat_id}: {data!r}")
        try:
            _handle_callback(call)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Ошибка callback {data!r}: {exc}")
            traceback.print_exc()
            try:
                bot.answer_callback_query(call.id, "Ошибка, попробуйте ещё раз")
            except Exception:
                pass
            try:
                bot.send_message(chat_id, "Не удалось выполнить действие. Нажмите /start")
            except Exception:
                pass


def _handle_callback(call):
    data = call.data or ""
    chat_id = call.message.chat.id

    # Клиент: позвонить в сервис
    if data == "call":
        bot.answer_callback_query(call.id, "Отправляю контакт для звонка")
        try:
            _send_call_contact(chat_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить контакт: {exc}")
            bot.send_message(chat_id, f"Наш телефон: {config.SERVICE_PHONE}")
        return

    if not _is_owner(chat_id):
        bot.answer_callback_query(call.id, "Только для владельца")
        return

    # ---- владелец ----
    if data == "flow:abort":
        _clear_state(chat_id)
        bot.answer_callback_query(call.id, "Отменено")
        bot.send_message(chat_id, "Действие отменено.", reply_markup=_owner_menu_keyboard())
        return

    if data.startswith("callc:"):
        code = data.split(":", 1)[1]
        b = store.get_by_code(code)
        if not b:
            bot.answer_callback_query(call.id, "Заявка не найдена")
            return
        bot.answer_callback_query(call.id, "Отправляю контакт клиента")
        phone = _normalize_phone(b["phone"])
        try:
            bot.send_contact(chat_id, phone, first_name=b["name"])
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Не удалось отправить контакт клиента: {exc}")
            bot.send_message(chat_id, f"Телефон клиента: {phone}")
        return

    if data.startswith("st:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "Ошибка")
            return
        _, status, code = parts
        b = store.update_status(code, status)
        if not b:
            bot.answer_callback_query(call.id, "Не найдено")
            return
        bot.answer_callback_query(call.id, store.status_label(status))
        try:
            bot.edit_message_text(
                _owner_text(b),
                chat_id,
                call.message.message_id,
                reply_markup=_owner_booking_keyboard(code),
            )
        except Exception:
            bot.send_message(chat_id, _owner_text(b), reply_markup=_owner_booking_keyboard(code))
        return

    if data.startswith("vis:"):
        code = data.split(":", 1)[1]
        b = store.get_by_code(code)
        if not b:
            bot.answer_callback_query(call.id, "Не найдено")
            return
        bot.answer_callback_query(call.id)
        _set_state(chat_id, action="visit_day", mode="visit", data={"code": code})
        bot.send_message(
            chat_id,
            f"📅 Визит для <code>{_e(code)}</code> · {_e(b['name'])}\nВыберите день:",
            reply_markup=_day_keyboard(),
        )
        return

    if data.startswith("vpick:"):
        code = data.split(":", 1)[1]
        b = store.get_by_code(code)
        if not b:
            bot.answer_callback_query(call.id, "Не найдено")
            return
        bot.answer_callback_query(call.id)
        _set_state(chat_id, action="visit_day", mode="visit", data={"code": code})
        bot.send_message(
            chat_id,
            f"📅 Визит для <code>{_e(code)}</code> · {_e(b['name'])}\nВыберите день:",
            reply_markup=_day_keyboard(),
        )
        return

    if data.startswith("cpick:"):
        code = data.split(":", 1)[1]
        b = store.update_status(code, "cancelled")
        _clear_state(chat_id)
        if not b:
            bot.answer_callback_query(call.id, "Не найдено")
            return
        bot.answer_callback_query(call.id, "Отменено")
        bot.send_message(
            chat_id,
            f"❌ Заявка отменена\n\n{_owner_text(b)}",
            reply_markup=_owner_booking_keyboard(code),
        )
        return

    if data.startswith("svc:"):
        try:
            idx = int(data.split(":")[1])
            service = store.SERVICES[idx]
        except (ValueError, IndexError):
            bot.answer_callback_query(call.id, "Ошибка")
            return
        state = _get_state(chat_id)
        d = state.setdefault("data", {})
        d["service"] = service
        _set_state(chat_id, action="add_visit_choice", mode="add", data=d)
        bot.answer_callback_query(call.id, service)
        bot.send_message(
            chat_id,
            f"Услуга: <b>{_e(service)}</b>\n\nНазначить визит сейчас?",
            reply_markup=_visit_later_keyboard(),
        )
        return

    if data == "add:visit_later":
        bot.answer_callback_query(call.id)
        _save_add_without_visit(chat_id)
        return

    if data == "add:visit_now":
        bot.answer_callback_query(call.id)
        _set_state(chat_id, mode="add")
        _ask_day(chat_id)
        return

    if data.startswith("day:"):
        key = data.split(":", 1)[1]
        state = _get_state(chat_id)
        d = state.setdefault("data", {})
        if key == "custom":
            _set_state(chat_id, action="visit_date_custom", data=d)
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, "Введите дату в формате ДД.ММ.ГГГГ:")
            return
        try:
            d["day_offset"] = int(key)
            d.pop("date", None)
        except ValueError:
            bot.answer_callback_query(call.id, "Ошибка")
            return
        _set_state(chat_id, data=d)
        bot.answer_callback_query(call.id)
        _ask_time(chat_id)
        return

    if data.startswith("tm:"):
        key = data.split(":", 1)[1]
        if key == "custom":
            _set_state(chat_id, action="visit_time_custom")
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, "Введите время в формате ЧЧ:ММ (например 15:30):")
            return
        bot.answer_callback_query(call.id)
        _finish_visit(chat_id, key)
        return

    bot.answer_callback_query(call.id)


def _send_status(chat_id: int, query: str):
    """Статус заявки клиенту — только по коду с сайта.

    Номер телефона, присланный текстом, ничего не подтверждает: так заявку мог
    бы посмотреть любой, кто знает чужой номер. Для проверки по номеру есть
    кнопка «Поделиться номером» (обработчик on_contact).
    """
    query = (query or "").strip()
    if not query:
        bot.send_message(
            chat_id,
            "Отправьте код заявки с сайта (5 символов) или нажмите кнопку ниже.",
            reply_markup=_client_menu_keyboard(),
        )
        return
    if not _lookup_allowed(chat_id):
        bot.send_message(
            chat_id,
            "Слишком много попыток. Подождите немного или позвоните нам: "
            f"{config.SERVICE_PHONE}",
            reply_markup=_client_menu_keyboard(),
        )
        return
    b = store.get_by_code(query)
    if b:
        bot.send_message(chat_id, _client_text(b), reply_markup=_call_keyboard())
        return
    if _phone_ok(query):
        bot.send_message(
            chat_id,
            "По номеру, написанному текстом, заявку не показываем — иначе её увидел бы "
            "любой, кто знает ваш номер.\n\n"
            f"Нажмите кнопку «{BTN_CLIENT_PHONE}» внизу: Telegram сам подтвердит, что номер ваш.\n"
            "Или отправьте код заявки с сайта (5 символов).",
            reply_markup=_client_menu_keyboard(),
        )
        return
    bot.send_message(
        chat_id,
        "Заявка не найдена 🤔\n"
        "Проверьте код с сайта (5 символов) или нажмите кнопку ниже, чтобы найти заявку "
        "по своему номеру.\n\n"
        "Если что-то не так — позвоните нам.",
        reply_markup=_client_menu_keyboard(),
    )


def run_polling():
    if not bot:
        return
    _register_handlers()
    reminders.start_background(bot)
    # Важно: при таймауте к api.telegram.org polling не должен умирать навсегда
    backoff = 3
    while True:
        try:
            print("[bot] Polling запущен…")
            bot.infinity_polling(
                skip_pending=True,
                timeout=40,
                long_polling_timeout=35,
                allowed_updates=["message", "callback_query"],
            )
            # штатный выход (stop_polling) — тоже перезапускаем
            print("[bot] Polling остановился, перезапуск через 3 с…")
            time.sleep(3)
            backoff = 3
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] Ошибка polling: {exc}")
            traceback.print_exc()
            print(f"[bot] Перезапуск через {backoff} с…")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
