"""Раздел «Чаты с покупателями»: список с пагинацией, история, живой диалог, картинки.

Порт UX чатов из playerok-universal, адаптированный под архитектуру Cardinal.
"""
from __future__ import annotations

import asyncio
import html
import json
import math
from contextlib import suppress
from datetime import datetime

from aiogram import F, Router
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, ReactionTypeEmoji
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from playerokapi import parser
from playerokapi.common.exceptions import PersistedQueryNotFoundError, RequestPlayerokError

from .common import nav_row, safe_edit

router = Router(name="chats")

#: Размеры страниц.
CHATS_PER_PAGE = 6
MESSAGES_LIMIT = 24      # серверный лимит chatMessages — не более 24 за запрос
MESSAGES_PER_PAGE = 8

#: Курсоры страниц списка чатов (tg_user_id -> список курсоров): курсоры длинные,
#: в callback_data (лимит 64 байта) их не положить — держим в кэше.
_list_cursors: dict[int, list[str | None]] = {}

#: Системные маркеры Playerok → человекочитаемый вид (как в universal).
_SYSTEM_MARKERS = {
    "{{ITEM_PAID}}": "🛒 Сделка оплачена",
    "{{ITEM_SENT}}": "📦 Товар отправлен",
    "{{DEAL_CONFIRMED}}": "🤝 Сделка подтверждена",
    "{{DEAL_CONFIRMED_AUTOMATICALLY}}": "🤝 Подтверждено автоматически",
    "{{DEAL_ROLLED_BACK}}": "↩️ Оформлен возврат",
    "{{DEAL_HAS_PROBLEM}}": "⚠️ Проблема в сделке",
    "{{DEAL_PROBLEM_RESOLVED}}": "✅ Проблема решена",
}

#: Seller-безопасный хэш persisted-запроса chatMessages — тот же, что в universal.
_CHAT_MESSAGES_HASH = "9b4e264ff1b20e0fd3929afe023dee8f50affc02b85f80cb4b3dc1516ecfbaa0"

#: Заголовки, которые universal добавляет к этому запросу.
_CHAT_MESSAGES_HEADERS = {
    "accept": "*/*",
    "apollographql-client-name": "web",
    "apollo-require-preflight": "true",
    "x-apollo-operation-name": "chatMessages",
}


class ChatReply(StatesGroup):
    message = State()


class ChatModeGuard(BaseMiddleware):
    """Любое нажатие inline-кнопки сбрасывает режим «живой диалог»."""

    async def __call__(self, handler, event: CallbackQuery, data: dict):
        state: FSMContext = data["state"]
        current = await state.get_state()
        if current is not None and current.startswith("ChatReply:"):
            await state.clear()
            logger.debug("[chats] Режим живого диалога завершён (навигация: {})", event.data)
        return await handler(event, data)


def setup_chat_mode_guard(dispatcher) -> None:
    dispatcher.callback_query.outer_middleware(ChatModeGuard())


# ----------------------------------------------------------------------
# Запросы к Playerok (в потоке, чтобы не блокировать event loop)
# ----------------------------------------------------------------------

async def _get_chats(cardinal, after_cursor=None):
    return await asyncio.to_thread(
        lambda: cardinal.account.get_chats(count=CHATS_PER_PAGE, after_cursor=after_cursor)
    )

async def _get_chat(cardinal, chat_id):
    return await asyncio.to_thread(cardinal.account.get_chat, chat_id)

async def _get_messages(cardinal, chat_id):
    return await asyncio.to_thread(_fetch_messages_sync, cardinal.account, chat_id)

def _fetch_messages_sync(account, chat_id: str, count: int = MESSAGES_LIMIT):
    """История чата: штатный запрос проекта, при 403 — seller-безопасный запрос universal."""
    count = min(count, 24)  # Playerok отдаёт FORBIDDEN при first > 24
    try:
        return account.get_chat_messages(chat_id, count=count)
    except (RequestPlayerokError, PersistedQueryNotFoundError):
        logger.warning(
            "[chats] штатный chatMessages отклонён — пробую seller-безопасный запрос universal…"
        )
    payload = {
        "operationName": "chatMessages",
        "variables": json.dumps(
            {
                "pagination": {"first": count, "after": None},
                "filter": {"chatId": chat_id},
                "hasSupportAccess": False,
                "showForbiddenImage": True,
            },
            separators=(",", ":"),
        ),
        "extensions": json.dumps(
            {"persistedQuery": {"version": 1, "sha256Hash": _CHAT_MESSAGES_HASH}},
            separators=(",", ":"),
        ),
    }
    response = account.request(
        "get", payload=payload, headers=_CHAT_MESSAGES_HEADERS, idempotent=True
    )
    data = (response.json() or {}).get("data") or {}
    return parser.chat_message_list(data.get("chatMessages"))


