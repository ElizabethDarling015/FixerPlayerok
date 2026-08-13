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
from aiogram.types import Message, ReactionTypeEmoji
from loguru import logger

router = Router(name="replies")

#: ID чата Playerok — UUID в тексте уведомления (фолбэк после перезапуска бота).
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


async def mark_sent_reaction(message: Message) -> bool:
    """
    Помечает сообщение продавца реакцией-галочкой после успешной отправки в Playerok.
    Пробует ✅ → 👍; если реакции недоступны — возвращает False (тогда шлём текст).
    """
    for emoji in ("✅", "👍"):
        try:
            await message.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
            )
            return True
        except Exception:
            continue
    return False


def _extract_chat_id(quoted: str) -> str | None:
    """Достаёт ID чата Playerok из текста уведомления (работает после рестарта)."""
    m = _UUID_RE.search(quoted or "")
    return m.group(0) if m else None


@router.message(F.reply_to_message, F.text)
async def on_reply(message: Message, state: FSMContext, cardinal, notifier) -> None:
    if await state.get_state() is not None:
        return  # идёт FSM-диалог другого раздела — не перехватываем
    l10n = cardinal.l10n
    chat_id = notifier.reply_map.get((message.chat.id, message.reply_to_message.message_id))
    if chat_id is None:
        # Бот перезапускался и соответствие в памяти потеряно —
        # восстанавливаем чат из текста самого уведомления.
        quoted = message.reply_to_message.text or message.reply_to_message.caption or ""
        chat_id = _extract_chat_id(quoted)
    if chat_id is None:
        await message.answer(l10n("reply_unknown"))
        return
    try:
        await asyncio.to_thread(cardinal.account.send_message, chat_id, message.text)
    except Exception as exc:
        logger.exception("Не удалось отправить ответ из TG в чат Playerok {}", chat_id)
        await message.answer(l10n("reply_failed", error=str(exc)))
        return

    # Вместо текста "✅ Отправлено" — реакция на сообщение
    if not await mark_sent_reaction(message):
        await message.answer(l10n("reply_sent"))