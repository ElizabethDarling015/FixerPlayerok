"""Раздел «⏳ Сделки в работе» (главное меню, справа от «Чатов»): всё в одном сообщении.

* Список — неподтверждённые продажи и сделки со спором в порядке появления
  (данные — `fixer.deals_in_work`, см. `fixer/deals_in_work.py`). По сделке: лот, раздел,
  покупатель и цена, дата оплаты, пометка «⚠️ Спор».
* Карточка сделки — ряд 1: «✅ Подтвердить выдачу» и «📦 Выдать со склада»,
  ряд 2: «↩️ К списку» и «🏠 Главное меню». Reply на карточку отвечает в чат сделки (строка 🆔).
* «Подтвердить выдачу» — тот же запрос, что кнопка в «Новой сделке» (`updateDeal → SENT`),
  сразу, без промежуточного вопроса.
* «📦 Выдать со склада» отправляет покупателю одну позицию со склада автовыдачи этого лота
  (по нажатию — даже если тумблер автовыдачи выключен) и отмечает выдачу в журнале, чтобы
  товар не ушёл дважды. Нет склада, склад пуст или товар уже выдан — кнопка-заглушка
  отвечает всплывающим сообщением. Выдачу она не подтверждает — это отдельная кнопка.
"""
from __future__ import annotations

import asyncio
import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from playerokapi.autodelivery import AutoDeliveryManager

from ...sales_stats import seller_tz
from .common import nav_row, paginate, pager_row, safe_edit
from .deal_actions import _confirm_with_retry, _is_not_found
from .last_deals import SEPARATOR, _dates_for, _sections_for, format_deal_date

router = Router(name="deals_in_work")

#: Сделок на странице списка.
PER_PAGE = 8
#: Длина названия лота в кнопке.
BUTTON_NAME_LIMIT = 28
#: Последняя открытая страница списка (tg_user_id → страница) — для «↩️ К списку».
_last_page: dict[int, int] = {}


def menu_button_text(fixer) -> str:
    """Текст кнопки главного меню: с числом сделок, если они есть."""
    l10n = fixer.l10n
    tracker = getattr(fixer, "deals_in_work", None)
    count = tracker.count if tracker is not None else 0
    return l10n("dw_btn_count", count=count) if count else l10n("btn_deals_in_work")


def _item_name(deal) -> str:
    return getattr(getattr(deal, "item", None), "name", None) or "?"


def _price(deal) -> str:
    price = getattr(getattr(deal, "item", None), "price", None)
    return f"{price} ₽" if price is not None else "?"


def _buyer(deal) -> str:
    return getattr(getattr(deal, "user", None), "username", None) or "?"


def _button_text(index: int, deal) -> str:
    name = _item_name(deal)
    if len(name) > BUTTON_NAME_LIMIT:
        name = name[:BUTTON_NAME_LIMIT - 1].rstrip() + "…"
    mark = "⚠️ " if getattr(deal, "has_problem", False) else ""
    return f"{index}. {mark}{name}"


def build_list(l10n, deals: list, page: int, sections: dict | None = None,
               dates: dict | None = None, synced: bool = True) -> tuple[str, object]:
    """Текст и кнопки списка. `sections`/`dates` — id сделки → раздел / «дд.мм.гггг, чч:мм»."""
    sections = sections or {}
    dates = dates or {}
    page_deals, page, total_pages, start = paginate(deals, page, PER_PAGE)
    text = l10n("dw_title", count=len(deals))
    if not deals:
        text += "\n\n" + l10n("dw_empty" if synced else "dw_syncing")
    else:
        blocks = []
        for offset, deal in enumerate(page_deals):
            blocks.append(l10n(
                "dw_entry",
                n=start + offset + 1,
                item=html.escape(_item_name(deal)),
                section=html.escape(sections.get(deal.id) or "?"),
                buyer=html.escape(_buyer(deal)),
                price=html.escape(_price(deal)),
                date=html.escape(dates.get(deal.id) or "—"),
                problem=l10n("dw_problem") if getattr(deal, "has_problem", False) else "",
            ))
        text += f"\n{SEPARATOR}\n" + f"\n{SEPARATOR}\n".join(blocks)

    builder = InlineKeyboardBuilder()
    for offset, deal in enumerate(page_deals):
        builder.row(InlineKeyboardButton(text=_button_text(start + offset + 1, deal),
                                         callback_data=f"dw:o:{deal.id}"))
    pager = pager_row("dw:p", page, total_pages)
    if pager:
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data=f"dw:r:{page}"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


