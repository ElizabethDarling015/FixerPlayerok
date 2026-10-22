"""Кнопки уведомлений о связи с Playerok: «🔄 Повторить подключение» и «📄 Логи»."""
from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..notifications import close_keyboard
from .common import safe_edit
from .system import build_logs_view

router = Router(name="playerok_link")


@router.callback_query(F.data == "plk:retry")
async def cb_retry(query: CallbackQuery, fixer) -> None:
    """Обрывает текущую попытку (или паузу) и сразу начинает новую. Само сообщение остаётся:
    после подключения оно превратится в «✅ Успешное подключение»."""
    l10n = fixer.l10n
    origin = (query.message.chat.id, query.message.message_id)
    if fixer.playerok_link.retry_now(origin) == "connected":
        await safe_edit(query.message, l10n("notif_playerok_connected"), close_keyboard(l10n))
        with suppress(Exception):
            await query.answer(l10n("plink_already_connected"))
        return
    with suppress(Exception):
        await query.answer(l10n("plink_retry_started"))


@router.callback_query(F.data == "plk:logs")
async def cb_logs(query: CallbackQuery, fixer) -> None:
    """Раздел «📄 Логи» новым сообщением: предупреждение остаётся и потом станет «✅ …»."""
    text, markup = build_logs_view(fixer)
    await query.message.answer(text, reply_markup=markup)
    with suppress(Exception):
        await query.answer()
