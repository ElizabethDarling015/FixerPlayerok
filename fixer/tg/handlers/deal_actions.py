"""Кнопки под уведомлением «Новая сделка»: «Подтвердить выдачу» и «Свернуть».

* «Свернуть» — уведомление сжимается до 5 строк (раздел, лот, покупатель, цена, 🆔),
  картинка лота остаётся, reply на сообщение по-прежнему отвечает в чат (по строке 🆔).
* «Подтвердить выдачу» — на Playerok сделка переводится в статус «отправлено»
  (тот же запрос `updateDeal → SENT`, что делает кнопка на сайте), затем алерт
  и то же сворачивание. При ошибке — алерт с причиной, кнопки остаются.

Нажатие любой из кнопок убирает обе. Всё нужное — в самой кнопке (ID сделки) и в тексте
уведомления, поэтому кнопки работают и после перезапуска бота.
"""
from __future__ import annotations

import asyncio
import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, LinkPreviewOptions
from loguru import logger

from playerokapi.common.enums import ItemDealStatuses

router = Router(name="deal_actions")

#: Строка уведомления → поле свёрнутого вида (по эмодзи в начале строки — не зависит от языка).
_FIELDS = {"📂": "section", "🎁": "item", "👤": "buyer", "💰": "price", "🆔": "chat_id"}


def parse_deal_notification(text: str) -> dict[str, str]:
    """Достаёт значения полей из текста уведомления «Новая сделка» (как его отдаёт Telegram)."""
    values: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip().lstrip("​")
        for emoji, field in _FIELDS.items():
            if field in values or not line.startswith(emoji):
                continue
            rest = line[len(emoji):].strip()
            if field != "chat_id":
                # «Раздел: X» → «X»; у 🆔 подписи нет.
                rest = rest.split(":", 1)[1].strip() if ":" in rest else rest
            values[field] = rest
    return values


def build_collapsed_text(l10n, text: str) -> str:
    v = parse_deal_notification(text)
    return l10n(
        "notif_new_deal_short",
        section=html.escape(v.get("section", "?")),
        item=html.escape(v.get("item", "?")),
        buyer=html.escape(v.get("buyer", "?")),
        price=html.escape(v.get("price", "?")),
        chat_id=html.escape(v.get("chat_id", "—")),
    )


async def _answer(query: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(Exception):
        await query.answer(text, show_alert=alert)


async def collapse(query: CallbackQuery, fixer) -> None:
    """Сжимает уведомление и убирает кнопки (картинка, если была, остаётся)."""
    message = query.message
    # Совсем старое/удалённое сообщение Telegram отдаёт как InaccessibleMessage — без текста.
    if message is None or not hasattr(message, "caption"):
        return
    source = message.caption if message.caption is not None else (message.text or "")
    short = build_collapsed_text(fixer.l10n, source)
    try:
        if message.photo or message.caption is not None:
            await message.edit_caption(caption=short, reply_markup=None)
        else:
            await message.edit_text(short, reply_markup=None,
                                    link_preview_options=LinkPreviewOptions(is_disabled=True))
    except TelegramBadRequest as exc:
        # Уже свёрнуто (повторное нажатие) — не ошибка.
        logger.debug("[deal] сворачивание не выполнено: {}", exc)


@router.callback_query(F.data == "dl:min")
async def cb_collapse(query: CallbackQuery, fixer) -> None:
    await collapse(query, fixer)
    await _answer(query)


@router.callback_query(F.data == "dl:test")
async def cb_confirm_test(query: CallbackQuery, fixer) -> None:
    """Кнопка из образца в «Настройки → Тесты»: ничего не отправляет на Playerok."""
    await _answer(query, fixer.l10n("deal_confirm_test"), alert=True)
    await collapse(query, fixer)


@router.callback_query(F.data.startswith("dl:ok:"))
async def cb_confirm(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    deal_id = query.data.split(":", 2)[2]
    if fixer.account is None:
        await _answer(query, l10n("deal_confirm_offline"), alert=True)
        return
    try:
        await asyncio.to_thread(fixer.account.update_deal, deal_id, ItemDealStatuses.SENT)
    except Exception as exc:
        logger.exception("[deal] Не удалось подтвердить выдачу по сделке {}", deal_id)
        reason = str(exc).strip() or type(exc).__name__
        await _answer(query, l10n("deal_confirm_failed", error=reason[:150]), alert=True)
        return
    logger.info("[deal] Выдача по сделке {} подтверждена из Telegram", deal_id)
    await _answer(query, l10n("deal_confirm_ok"), alert=True)
    await collapse(query, fixer)