def build_card(l10n, deal, *, section: str | None, date: str | None, chat_id: str | None,
               sent: bool, give_state: str, done: bool = False) -> tuple[str, object]:
    """Карточка сделки.

    `give_state` — состояние кнопки «Выдать со склада»: ``ready`` / ``none`` (склада нет) /
    ``empty`` (склад пуст) / ``given`` (уже выдано). `done` — выдача только что подтверждена,
    сделки в работе больше нет: остаётся только навигация.
    """
    problem = bool(getattr(deal, "has_problem", False))
    state = ""
    if problem:
        state += "\n" + l10n("dw_card_problem")
    if sent and problem and not done:
        state += "\n" + l10n("dw_card_sent")
    text = l10n("dw_card_done_title" if done else "dw_card_title") + "\n" + SEPARATOR + "\n" + l10n(
        "dw_card",
        item=html.escape(_item_name(deal)),
        section=html.escape(section or "?"),
        buyer=html.escape(_buyer(deal)),
        price=html.escape(_price(deal)),
        date=html.escape(date or "—"),
        chat_id=html.escape(chat_id or "—"),
    ) + state

    builder = InlineKeyboardBuilder()
    if not done:
        confirm = (InlineKeyboardButton(text=l10n("dw_btn_confirmed"), callback_data=f"dw:sent:{deal.id}")
                   if sent else
                   InlineKeyboardButton(text=l10n("deal_btn_confirm"), callback_data=f"dw:ok:{deal.id}"))
        give_text = l10n("dw_btn_given") if give_state == "given" else l10n("dw_btn_give")
        builder.row(confirm, InlineKeyboardButton(text=give_text, callback_data=f"dw:give:{deal.id}"))
    builder.row(*nav_row(l10n, "dw:back"))
    return text, builder.as_markup()


# ----------------------------------------------------------------------
# Выдача со склада
# ----------------------------------------------------------------------

def give_state(fixer, deal) -> str:
    """Можно ли выдать товар со склада: ready / none / empty / given."""
    manager = getattr(fixer, "autodelivery_manager", None)
    name = _item_name(deal)
    if manager is None or name not in fixer.autodelivery_config.lots:
        return "none"
    ledger = getattr(manager, "ledger", None)
    if ledger is not None and ledger.get_state(deal.id) in ("reserved", "sent"):
        return "given"
    with suppress(Exception):
        if manager.get_stock_size(name) <= 0:
            return "empty"
    return "ready"


def deliver_from_stock(fixer, deal, chat_id: str) -> tuple[str, str | None]:
    """Забирает позицию со склада и шлёт покупателю. Возвращает (итог, ошибка).

    Итог: ``ok`` / ``none`` / ``empty`` / ``given`` / ``failed``. Синхронно — звать из потока.
    """
    state = give_state(fixer, deal)
    if state != "ready":
        return state, None
    manager = fixer.autodelivery_manager
    name = _item_name(deal)
    # Мимо тумблера автовыдачи: вы нажали кнопку сами.
    value = AutoDeliveryManager.reserve(manager, name)
    if value is None:
        return "empty", None
    ledger = getattr(manager, "ledger", None)
    if ledger is not None:
        ledger.mark_reserved(deal.id, name)
    try:
        fixer.account.send_message(chat_id, manager.format_delivery_text(value))
    except Exception as exc:
        logger.warning("[в работе] Товар по сделке {} не отправлен — возвращаю на склад: {}", deal.id, exc)
        try:
            manager.restore(name, value)
            if ledger is not None:
                ledger.mark_restored(deal.id)
        except Exception:
            logger.error("[в работе] Не удалось вернуть товар на склад лота {!r}", name)
        return "failed", str(exc).strip() or type(exc).__name__
    if ledger is not None:
        ledger.mark_sent(deal.id)
    logger.info("[в работе] Товар по лоту {!r} выдан со склада вручную (сделка {})", name, deal.id)
    return "ok", None


# ----------------------------------------------------------------------
# Хендлеры
# ----------------------------------------------------------------------

