"""
Ответ из Telegram в чат Playerok: reply на уведомление о новом сообщении пересылает
текст собеседнику на Playerok (соответствие хранит `Notifier.reply_map`).

Роутер подключается последним: он ловит только сообщения-реплаи вне FSM-диалогов.
"""
from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

router = Router(name="replies")


@router.message(F.reply_to_message, F.text)
async def on_reply(message: Message, state: FSMContext, cardinal, notifier) -> None:
    if await state.get_state() is not None:
        return  # идёт FSM-диалог другого раздела — не перехватываем
    l10n = cardinal.l10n
    chat_id = notifier.reply_map.get((message.chat.id, message.reply_to_message.message_id))
    if chat_id is None:
        await message.answer(l10n("reply_unknown"))
        return
    try:
        await asyncio.to_thread(cardinal.account.send_message, chat_id, message.text)
    except Exception as exc:
        logger.exception("Не удалось отправить ответ из TG в чат Playerok {}", chat_id)
        await message.answer(l10n("reply_failed", error=str(exc)))
        return
    await message.answer(l10n("reply_sent"))