# ----------------------------------------------------------------------
# Вспомогательное
# ----------------------------------------------------------------------

async def _safe_answer(query: CallbackQuery, *args, **kwargs) -> None:
    """Отвечает на callback, глотая 'query is too old' и повторные ответы."""
    with suppress(Exception):
        await query.answer(*args, **kwargs)

async def _require_online(cardinal, query: CallbackQuery) -> bool:
    """Offline-режим: предупреждающий алерт + лог, раздел недоступен."""
    if cardinal.account is not None:
        return True
    logger.warning("[chats] Раздел недоступен: Playerok не подключён (offline mode)")
    await _safe_answer(
        query,
        "⚠️ Playerok не подключён.\nРаздел «Чаты» доступен в онлайн-режиме.",
        show_alert=True,
    )
    return False

def _other_user(cardinal, chat):
    users = getattr(chat, "users", None) or []
    other = next((u for u in users if u.id != cardinal.account.id), None)
    return other or (users[0] if users else None)

async def _react(message: Message) -> None:
    for emoji in ("✅", "👍"):
        try:
            await message.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
            )
            break
        except Exception:
            continue

def _fmt_time(iso_dt: str | None) -> str:
    """ISO-время Playerok (UTC) → локальное: сегодня — ЧЧ:ММ, старше — ДД.ММ ЧЧ:ММ."""
    if not iso_dt:
        return ""
    try:
        raw = iso_dt[:-1] + "+00:00" if iso_dt.endswith("Z") else iso_dt
        dt = datetime.fromisoformat(raw).astimezone()
        if dt.date() == datetime.now().astimezone().date():
            return dt.strftime("%H:%M")
        return dt.strftime("%d.%m %H:%M")
    except Exception:
        return ""


# ----------------------------------------------------------------------
# Построение экранов
# ----------------------------------------------------------------------

def build_chats_list(cardinal, chat_list, page: int, has_next: bool) -> tuple[str, object]:
    l10n = cardinal.l10n
    text = l10n("chats_title")
    builder = InlineKeyboardBuilder()

    if not chat_list or not chat_list.chats:
        text += "\n\n" + l10n("chats_empty")
    else:
        for chat in chat_list.chats:
            other = _other_user(cardinal, chat)
            username = other.username if other and other.username else "Unknown"
            unread = chat.unread_messages_counter or 0
            badge = f" 🔸{unread}" if unread > 0 else ""
            builder.button(
                text=f"👤 {html.escape(username)}{badge}",
                callback_data=f"chat:view:{chat.id}",
            )
        builder.adjust(1)

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text=l10n("chats_btn_prev_page"), callback_data=f"chats:{page - 1}"))
        if has_next:
            nav.append(InlineKeyboardButton(text=l10n("chats_btn_next_page"), callback_data=f"chats:{page + 1}"))
        if nav:
            builder.row(*nav)

    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


