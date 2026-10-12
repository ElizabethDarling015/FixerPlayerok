"""Раздел «🛍 Товары» (главное меню): свои лоты на Playerok по разделам и карточка лота.

Экраны:

1. Разделы («JetBrains → Подписки (8)») — только активные лоты и лоты на модерации.
   Внизу — «⏸ Снятые и заблокированные».
2. Лоты раздела: значок статуса, название, цена; 🔁 — включено автовыставление.
3. Карточка лота: цена, статус, премиум, срок выставления, просмотры и продажи, комментарий,
   автовыставление, автовыдача. Действия:

   * 🔁 Автовыставление — тот же переключатель, что «Оставлять в продаже» на сайте:
     после продажи лот остаётся на витрине (Playerok сам делает проданную копию);
   * 💬 Комментарий / 💰 Цена — правка на Playerok (после правки комментария лот ненадолго
     уходит на модерацию, цена — без модерации);
   * ⬆️ Поднять — платно, сначала экран с ценой; срок выставления начинается заново;
   * ⏸ Снять с продажи / ▶️ Вернуть в продажу — бесплатно;
   * 🔄 Выставить заново — для истёкших лотов, платно, сначала экран с ценой.

Ничего платного без отдельного нажатия «✅ …» на экране с ценой не делается.
"""
from __future__ import annotations

import asyncio
import html
import time
from contextlib import suppress

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from playerokapi.common.exceptions import RequestPlayerokError

from ...sales_stats import _parse_dt, seller_tz
from ...storefront import (INACTIVE_STATUSES, STATUS_EMOJI, ItemsCache, fetch_items, group_by_section,
                           section_of, status_name)
from .common import nav_row, pager_row, remember_panel, safe_edit, show_in_panel, with_error

router = Router(name="items")

SECTIONS_PER_PAGE = 10
ITEMS_PER_PAGE = 10
NAME_LIMIT = 38
COMMENT_LIMIT = 700
#: Сколько ждать новый текст комментария / цену; потом сообщения снова обычные.
WAIT_SECONDS = 10 * 60

cache = ItemsCache()
#: Ожидающее подтверждения платное действие (tg_user_id → данные): в callback_data не влезает.
_pending: dict[int, dict] = {}


class ItemEdit(StatesGroup):
    comment = State()
    price = State()


# ----------------------------------------------------------------------
# Тексты и кнопки (чистые функции — для тестов)
# ----------------------------------------------------------------------

def _short(name: str | None, limit: int = NAME_LIMIT) -> str:
    name = (name or "?").strip()
    return name if len(name) <= limit else name[: limit - 1] + "…"


def item_button_text(item) -> str:
    emoji = STATUS_EMOJI.get(status_name(item) or "", "❔")
    keep = " 🔁" if getattr(item, "keep_in_sale", False) else ""
    return f"{emoji} {_short(item.name)} · {item.price} ₽{keep}"


