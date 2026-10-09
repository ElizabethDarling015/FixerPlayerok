"""
Раздел «Авто-выдача»: список лотов и остатков, добавление/удаление лотов,
пополнение складов (текстом или .txt-файлом), флаги восстановления/деактивации.

Лоты в callback-данных адресуются индексом в отсортированном списке (название лота
может быть длиннее лимита callback_data в 64 байта).
"""
from __future__ import annotations

import html
import os
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playerokapi.autodelivery import parse_stock_text

from ...settings import AutoDeliveryLot, save_autodelivery_config
from .common import PAGE_SIZE, cancel_markup, nav_row, on_off, pager_row, paginate, safe_edit

router = Router(name="autodelivery")


class AddLot(StatesGroup):
    name = State()
    stock_file = State()


class AddStock(StatesGroup):
    items = State()


def _lot_names(fixer) -> list[str]:
    return sorted(fixer.autodelivery_config.lots)


def _lot_by_index(fixer, index: int) -> tuple[str, AutoDeliveryLot] | None:
    names = _lot_names(fixer)
    if 0 <= index < len(names):
        name = names[index]
        return name, fixer.autodelivery_config.lots[name]
    return None


def _save_and_apply(fixer) -> None:
    save_autodelivery_config(fixer.autodelivery_config)
    fixer.apply_autodelivery_config()


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "_", name, flags=re.UNICODE).strip("_")
    return cleaned or "lot"


def build_lots_list(fixer, page: int = 0) -> tuple[str, object]:
    l10n = fixer.l10n
    manager = fixer.autodelivery_manager
    names = _lot_names(fixer)
    page_names, page, total_pages, start = paginate(names, page)

    if page_names:
        lines = [l10n("ad_lot_line", name=html.escape(name),
                      stock=manager.get_stock_size(name) if manager else "?")
                 for name in page_names]
        text = l10n("ad_title") + "\n" + "\n".join(lines)
    else:
        text = l10n("ad_title") + "\n" + l10n("ad_no_lots")

    builder = InlineKeyboardBuilder()
    for offset, name in enumerate(page_names):
        builder.button(text=name[:40], callback_data=f"ad:lot:{start + offset}")
    builder.adjust(1)
    if pager := pager_row("ad:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("ad_btn_add_lot"), callback_data="ad:addlot"))
    builder.row(*nav_row(l10n, "sys"))
    return text, builder.as_markup()


def build_lot_view(fixer, index: int) -> tuple[str, object] | None:
    found = _lot_by_index(fixer, index)
    if found is None:
        return None
    name, lot = found
    l10n = fixer.l10n
    manager = fixer.autodelivery_manager
    text = l10n(
        "ad_lot_title",
        name=html.escape(name),
        stock_file=html.escape(lot.stock_file),
        stock=manager.get_stock_size(name) if manager else "?",
        restore=on_off(l10n, lot.restore),
        deactivate=on_off(l10n, lot.deactivate_when_empty),
    )
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("ad_btn_view_stock"), callback_data=f"ad:view:{index}")
    builder.button(text=l10n("ad_btn_add_stock"), callback_data=f"ad:stock:{index}")
    builder.button(text=l10n("ad_btn_toggle_restore", state=on_off(l10n, lot.restore)),
                   callback_data=f"ad:restore:{index}")
    builder.button(text=l10n("ad_btn_toggle_deactivate", state=on_off(l10n, lot.deactivate_when_empty)),
                   callback_data=f"ad:deact:{index}")
    builder.button(text=l10n("ad_btn_delete_lot"), callback_data=f"ad:del:{index}")
    builder.adjust(1)
    # «Назад» ведёт на страницу списка, где находится этот лот.
    builder.row(*nav_row(l10n, f"ad:p:{index // PAGE_SIZE}"))
    return text, builder.as_markup()


def build_stock_view(fixer, index: int, limit: int = PAGE_SIZE) -> tuple[str, object] | None:
    """Первые `limit` позиций склада лота (многострочные позиции показываются целиком)."""
    found = _lot_by_index(fixer, index)
    if found is None:
        return None
    name, lot = found
    l10n = fixer.l10n

    items: list[str] = []
    try:
        with open(lot.stock_file, "r", encoding="utf-8") as f:
            items = parse_stock_text(f.read())
    except OSError:
        pass

    if items:
        shown = items[:limit]
        lines = [f"{pos}. <code>{html.escape(item)}</code>" for pos, item in enumerate(shown, 1)]
        body = "\n".join(lines)
        if len(items) > limit:
            body += "\n" + l10n("ad_stock_more", count=len(items) - limit)
    else:
        body = l10n("ad_stock_view_empty")

    text = l10n("ad_stock_view_title", name=html.escape(name), total=len(items)) + "\n" + body
    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n, f"ad:lot:{index}"))
    return text, builder.as_markup()


# ----------------------------------------------------------------------
# Просмотр
# ----------------------------------------------------------------------