def build_chat_view(cardinal, chat, messages, page: int | None) -> tuple[str, object, list[str]]:
    l10n = cardinal.l10n
    account_id = cardinal.account.id

    other = _other_user(cardinal, chat)
    username = other.username if other and other.username else "Unknown"

    text = l10n("chats_view_title", username=html.escape(username))

    photo_urls: list[str] = []

    if messages is None:
        text += "\n<i>⚠️ История недоступна (Playerok ограничил запрос).</i>"
        text += "\n<i>Режим ответа работает — пишите сюда или жмите «Ответить».</i>"
        chunk: list = []
        pages = 1
        page = 0
    else:
        sorted_msgs = sorted(
            (messages.messages if messages and messages.messages else []),
            key=lambda m: m.created_at or "",
        )
        total = len(sorted_msgs)
        pages = max(1, math.ceil(total / MESSAGES_PER_PAGE))
        if page is None:
            page = pages - 1
        page = min(max(page, 0), pages - 1)
        chunk = sorted_msgs[page * MESSAGES_PER_PAGE:(page + 1) * MESSAGES_PER_PAGE]

    if not chunk:
        if messages is not None:
            text += "\n<i>Сообщений пока нет.</i>"
    else:
        for i, msg in enumerate(chunk):
            time_str = _fmt_time(msg.created_at)

            if msg.text and msg.text in _SYSTEM_MARKERS:
                msg_text = f"<i>{_SYSTEM_MARKERS[msg.text]}</i>"
            elif msg.text:
                msg_text = html.escape(msg.text)
            elif msg.images or msg.file:
                msg_text = "<i>(изображение)</i>"
                for img in (msg.images or []):
                    url = getattr(img, "url", None)
                    if url:
                        photo_urls.append(url)
                file_url = getattr(msg.file, "url", None)
                if file_url:
                    photo_urls.append(file_url)
            elif msg.event:
                msg_text = f"<i>(системное событие: {html.escape(str(msg.event))})</i>"
            else:
                msg_text = "<i>(пустое сообщение)</i>"

            # Лот, прикреплённый к сообщению: название жирным + ссылка моноширинным.
            lot = getattr(msg, "item", None)
            lot_slug = getattr(lot, "slug", None) if lot is not None else None
            if lot_slug:
                lot_url = f"https://playerok.com/products/{lot_slug}"
                lot_name = html.escape(getattr(lot, "name", None) or lot_slug)
                msg_text += f'\n🛍 <b>{lot_name}</b>\n<a href="{lot_url}"><code>{lot_url}</code></a>'

            # Разделитель между блоками сообщений.
            if i > 0:
                text += "\n━━━━━━━━━━━━━━━━━━━━\n"

            if msg.user and msg.user.id == account_id:
                text += f"👤 <b>Вы</b> ({time_str}):\n{msg_text}\n"
            else:
                sender = html.escape(msg.user.username) if msg.user and msg.user.username else html.escape(username)
                text += f"🛒 <b>{sender}</b> ({time_str}):\n{msg_text}\n"

    if pages > 1:
        text += f"\n<i>📄 Стр. {page + 1}/{pages}</i>"
    text += "\n<i>💬 Пишите сюда или отправьте фото — всё уйдёт покупателю, пока открыт этот чат.</i>"
    text += "\n<i>Любая кнопка навигации завершает режим диалога.</i>"

    builder = InlineKeyboardBuilder()
    if pages > 1:
        row = []
        if page > 0:
            row.append(InlineKeyboardButton(text=l10n("chats_btn_older"), callback_data=f"chat:page:{chat.id}:{page - 1}"))
        if page < pages - 1:
            row.append(InlineKeyboardButton(text=l10n("chats_btn_newer"), callback_data=f"chat:page:{chat.id}:{page + 1}"))
        builder.row(*row)
    builder.row(
        InlineKeyboardButton(text=l10n("chats_btn_reply"), callback_data=f"chat:reply:{chat.id}"),
        InlineKeyboardButton(text=l10n("chats_btn_read"), callback_data=f"chat:read:{chat.id}"),
        InlineKeyboardButton(text=l10n("chats_btn_refresh"), callback_data=f"chat:view:{chat.id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ В чаты", callback_data="chats"),
        *nav_row(l10n),
    )
    return text, builder.as_markup(), photo_urls


async def _render_chat_view(query: CallbackQuery, cardinal, chat_id: str, page: int | None) -> None:
    chat = await _get_chat(cardinal, chat_id)
    try:
        messages = await _get_messages(cardinal, chat_id)
    except Exception:
        logger.warning("[chats] История чата {} недоступна — показываю без истории", chat_id)
        messages = None
    text, markup, photo_urls = build_chat_view(cardinal, chat, messages, page)
    await safe_edit(query.message, text, markup)
    for url in photo_urls[:2]:
        with suppress(Exception):
            await query.message.answer_photo(photo=url)


# ----------------------------------------------------------------------
# Хендлеры
# ----------------------------------------------------------------------

@router.callback_query(F.data.regexp(r"^chats(:\d+)?$"))
async def cb_chats_list(query: CallbackQuery, cardinal) -> None:
    """Список чатов с пагинацией — при каждом нажатии свежий запрос к серверу."""
    if not await _require_online(cardinal, query):
        return
    await _safe_answer(query)
    page = int(query.data.split(":", 1)[1]) if ":" in query.data else 0
    try:
        cursors = _list_cursors.setdefault(query.from_user.id, [None])
        while len(cursors) <= page:
            cursors.append(None)
        chat_list = await _get_chats(cardinal, cursors[page])
        has_next = bool(chat_list and chat_list.page_info and chat_list.page_info.has_next_page)
        if has_next:
            nxt = chat_list.page_info.end_cursor
            if len(cursors) <= page + 1:
                cursors.append(nxt)
            elif not cursors[page + 1]:
                cursors[page + 1] = nxt
        text, markup = build_chats_list(cardinal, chat_list, page, has_next)
        await safe_edit(query.message, text, markup)
    except Exception:
        logger.exception("Ошибка при получении списка чатов")