def build_sections(l10n, items, page: int = 0) -> tuple[str, object]:
    groups = group_by_section(items)
    total_pages = max(1, -(-len(groups) // SECTIONS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    on_sale = sum(1 for it in items if status_name(it) == "APPROVED")
    moderation = len(items) - on_sale
    text = l10n("it_title", on_sale=on_sale, moderation=moderation)
    if not groups:
        text += "\n\n" + l10n("it_empty")
    builder = InlineKeyboardBuilder()
    start = page * SECTIONS_PER_PAGE
    for index, (name, group) in enumerate(groups[start:start + SECTIONS_PER_PAGE], start=start):
        builder.row(InlineKeyboardButton(text=f"{name} ({len(group)})", callback_data=f"it:s:{index}:0"))
    if pager := pager_row("it:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("it_btn_inactive"), callback_data="it:x:0"))
    builder.row(InlineKeyboardButton(text=l10n("it_btn_refresh"), callback_data="it:r"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


def build_section_items(l10n, items, section_index: int, page: int = 0) -> tuple[str, object] | None:
    groups = group_by_section(items)
    if not 0 <= section_index < len(groups):
        return None
    name, group = groups[section_index]
    total_pages = max(1, -(-len(group) // ITEMS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    text = l10n("it_section_title", section=html.escape(name), count=len(group))
    builder = InlineKeyboardBuilder()
    start = page * ITEMS_PER_PAGE
    for item in group[start:start + ITEMS_PER_PAGE]:
        builder.row(InlineKeyboardButton(text=item_button_text(item), callback_data=f"it:v:{item.id}"))
    if pager := pager_row(f"it:s:{section_index}", page, total_pages):
        builder.row(*pager)
    builder.row(*nav_row(l10n, f"it:p:{section_index // SECTIONS_PER_PAGE}"))
    return text, builder.as_markup()


_INACTIVE_ORDER = ("DISCONTINUED", "BLOCKED", "DECLINED", "EXPIRED")
#: Статусы, в которых сайт показывает «Оставлять в продаже».
ACTIVE_STATUS_NAMES = ("APPROVED", "PENDING_MODERATION", "PENDING_APPROVAL")


def build_inactive(l10n, items, page: int = 0) -> tuple[str, object]:
    ordered = sorted(items, key=lambda it: (_INACTIVE_ORDER.index(status_name(it))
                                            if status_name(it) in _INACTIVE_ORDER else 9,
                                            (it.name or "").lower()))
    counts = {s: sum(1 for it in items if status_name(it) == s) for s in _INACTIVE_ORDER}
    text = l10n("it_inactive_title", discontinued=counts["DISCONTINUED"], blocked=counts["BLOCKED"],
                declined=counts["DECLINED"], expired=counts["EXPIRED"])
    if not ordered:
        text += "\n\n" + l10n("it_inactive_empty")
    total_pages = max(1, -(-len(ordered) // ITEMS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    builder = InlineKeyboardBuilder()
    start = page * ITEMS_PER_PAGE
    for item in ordered[start:start + ITEMS_PER_PAGE]:
        builder.row(InlineKeyboardButton(text=item_button_text(item), callback_data=f"it:v:{item.id}"))
    if pager := pager_row("it:x", page, total_pages):
        builder.row(*pager)
    builder.row(*nav_row(l10n, "it"))
    return text, builder.as_markup()


def _status_label(l10n, status: str) -> str:
    key = "it_status_" + status.lower()
    label = l10n(key)
    return status if label == key else label


def format_until(iso: str | None, tz=None) -> str | None:
    dt = _parse_dt(iso)
    return dt.astimezone(tz).strftime("%d.%m.%Y в %H:%M") if dt is not None else None


def build_item_card(l10n, item, autodelivery: str, tz=None, back: str = "it", notice: str | None = None):
    status = status_name(item) or "?"
    priority = getattr(getattr(item, "priority", None), "name", None)
    lines = [l10n("it_card_title", name=html.escape(item.name or "?")),
             l10n("it_card_section", section=html.escape(section_of(item))),
             l10n("it_card_price", price=item.price,
                  status=f"{STATUS_EMOJI.get(status, '❔')} {_status_label(l10n, status)}",
                  priority=l10n("it_premium") if priority == "PREMIUM" else l10n("it_free"))]
    until = format_until(getattr(item, "status_expiration_date", None), tz)
    if until and status == "APPROVED":
        lines.append(l10n("it_card_until", until=until))
    lines.append(l10n("it_card_stats", views=getattr(item, "views_counter", None) or 0,
                      deals=getattr(item, "deals_counter", None) or 0))
    reason = getattr(item, "status_description", None)
    if reason:
        lines.append(l10n("it_card_reason", reason=html.escape(reason.strip())))
    comment = (getattr(item, "comment", None) or "").strip()
    lines.append(l10n("it_card_comment", comment=html.escape(_short(comment, COMMENT_LIMIT)))
                 if comment else l10n("it_card_no_comment"))
    lines.append("━━━━━━━━━━━━━━━━━━━")
    keep = bool(getattr(item, "keep_in_sale", False))
    if status in ACTIVE_STATUS_NAMES:
        lines.append(l10n("it_card_keep", state=l10n("it_on") if keep else l10n("it_off")))
    lines.append(l10n("it_card_autodelivery", state=autodelivery))
    text = "\n".join(lines)
    if notice:
        text = notice + "\n\n" + text

    builder = InlineKeyboardBuilder()
    editable = getattr(item, "is_editable", True) is not False
    # Как на сайте: у заблокированного/отклонённого лота Playerok отдаёт keepInSaleAvailable=true,
    # но editable=false и переключатель не показывает (запрос получит 403).
    if editable and status in ACTIVE_STATUS_NAMES and getattr(item, "keep_in_sale_available", True) is not False:
        builder.row(InlineKeyboardButton(
            text=l10n("it_btn_keep", state="🟢" if keep else "🔴"), callback_data=f"it:k:{item.id}"))
    if editable:
        builder.row(InlineKeyboardButton(text=l10n("it_btn_comment"), callback_data=f"it:c:{item.id}"),
                    InlineKeyboardButton(text=l10n("it_btn_price"), callback_data=f"it:$:{item.id}"))
    actions = []
    if status == "APPROVED":
        actions.append(InlineKeyboardButton(text=l10n("it_btn_raise"), callback_data=f"it:up:{item.id}"))
    if getattr(item, "pause_available", False):
        actions.append(InlineKeyboardButton(text=l10n("it_btn_pause"), callback_data=f"it:off:{item.id}"))
    if getattr(item, "republish_available", False):
        actions.append(InlineKeyboardButton(text=l10n("it_btn_resume"), callback_data=f"it:on:{item.id}"))
    elif status == "EXPIRED":
        actions.append(InlineKeyboardButton(text=l10n("it_btn_publish"), callback_data=f"it:pub:{item.id}"))
    if actions:
        builder.row(*actions)
    if getattr(item, "slug", None):
        builder.row(InlineKeyboardButton(text=l10n("it_btn_site"), url=f"https://playerok.com/products/{item.slug}"))
    builder.row(*nav_row(l10n, back))
    return text, builder.as_markup()


def build_pay_confirm(l10n, item, action: str, options: list[tuple[str, int, str]]) -> tuple[str, object]:
    """Экран оплаты: `options` — [(id статуса, цена, тип)]; кнопка на каждый вариант."""
    key = "it_raise_confirm" if action == "raise" else "it_publish_confirm"
    text = l10n(key, name=html.escape(item.name or "?"))
    builder = InlineKeyboardBuilder()
    for index, (_, price, kind) in enumerate(options):
        label = l10n("it_premium") if kind == "PREMIUM" else l10n("it_free")
        builder.row(InlineKeyboardButton(
            text=l10n("it_btn_pay", label=label, price=price), callback_data=f"it:go:{index}"))
    if not options:
        text += "\n\n" + l10n("it_no_statuses")
    builder.row(InlineKeyboardButton(text=l10n("btn_cancel"), callback_data=f"it:v:{item.id}"))
    return text, builder.as_markup()


# ----------------------------------------------------------------------
# Помощники
# ----------------------------------------------------------------------

async def _offline(query: CallbackQuery, fixer) -> bool:
    if fixer.account is None:
        with suppress(Exception):
            await query.answer(fixer.l10n("it_offline"), show_alert=True)
        return True
    return False


def _autodelivery_state(fixer, item) -> str:
    l10n = fixer.l10n
    lot = fixer.autodelivery_config.lots.get(item.name or "")
    if lot is None:
        return l10n("it_off")
    manager = getattr(fixer, "autodelivery_manager", None)
    stock = manager.get_stock_size(item.name) if manager is not None else "?"
    return l10n("it_autodelivery_on", stock=stock)


def _back_for(item) -> str:
    """Куда ведёт «Назад» из карточки: в раздел лота или к снятым."""
    status = status_name(item)
    if status not in ("APPROVED", "PENDING_MODERATION", "PENDING_APPROVAL"):
        return "it:x:0"
    for index, (name, _) in enumerate(group_by_section(cache.peek())):
        if name == section_of(item):
            return f"it:s:{index}:0"
    return "it"


async def _load_item(fixer, item_id: str):
    return await asyncio.to_thread(fixer.account.get_item, id=item_id)


async def show_card(message, fixer, item_id: str, notice: str | None = None, state=None) -> None:
    """Карточка лота. С `state` — `message` это ваше сообщение: оно удаляется, а карточка
    показывается в сообщении бота, где шла правка."""
    item = await _load_item(fixer, item_id)
    if item is None:
        text, markup = fixer.l10n("it_not_found"), None
    else:
        text, markup = build_item_card(fixer.l10n, item, _autodelivery_state(fixer, item),
                                       seller_tz(fixer.settings), _back_for(item), notice)
    if state is not None:
        await show_in_panel(message, state, text, markup)
    else:
        await safe_edit(message, text, markup)


def _error_text(fixer, exc: Exception) -> str:
    code = getattr(exc, "error_code", None)
    if code == "FORBIDDEN" or getattr(exc, "status_code", None) == 403:
        return fixer.l10n("it_forbidden")
    return fixer.l10n("it_failed", error=str(exc)[:150])


async def _fail(query: CallbackQuery, fixer, exc: Exception) -> None:
    if isinstance(exc, RequestPlayerokError):  # отказ Playerok — одной строкой, без traceback
        logger.warning("[items] Playerok отказал: {}", exc)
    else:
        logger.opt(exception=exc).error("[items] Действие с лотом не выполнено: {}", exc)
    with suppress(Exception):
        await query.answer(_error_text(fixer, exc), show_alert=True)


# ----------------------------------------------------------------------
# Навигация
# ----------------------------------------------------------------------

@router.callback_query(F.data.regexp(r"^it(:p:\d+|:r)?$"))
async def cb_sections(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    if query.data == "it:r":
        cache.invalidate()
    page = int(query.data.rsplit(":", 1)[1]) if query.data.startswith("it:p:") else 0
    with suppress(Exception):
        await query.answer()
    try:
        items = await asyncio.to_thread(cache.get, fixer.account)
    except Exception as exc:
        logger.exception("[items] Не удалось загрузить лоты")
        await safe_edit(query.message, fixer.l10n("it_load_failed", error=html.escape(str(exc)[:200])),
                        build_sections(fixer.l10n, [], 0)[1])
        return
    await safe_edit(query.message, *build_sections(fixer.l10n, items, page))


@router.callback_query(F.data.regexp(r"^it:s:\d+:\d+$"))
async def cb_section(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    _, _, index, page = query.data.split(":")
    with suppress(Exception):
        await query.answer()
    items = await asyncio.to_thread(cache.get, fixer.account)
    view = build_section_items(fixer.l10n, items, int(index), int(page))
    if view is None:  # список изменился — к разделам
        view = build_sections(fixer.l10n, items, 0)
    await safe_edit(query.message, *view)


@router.callback_query(F.data.regexp(r"^it:x:\d+$"))
async def cb_inactive(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    with suppress(Exception):
        await query.answer()
    page = int(query.data.rsplit(":", 1)[1])
    try:
        items = await asyncio.to_thread(fetch_items, fixer.account, INACTIVE_STATUSES)
    except Exception as exc:
        logger.exception("[items] Не удалось загрузить снятые лоты")
        await safe_edit(query.message, fixer.l10n("it_load_failed", error=html.escape(str(exc)[:200])),
                        build_inactive(fixer.l10n, [], 0)[1])
        return
    await safe_edit(query.message, *build_inactive(fixer.l10n, items, page))


@router.callback_query(F.data.startswith("it:v:"))
async def cb_card(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if await _offline(query, fixer):
        return
    await state.clear()
    _pending.pop(query.from_user.id, None)
    with suppress(Exception):
        await query.answer()
    try:
        await show_card(query.message, fixer, query.data[5:])
    except Exception as exc:
        await _fail(query, fixer, exc)


# ----------------------------------------------------------------------
# Бесплатные действия
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("it:k:"))
async def cb_keep(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    item_id = query.data[5:]
    l10n = fixer.l10n
    try:
        item = await _load_item(fixer, item_id)
        current = getattr(item, "keep_in_sale", None)
        if current is None:
            # Playerok не прислал состояние — переключать вслепую нельзя.
            with suppress(Exception):
                await query.answer(l10n("it_keep_unknown"), show_alert=True)
            return
        result = await asyncio.to_thread(fixer.account.update_item, item_id, keep_in_sale=not current)
    except Exception as exc:
        await _fail(query, fixer, exc)
        return
    cache.invalidate()
    # Что на самом деле стало на Playerok — по ответу сервера, а не по нажатию.
    actual = getattr(result, "keep_in_sale", None)
    if actual is None:
        alert = l10n("it_keep_sent")
    else:
        alert = l10n("it_keep_on" if actual else "it_keep_off")
        if actual == current:
            alert = l10n("it_keep_not_changed")
    with suppress(Exception):
        await query.answer(alert, show_alert=actual is None or actual == current)
    await show_card(query.message, fixer, item_id)


@router.callback_query(F.data.startswith("it:off:") | F.data.startswith("it:on:"))
async def cb_pause_resume(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    action, item_id = query.data.split(":")[1], query.data.split(":", 2)[2]
    try:
        if action == "off":
            await asyncio.to_thread(fixer.account.discontinue_item, item_id)
        else:
            await asyncio.to_thread(fixer.account.republish_item, item_id)
    except Exception as exc:
        await _fail(query, fixer, exc)
        return
    cache.invalidate()
    with suppress(Exception):
        await query.answer(fixer.l10n("it_paused" if action == "off" else "it_resumed"))
    await show_card(query.message, fixer, item_id)


# ----------------------------------------------------------------------
# Платные действия: поднять / выставить заново (через экран с ценой)
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("it:up:") | F.data.startswith("it:pub:"))
async def cb_pay_prepare(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    action = "raise" if query.data.startswith("it:up:") else "publish"
    item_id = query.data.split(":", 2)[2]
    try:
        item = await _load_item(fixer, item_id)
        statuses = await asyncio.to_thread(fixer.account.get_item_priority_statuses, item_id, item.price)
    except Exception as exc:
        await _fail(query, fixer, exc)
        return
    options = []
    for status in statuses or []:
        kind = getattr(getattr(status, "type", None), "name", None)
        if action == "raise" and kind != "PREMIUM":
            continue  # поднять можно только премиумом
        options.append((status.id, int(getattr(status, "price", 0) or 0), kind or "?"))
    options.sort(key=lambda o: o[1], reverse=True)
    _pending[query.from_user.id] = {"action": action, "item_id": item_id, "options": options,
                                    "keep": getattr(item, "keep_in_sale", None), "name": item.name}
    with suppress(Exception):
        await query.answer()
    await safe_edit(query.message, *build_pay_confirm(fixer.l10n, item, action, options))


@router.callback_query(F.data.regexp(r"^it:go:\d+$"))
async def cb_pay_go(query: CallbackQuery, fixer) -> None:
    if await _offline(query, fixer):
        return
    pending = _pending.pop(query.from_user.id, None)
    index = int(query.data.rsplit(":", 1)[1])
    if not pending or not 0 <= index < len(pending["options"]):
        with suppress(Exception):
            await query.answer(fixer.l10n("it_pending_expired"), show_alert=True)
        return
    status_id, price, _ = pending["options"][index]
    account = fixer.account
    try:
        if pending["action"] == "raise":
            await asyncio.to_thread(account.increase_item_priority_status, pending["item_id"], status_id,
                                    keep_in_sale=pending["keep"])
        else:
            await asyncio.to_thread(account.publish_item, pending["item_id"], status_id,
                                    keep_in_sale=pending["keep"])
    except Exception as exc:
        await _fail(query, fixer, exc)
        return
    cache.invalidate()
    logger.info("[items] {} «{}» за {} ₽", "Поднят" if pending["action"] == "raise" else "Выставлен",
                pending["name"], price)
    notice = fixer.l10n("it_raised" if pending["action"] == "raise" else "it_published", price=price)
    with suppress(Exception):
        await query.answer()
    await show_card(query.message, fixer, pending["item_id"], notice=notice)


# ----------------------------------------------------------------------
# Правка комментария и цены
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("it:c:") | F.data.startswith("it:$:"))
async def cb_edit_start(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if await _offline(query, fixer):
        return
    field = "comment" if query.data.startswith("it:c:") else "price"
    item_id = query.data[5:]
    await state.set_state(ItemEdit.comment if field == "comment" else ItemEdit.price)
    await state.update_data(item_id=item_id, since=time.time())
    await remember_panel(state, query.message)
    with suppress(Exception):
        await query.answer()
    await safe_edit(query.message, *_edit_prompt(fixer.l10n, field, item_id))


def _edit_prompt(l10n, field: str, item_id: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("btn_cancel"), callback_data=f"it:v:{item_id}"))
    return l10n("it_enter_comment" if field == "comment" else "it_enter_price"), builder.as_markup()


@router.message(StateFilter(ItemEdit.comment, ItemEdit.price), F.text)
async def on_edit_value(message: Message, state: FSMContext, fixer) -> None:
    l10n = fixer.l10n
    data = await state.get_data()
    current = await state.get_state()
    # Reply на уведомление или давно забытое ожидание — не правка лота: отпускаем дальше.
    if message.reply_to_message is not None or time.time() - data.get("since", 0) > WAIT_SECONDS:
        await state.clear()
        raise SkipHandler()
    value = (message.text or "").strip()
    item_id = data.get("item_id")
    field = "price" if current == ItemEdit.price.state else "comment"

    async def fail(error: str) -> None:
        text, markup = _edit_prompt(l10n, field, item_id)
        await show_in_panel(message, state, with_error(error, text), markup)

    if fixer.account is None:
        await fail(l10n("it_offline"))
        return
    kwargs: dict = {}
    if field == "price":
        digits = value.replace(" ", "").replace("₽", "")
        if not digits.isdigit() or int(digits) <= 0:
            await fail(l10n("it_bad_price"))
            return
        kwargs["price"] = int(digits)
        notice = l10n("it_price_saved", price=int(digits))
    else:
        if not value or value.startswith("/"):
            await fail(l10n("it_bad_comment"))
            return
        kwargs["comment"] = value
        notice = l10n("it_comment_saved")
    try:
        await asyncio.to_thread(fixer.account.update_item, item_id, **kwargs)
    except Exception as exc:
        logger.exception("[items] Не удалось изменить лот {}", item_id)
        await fail(l10n("it_failed", error=html.escape(str(exc)[:200])))
        return
    cache.invalidate()
    await show_card(message, fixer, item_id, notice=notice, state=state)
    await state.clear()
