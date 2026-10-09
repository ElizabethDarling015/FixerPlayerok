"""Раздел «🕒 Последние сделки» (главное меню): список продаж в том же сообщении.

По каждой сделке — раздел, лот, «покупатель | цена» и состояние (возврат / не подтвердил /
завершено, с оценкой отзыва, если он есть); между сделками — линия-разделитель.
Страница — 8 сделок, листание как в «Чатах» (курсоры Playerok держим в памяти).

Откуда данные:

* список — тот же запрос, что страница «Мои продажи» на сайте (`deals`, direction = OUT);
* раздел (игра → категория) в списке сделок не приходит — берём его из списка своих лотов
  (один запрос, кэш уведомлений на 10 минут), а для лотов, которых там нет, — из полной
  сделки (кэш на час). Повторное открытие раздела почти не стоит запросов.
"""
from __future__ import annotations

import asyncio
import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from playerokapi.common.enums import ItemDealDirections

from .common import nav_row, safe_edit

router = Router(name="last_deals")

DEALS_PER_PAGE = 8
#: Разделитель между сделками — такой же, как в уведомлениях.
SEPARATOR = "━━━━━━━━━━━━━━━━━━━"
#: Курсоры страниц (tg_user_id -> курсоры): в callback_data (64 байта) они не помещаются.
_cursors: dict[int, list[str | None]] = {}


def _section_of(item) -> str | None:
    game = getattr(getattr(item, "game", None), "name", None)
    category = getattr(getattr(item, "category", None), "name", None)
    if game and category:
        return f"{game} → {category}"
    return game or category


#: Сырой статус сделки → строка состояния.
_STATE_KEYS = {
    "PAID": "ld_state_paid",
    "SENT": "ld_state_sent",
    "CONFIRMED": "ld_state_confirmed",
    "CONFIRMED_AUTOMATICALLY": "ld_state_auto",
    "ROLLED_BACK": "ld_state_rolled_back",
}


def deal_state(l10n, deal) -> str:
    """Состояние сделки одной строкой: возврат / не подтвердил / завершено (+ оценка отзыва)."""
    raw = getattr(getattr(deal, "raw_status", None), "name", None)
    if getattr(deal, "has_problem", False) and raw not in ("CONFIRMED", "CONFIRMED_AUTOMATICALLY", "ROLLED_BACK"):
        state = l10n("ld_state_problem")
    elif raw in _STATE_KEYS:
        state = l10n(_STATE_KEYS[raw])
    else:
        state = l10n("ld_state_unknown", status=html.escape(raw or "?"))
    rating = getattr(getattr(deal, "review", None), "rating", None)
    if rating:
        state += l10n("ld_review", rating=rating)
    return state


def build_last_deals(l10n, deals, sections: dict, page: int, has_next: bool) -> tuple[str, object]:
    """Текст и кнопки раздела. `sections` — id сделки → раздел."""
    text = l10n("ld_title")
    if not deals:
        text += "\n\n" + l10n("ld_empty")
    else:
        blocks = []
        for deal in deals:
            item = getattr(deal, "item", None)
            price = getattr(item, "price", None)
            blocks.append(l10n(
                "ld_entry",
                section=html.escape(sections.get(deal.id) or "?"),
                item=html.escape(getattr(item, "name", None) or "?"),
                buyer=html.escape(getattr(getattr(deal, "user", None), "username", None) or "?"),
                price=html.escape(f"{price} ₽" if price is not None else "?"),
                state=deal_state(l10n, deal),
            ))
        text += "\n\n" + f"\n{SEPARATOR}\n".join(blocks)
        if page > 0 or has_next:
            text += "\n\n" + l10n("ld_page", page=page + 1)

    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=l10n("chats_btn_prev_page"), callback_data=f"last_deals:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text=l10n("chats_btn_next_page"), callback_data=f"last_deals:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data=f"last_deals:{page}"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


async def _sections_for(fixer, deals) -> dict:
    """Раздел для каждой сделки: из списка своих лотов, иначе из полной сделки (через кэш)."""
    notifier = getattr(fixer, "notifier", None)
    by_item: dict[str, str] = {}
    try:
        if notifier is not None:
            page = await notifier._get_my_items()
        else:
            page = await asyncio.to_thread(fixer.account.get_my_items, None, 100)
        for it in (page.items if page and page.items else []):
            section = _section_of(it)
            if section and getattr(it, "id", None):
                by_item[it.id] = section
    except Exception as exc:
        logger.debug("[last_deals] Список своих лотов не загрузился: {}", exc)

    sections: dict[str, str] = {}
    for deal in deals:
        item_id = getattr(getattr(deal, "item", None), "id", None)
        section = by_item.get(item_id) or _section_of(getattr(deal, "item", None))
        if not section and notifier is not None:
            with suppress(Exception):
                found = await notifier._resolve_section_via_deal_api(deal)
                section = found if found != "Не определено" else None
        sections[deal.id] = section or "?"
    return sections


@router.callback_query(F.data.regexp(r"^last_deals(:\d+)?$"))
async def cb_last_deals(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    if fixer.account is None:
        with suppress(Exception):
            await query.answer(l10n("ld_offline"), show_alert=True)
        return
    with suppress(Exception):
        await query.answer()
    page = int(query.data.split(":", 1)[1]) if ":" in query.data else 0
    cursors = _cursors.setdefault(query.from_user.id, [None])
    while len(cursors) <= page:
        cursors.append(None)
    try:
        deal_list = await asyncio.to_thread(
            lambda: fixer.account.get_deals(count=DEALS_PER_PAGE, after_cursor=cursors[page],
                                            direction=ItemDealDirections.OUT)
        )
    except Exception as exc:
        logger.exception("[last_deals] Не удалось получить сделки")
        await safe_edit(query.message, l10n("ld_title") + "\n\n" + l10n("ld_failed", error=html.escape(str(exc)[:200])),
                        build_last_deals(l10n, [], {}, page, False)[1])
        return
    deals = list(deal_list.deals) if deal_list and deal_list.deals else []
    has_next = bool(deal_list and deal_list.page_info and deal_list.page_info.has_next_page)
    if has_next:
        nxt = deal_list.page_info.end_cursor
        if len(cursors) <= page + 1:
            cursors.append(nxt)
        else:
            cursors[page + 1] = nxt
    sections = await _sections_for(fixer, deals)
    text, markup = build_last_deals(l10n, deals, sections, page, has_next)
    await safe_edit(query.message, text, markup)
