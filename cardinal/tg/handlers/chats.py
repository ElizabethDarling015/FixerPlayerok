"""Раздел «Чаты с покупателями»: актуальный список, история и режим «живого диалога»."""
from __future__ import annotations

import asyncio
import html

from aiogram import F, Router
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReactionTypeEmoji
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from playerokapi import parser
from playerokapi.common.exceptions import RequestPlayerokError

from .common import nav_row, safe_edit

router = Router(name="chats")

#: Сколько чатов показывать в списке и сообщений в истории.
CHATS_LIMIT = 6
MESSAGES_LIMIT = 50

#: Минимальный полнотекстовый запрос истории чата. Используется как фолбэк, когда
#: persisted `chatMessages` возвращает 403 FORBIDDEN (в его тексте есть support-поля,
#: закрытые для seller-аккаунтов). Запрашиваем только безопасные поля участника чата.
CHAT_MESSAGES_MINIMAL_QUERY = """
query chatMessages($pagination: Pagination, $filter: ChatMessageFilter) {
  chatMessages(pagination: $pagination, filter: $filter) {
    edges {
      node {
        id
        text
        createdAt
        deletedAt
        isRead
        isAutoResponse
        event
        imageLinks
        file {
          id
          url
          __typename
        }
        images {
          id
          url
          __typename
        }
        user {
          id
          username
          role
          avatarURL
          isOnline
          __typename
        }
        eventByUser {
          id
          username
          __typename
        }
        eventToUser {
          id
          username
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}
"""


class ChatReply(StatesGroup):
    message = State()


class ChatModeGuard(BaseMiddleware):
    """
    Сторож режима «живой диалог».

    Пока открыт чат (активно состояние `ChatReply`), любой текст в бота уходит
    покупателю. ЛЮБОЕ нажатие inline-кнопки (главное меню, другой раздел, список
    чатов…) сбрасывает состояние — сообщения снова работают по стандартной логике.
    """

    async def __call__(self, handler, event: CallbackQuery, data: dict):
        state: FSMContext = data["state"]
        current = await state.get_state()
        if current is not None and current.startswith("ChatReply:"):
            await state.clear()
            logger.debug("[chats] Режим живого диалога завершён (навигация: {})", event.data)
        return await handler(event, data)


def setup_chat_mode_guard(dispatcher) -> None:
    """Вешает сторожа на все callback-кнопки панели (вызывается из setup_routers)."""
    dispatcher.callback_query.outer_middleware(ChatModeGuard())


# ----------------------------------------------------------------------
# Запросы к Playerok (в потоке, чтобы не блокировать event loop)
# ----------------------------------------------------------------------

async def _get_chats(cardinal):
    return await asyncio.to_thread(cardinal.account.get_chats, count=CHATS_LIMIT)


async def _get_chat(cardinal, chat_id):
    return await asyncio.to_thread(cardinal.account.get_chat, chat_id)


async def _get_messages(cardinal, chat_id):
    return await asyncio.to_thread(_fetch_messages_sync, cardinal.account, chat_id)


async def _send_message(cardinal, chat_id, text):
    return await asyncio.to_thread(cardinal.account.send_message, chat_id, text)


def _fetch_messages_sync(account, chat_id: str, count: int = MESSAGES_LIMIT):
    """История чата: штатный persisted-запрос, при 403 — минимальный POST-фолбэк."""
    try:
        return account.get_chat_messages(chat_id, count=count)
    except RequestPlayerokError as exc:
        logger.warning(
            "[chats] persisted-запрос chatMessages отклонён ({}). "
            "Пробую минимальный POST-запрос без support-полей…",
            getattr(exc, "error_message", exc),
        )
        variables = {"pagination": {"first": count}, "filter": {"chatId": chat_id}}
        response = account.request(
            "post",
            payload={
                "operationName": "chatMessages",
                "variables": variables,
                "query": CHAT_MESSAGES_MINIMAL_QUERY,
            },
            idempotent=True,
        )
        data = (response.json() or {}).get("data") or {}
        return parser.chat_message_list(data.get("chatMessages"))


# ----------------------------------------------------------------------
# Построение экранов
# ----------------------------------------------------------------------

