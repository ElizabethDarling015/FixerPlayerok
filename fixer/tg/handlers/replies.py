"""
Ответ из Telegram в чат Playerok: reply на уведомление о новом сообщении пересылает
текст собеседнику на Playerok (соответствие хранит `Notifier.reply_map`).

Роутер подключается последним: он ловит только сообщения-реплаи вне FSM-диалогов.
"""
from __future__ import annotations

import asyncio
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from ..reactions import deliver, precheck
from .chats import _format_quick_response, _match_quick_command, _other_user

router = Router(name="replies")

#: ID чата Playerok — UUID в тексте уведомления (фолбэк после перезапуска бота).
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _extract_chat_id(quoted: str) -> str | None:
    """Достаёт ID чата Playerok из текста уведомления (работает после рестарта)."""
    m = _UUID_RE.search(quoted or "")
    return m.group(0) if m else None


@router.message(F.reply_to_message, F.text)
async def on_reply(message: Message, state: FSMContext, fixer, notifier) -> None:
    if await state.get_state() is not None:
        return  # идёт FSM-диалог другого раздела — не перехватываем
    chat_id = notifier.reply_map.get((message.chat.id, message.reply_to_message.message_id))
    if chat_id is None:
        # Бот перезапускался и соответствие в памяти потеряно —
        # восстанавливаем чат из текста самого уведомления.
        replied = message.reply_to_message
        # Невидимая ссылка в начале уведомления (https://playerok.com/chats/<id>)…
        for entity in (replied.entities or replied.caption_entities or []):
            if getattr(entity, "url", None):
                chat_id = _extract_chat_id(entity.url)
                if chat_id:
                    break
        # …или строка 🆔 в самом тексте (уведомление о сделке).
        if chat_id is None:
            quoted = replied.text or replied.caption or ""
            chat_id = _extract_chat_id(quoted)
    # Не тот чат → 🤷, нет связи → 🤬 (без лишних запросов).
    if not await precheck(message, fixer, chat_id):
        return
    # Быстрые команды продавца: !!команда → шаблонный текст автоответчика
    text_to_send = message.text
    quick = _match_quick_command(fixer, message.text)
    if quick is not None:
        command, template = quick
        try:
            chat = await asyncio.to_thread(fixer.account.get_chat, chat_id)
            other = _other_user(fixer, chat)
            username = other.username if other and other.username else "?"
        except Exception:
            username = "?"
        text_to_send = _format_quick_response(template, username=username, chat_id=chat_id)
        logger.info("[replies] Быстрая команда продавца {!r} → чат {}", command, chat_id)

    # Отправлено → 👍, нет связи → 🤬, Playerok не принял → 🤷 + просьба посмотреть лог.
    await deliver(message, fixer, chat_id, text_to_send, check=False)