@router.callback_query(F.data == "ad")
async def cb_list(query: CallbackQuery, fixer) -> None:
    text, markup = build_lots_list(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ad:p:"))
async def cb_list_page(query: CallbackQuery, fixer) -> None:
    text, markup = build_lots_list(fixer, page=int(query.data.rsplit(":", 1)[1]))
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ad:lot:"))
async def cb_lot(query: CallbackQuery, fixer) -> None:
    view = build_lot_view(fixer, int(query.data.rsplit(":", 1)[1]))
    if view is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()


@router.callback_query(F.data.startswith("ad:view:"))
async def cb_view_stock(query: CallbackQuery, fixer) -> None:
    view = build_stock_view(fixer, int(query.data.rsplit(":", 1)[1]))
    if view is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()


# ----------------------------------------------------------------------
# Флаги и удаление
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("ad:restore:"))
async def cb_toggle_restore(query: CallbackQuery, fixer) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(fixer, index)
    if found is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    _, lot = found
    lot.restore = not lot.restore
    _save_and_apply(fixer)
    await safe_edit(query.message, *build_lot_view(fixer, index))
    await query.answer()


@router.callback_query(F.data.startswith("ad:deact:"))
async def cb_toggle_deactivate(query: CallbackQuery, fixer) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(fixer, index)
    if found is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    _, lot = found
    lot.deactivate_when_empty = not lot.deactivate_when_empty
    _save_and_apply(fixer)
    await safe_edit(query.message, *build_lot_view(fixer, index))
    await query.answer()


@router.callback_query(F.data.startswith("ad:del:"))
async def cb_delete_lot(query: CallbackQuery, fixer) -> None:
    found = _lot_by_index(fixer, int(query.data.rsplit(":", 1)[1]))
    if found is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    name, _ = found
    del fixer.autodelivery_config.lots[name]
    _save_and_apply(fixer)
    await query.answer(fixer.l10n("ad_lot_deleted", name=name))
    text, markup = build_lots_list(fixer)
    await safe_edit(query.message, text, markup)


# ----------------------------------------------------------------------
# Добавление лота (FSM)
# ----------------------------------------------------------------------

@router.callback_query(F.data == "ad:addlot")
async def cb_add_lot(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.set_state(AddLot.name)
    await safe_edit(query.message, fixer.l10n("ad_enter_lot_name"), cancel_markup(fixer.l10n))
    await query.answer()


@router.message(AddLot.name, F.text)
async def msg_lot_name(message: Message, state: FSMContext, fixer) -> None:
    await state.update_data(lot_name=message.text.strip())
    await state.set_state(AddLot.stock_file)
    await message.answer(fixer.l10n("ad_enter_stock_file"), reply_markup=cancel_markup(fixer.l10n))


@router.message(AddLot.stock_file, F.text)
async def msg_lot_stock_file(message: Message, state: FSMContext, fixer) -> None:
    data = await state.get_data()
    await state.clear()
    lot_name = data["lot_name"]

    stock_file = message.text.strip()
    if stock_file == "-":
        stock_file = os.path.join("storage", "stock", f"{_sanitize_filename(lot_name)}.txt")

    os.makedirs(os.path.dirname(os.path.abspath(stock_file)), exist_ok=True)
    if not os.path.isfile(stock_file):
        open(stock_file, "w", encoding="utf-8").close()

    fixer.autodelivery_config.lots[lot_name] = AutoDeliveryLot(stock_file=stock_file)
    _save_and_apply(fixer)

    await message.answer(fixer.l10n("ad_lot_added", name=html.escape(lot_name),
                                       stock_file=html.escape(stock_file)))
    text, markup = build_lots_list(fixer)
    await message.answer(text, reply_markup=markup)


# ----------------------------------------------------------------------
# Пополнение склада (FSM: текст или .txt-файл)
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("ad:stock:"))
async def cb_add_stock(query: CallbackQuery, state: FSMContext, fixer) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(fixer, index)
    if found is None:
        await query.answer(fixer.l10n("ad_lot_missing"), show_alert=True)
        return
    await state.set_state(AddStock.items)
    await state.update_data(lot_name=found[0])
    await safe_edit(query.message, fixer.l10n("ad_send_stock_items"), cancel_markup(fixer.l10n))
    await query.answer()


async def _finish_add_stock(message: Message, state: FSMContext, fixer, text: str) -> None:
    data = await state.get_data()
    await state.clear()
    lot_name = data.get("lot_name", "")
    manager = fixer.autodelivery_manager
    if lot_name not in fixer.autodelivery_config.lots or manager is None:
        await message.answer(fixer.l10n("ad_lot_missing"))
        return
    count = manager.add_stock(lot_name, text)
    await message.answer(fixer.l10n("ad_stock_added", count=count,
                                       stock=manager.get_stock_size(lot_name)))


@router.message(AddStock.items, F.document)
async def msg_stock_document(message: Message, state: FSMContext, fixer) -> None:
    file = await message.bot.download(message.document)
    content = file.read().decode("utf-8", errors="replace")
    await _finish_add_stock(message, state, fixer, content)


@router.message(AddStock.items, F.text)
async def msg_stock_text(message: Message, state: FSMContext, fixer) -> None:
    await _finish_add_stock(message, state, fixer, message.text)