@router.callback_query(F.data.startswith("chat:view:"))
async def cb_chat_view(query: CallbackQuery, cardinal, state: FSMContext) -> None:
    """Открытие чата: свежие сообщения + включение режима живого диалога."""
    if not await _require_online(cardinal, query):
        return
    await _safe_answer(query)
    chat_id = query.data.split(":", 2)[2]
    try:
        await _render_chat_view(query, cardinal, chat_id, None)
    except Exception:
        logger.exception("Ошибка при просмотре чата {}", chat_id)
        return
    await state.set_state(ChatReply.message)
    await state.update_data(chat_id=chat_id)

@router.callback_query(F.data.startswith("chat:page:"))
async def cb_chat_page(query: CallbackQuery, cardinal, state: FSMContext) -> None:
    """Листание истории сообщений."""
    if not await _require_online(cardinal, query):
        return
    await _safe_answer(query)
    _, _, chat_id, page_s = query.data.split(":", 3)
    try:
        await _render_chat_view(query, cardinal, chat_id, int(page_s))
    except Exception:
        logger.exception("Ошибка при листании истории чата {}", chat_id)
        return
    await state.set_state(ChatReply.message)
    await state.update_data(chat_id=chat_id)

@router.callback_query(F.data.startswith("chat:read:"))
async def cb_chat_read(query: CallbackQuery, cardinal) -> None:
    """Отметить чат прочитанным."""
    if not await _require_online(cardinal, query):
        return
    await _safe_answer(query)
    chat_id = query.data.split(":", 2)[2]
    try:
        await asyncio.to_thread(cardinal.account.mark_chat_as_read, chat_id)
        await query.message.answer(cardinal.l10n("chats_read_done"))
    except Exception:
        logger.exception("Ошибка отметки прочитанным чата {}", chat_id)

@router.callback_query(F.data.startswith("chat:reply:"))
async def cb_chat_reply(query: CallbackQuery, cardinal, state: FSMContext) -> None:
    """Явный вход в режим живого диалога."""
    if not await _require_online(cardinal, query):
        return
    await _safe_answer(query)
    chat_id = query.data.split(":", 2)[2]
    try:
        chat = await _get_chat(cardinal, chat_id)
    except Exception:
        logger.exception("Ошибка при открытии чата {}", chat_id)
        return
    other = _other_user(cardinal, chat)
    username = other.username if other and other.username else "Unknown"

    await state.set_state(ChatReply.message)
    await state.update_data(chat_id=chat_id)

    kb = InlineKeyboardBuilder()
    kb.button(text=cardinal.l10n("chats_btn_cancel"), callback_data=f"chat:view:{chat_id}")
    await query.message.answer(
        cardinal.l10n("chats_enter_text", username=html.escape(username)),
        reply_markup=kb.as_markup(),
    )

@router.message(ChatReply.message, F.photo)
async def on_chat_mode_photo(message: Message, state: FSMContext, cardinal) -> None:
    """Фото в режиме диалога уходит покупателю как изображение."""
    chat_id = (await state.get_data()).get("chat_id")
    if not chat_id:
        await state.clear()
        return
    try:
        photo = message.photo[-1]
        tg_file = await message.bot.get_file(photo.file_id)
        buf = await message.bot.download_file(tg_file.file_path)
        image = buf.read()
        await asyncio.to_thread(cardinal.account.send_message, chat_id, None, image)
    except Exception:
        logger.exception("Ошибка при отправке изображения в чат {}", chat_id)
        await message.answer(cardinal.l10n("reply_failed", error="не удалось отправить, см. лог"))
        return
    await _react(message)

@router.message(ChatReply.message, F.text & ~F.text.startswith("/"))
async def on_chat_mode_message(message: Message, state: FSMContext, cardinal) -> None:
    """Текст в режиме живого диалога отправляется покупателю (команды бота — нет)."""
    chat_id = (await state.get_data()).get("chat_id")
    if not chat_id:
        await state.clear()
        return
    try:
        await asyncio.to_thread(cardinal.account.send_message, chat_id, message.text)
    except Exception:
        logger.exception("Ошибка при отправке сообщения в чат {}", chat_id)
        await message.answer(cardinal.l10n("reply_failed", error="не удалось отправить, см. лог"))
        return
    await _react(message)