def _other_user(cardinal, chat):
    """Собеседник чата (все участники кроме меня)."""
    users = getattr(chat, "users", None) or []
    other = next((u for u in users if u.id != cardinal.account.id), None)
    return other or (users[0] if users else None)


def build_chats_list(cardinal, chat_list) -> tuple[str, object]:
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
            badge = f" ({unread})" if unread > 0 else ""
            builder.button(
                text=f"👤 {html.escape(username)}{badge}",
                callback_data=f"chat:view:{chat.id}",
            )
        builder.adjust(1)

    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


def build_chat_view(cardinal, chat, messages) -> tuple[str, object]:
    l10n = cardinal.l10n
    account_id = cardinal.account.id

    other = _other_user(cardinal, chat)
    username = other.username if other and other.username else "Unknown"

    text = l10n("chats_view_title", username=html.escape(username))

    if not messages or not messages.messages:
        text += "\n<i>Сообщений пока нет.</i>"
    else:
        # От старых к новым.
        sorted_msgs = sorted(messages.messages, key=lambda m: m.created_at or "")
        for msg in sorted_msgs:
            time_str = ""
            if msg.created_at:
                try:
                    time_str = msg.created_at.split("T")[1].split(".")[0][:5]
                except Exception:
                    pass

            if msg.text:
                msg_text = html.escape(msg.text)
            elif msg.file or msg.images:
                msg_text = "<i>(изображение/файл)</i>"
            elif msg.event:
                msg_text = f"<i>(системное событие: {html.escape(str(msg.event))})</i>"
            else:
                msg_text = "<i>(пустое сообщение)</i>"

            if msg.user and msg.user.id == account_id:
                text += f"\n👤 <b>Вы</b> ({time_str}):\n{msg_text}\n"
            else:
                sender = html.escape(msg.user.username) if msg.user and msg.user.username else html.escape(username)
                text += f"\n🛒 <b>{sender}</b> ({time_str}):\n{msg_text}\n"

    text += "\n<i>💬 Пишите сообщения сюда — они уходят покупателю, пока открыт этот чат.</i>"
    text += "\n<i>Любая кнопка навигации завершает режим диалога.</i>"

    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_chats"), callback_data="chats")
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


# ----------------------------------------------------------------------
# Хендлеры
# ----------------------------------------------------------------------

@router.callback_query(F.data == "chats")
async def cb_chats_list(query: CallbackQuery, cardinal) -> None:
    """Список чатов — при каждом нажатии свежий запрос к серверу."""
    try:
        chat_list = await _get_chats(cardinal)
        text, markup = build_chats_list(cardinal, chat_list)
        await safe_edit(query.message, text, markup)
    except Exception as exc:
        logger.exception("Ошибка при получении списка чатов")
        await query.answer(f"Ошибка: {exc}", show_alert=True)
        return
    await query.answer()


@router.callback_query(F.data.startswith("chat:view:"))
async def cb_chat_view(query: CallbackQuery, cardinal, state: FSMContext) -> None:
    """Открытие чата: история сообщений + включение режима живого диалога."""
    chat_id = query.data.split(":", 2)[2]
    try:
        chat = await _get_chat(cardinal, chat_id)
        messages = await _get_messages(cardinal, chat_id)
        text, markup = build_chat_view(cardinal, chat, messages)
        await safe_edit(query.message, text, markup)
    except Exception as exc:
        logger.exception("Ошибка при просмотре чата {}", chat_id)
        await query.answer(f"Ошибка: {exc}", show_alert=True)
        return

    # Включаем режим живого диалога: любой текст в бота уходит в этот чат.
    await state.set_state(ChatReply.message)
    await state.update_data(chat_id=chat_id)
    await query.answer()


@router.message(ChatReply.message, F.text)
async def on_chat_mode_message(message: Message, state: FSMContext, cardinal) -> None:
    """Любой текст в режиме живого диалога отправляется покупателю на Playerok."""
    chat_id = (await state.get_data()).get("chat_id")
    if not chat_id:
        await state.clear()
        return

    try:
        await _send_message(cardinal, chat_id, message.text)
    except Exception as exc:
        logger.exception("Ошибка при отправке сообщения в чат {}", chat_id)
        await message.answer(f"❌ Ошибка отправки: {exc}")
        return

    # Реакция-галочка вместо спама сообщениями (как в replies.py).
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