async def _answer(query: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(Exception):
        await query.answer(text, show_alert=alert)


async def _dates(fixer, deals) -> dict[str, str]:
    tz = seller_tz(fixer.settings)
    try:
        isos = await _dates_for(fixer, deals)
    except Exception as exc:
        logger.debug("[в работе] Даты сделок не загрузились: {}", exc)
        return {}
    return {deal_id: format_deal_date(iso, tz) for deal_id, iso in isos.items()}


async def show_list(query: CallbackQuery, fixer, page: int) -> None:
    l10n = fixer.l10n
    tracker = fixer.deals_in_work
    _last_page[query.from_user.id] = page
    deals = tracker.deals()
    page_deals = paginate(deals, page, PER_PAGE)[0]
    sections = await _sections_for(fixer, page_deals) if page_deals else {}
    dates = await _dates(fixer, page_deals) if page_deals else {}
    text, markup = build_list(l10n, deals, page, sections, dates, synced=tracker.synced)
    await safe_edit(query.message, text, markup)


async def show_card(query: CallbackQuery, fixer, deal, *, done: bool = False) -> None:
    tracker = fixer.deals_in_work
    notifier = getattr(fixer, "notifier", None)
    section = (await _sections_for(fixer, [deal])).get(deal.id)
    date = (await _dates(fixer, [deal])).get(deal.id)
    chat_id = None
    if notifier is not None:
        with suppress(Exception):
            chat_id = await notifier._resolve_deal_chat_id(deal)
    text, markup = build_card(fixer.l10n, deal, section=section, date=date, chat_id=chat_id,
                              sent=tracker.is_sent(deal.id), give_state=give_state(fixer, deal), done=done)
    await safe_edit(query.message, text, markup)


def _offline(fixer) -> bool:
    return fixer.account is None or not fixer.playerok_connected


@router.callback_query(F.data == "dw")
@router.callback_query(F.data.regexp(r"^dw:(p|r):\d+$"))
async def cb_list(query: CallbackQuery, fixer) -> None:
    if _offline(fixer):
        await _answer(query, fixer.l10n("dw_offline"), alert=True)
        return
    await _answer(query)
    parts = query.data.split(":")
    page = int(parts[2]) if len(parts) == 3 else 0
    if len(parts) == 3 and parts[1] == "r":
        await fixer.deals_in_work.resync(fixer)
    await show_list(query, fixer, page)


@router.callback_query(F.data == "dw:back")
async def cb_back(query: CallbackQuery, fixer) -> None:
    await _answer(query)
    await show_list(query, fixer, _last_page.get(query.from_user.id, 0))


@router.callback_query(F.data.startswith("dw:o:"))
async def cb_open(query: CallbackQuery, fixer) -> None:
    deal = fixer.deals_in_work.get(query.data.split(":", 2)[2])
    if deal is None:
        await _answer(query, fixer.l10n("dw_gone"), alert=True)
        await show_list(query, fixer, _last_page.get(query.from_user.id, 0))
        return
    await _answer(query)
    await show_card(query, fixer, deal)


@router.callback_query(F.data.startswith("dw:sent:"))
async def cb_already_sent(query: CallbackQuery, fixer) -> None:
    await _answer(query, fixer.l10n("dw_already_sent"), alert=True)


@router.callback_query(F.data.startswith("dw:ok:"))
async def cb_confirm(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    tracker = fixer.deals_in_work
    deal_id = query.data.split(":", 2)[2]
    deal = tracker.get(deal_id)
    if _offline(fixer):
        await _answer(query, l10n("deal_confirm_offline"), alert=True)
        return
    if deal is None:
        await _answer(query, l10n("dw_gone"), alert=True)
        await show_list(query, fixer, _last_page.get(query.from_user.id, 0))
        return
    try:
        await _confirm_with_retry(fixer, deal_id)
    except Exception as exc:
        if _is_not_found(exc):
            await _answer(query, l10n("deal_confirm_not_ready"), alert=True)
            return
        logger.exception("[в работе] Не удалось подтвердить выдачу по сделке {}", deal_id)
        reason = str(exc).strip() or type(exc).__name__
        await _answer(query, l10n("deal_confirm_failed", error=reason[:150]), alert=True)
        return
    logger.info("[в работе] Выдача по сделке {} подтверждена из раздела", deal_id)
    tracker.mark_sent(deal_id)
    await _answer(query, l10n("deal_confirm_ok"), alert=True)
    # Остался в разделе (спор) — обычная карточка, иначе — «✅ Выдача подтверждена».
    await show_card(query, fixer, deal, done=tracker.get(deal_id) is None)


@router.callback_query(F.data.startswith("dw:give:"))
async def cb_give(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    deal = fixer.deals_in_work.get(query.data.split(":", 2)[2])
    if deal is None:
        await _answer(query, l10n("dw_gone"), alert=True)
        await show_list(query, fixer, _last_page.get(query.from_user.id, 0))
        return
    state = give_state(fixer, deal)
    if state != "ready":
        await _answer(query, l10n("dw_give_" + state), alert=True)
        return
    if _offline(fixer):
        await _answer(query, l10n("deal_confirm_offline"), alert=True)
        return
    chat_id = None
    notifier = getattr(fixer, "notifier", None)
    with suppress(Exception):
        chat_id = (await notifier._resolve_deal_chat_id(deal) if notifier is not None
                   else getattr(getattr(deal, "chat", None), "id", None))
    if not chat_id:
        await _answer(query, l10n("dw_give_no_chat"), alert=True)
        return
    result, error = await asyncio.to_thread(deliver_from_stock, fixer, deal, chat_id)
    if result == "failed":
        await _answer(query, l10n("dw_give_failed", error=(error or "?")[:150]), alert=True)
        return
    await _answer(query, l10n("dw_give_" + result), alert=True)
    await show_card(query, fixer, deal)
