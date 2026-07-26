"""
Раздел «Авто-выдача»: список лотов и остатков, добавление/удаление лотов (вручную или
выбором из своих лотов на Playerok), пополнение складов (текстом или .txt-файлом),
пер-лотовый текст выдачи, тест выдачи без покупки, флаги восстановления/деактивации.

Лоты в callback-данных адресуются индексом в отсортированном списке (название лота
может быть длиннее лимита callback_data в 64 байта).
"""
from __future__ import annotations

import asyncio
import html
import os
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playerokapi.autodelivery import parse_stock_text
from playerokapi.common.enums import ItemStatuses

from ...settings import AutoDeliveryLot, save_autodelivery_config, save_main_settings
from .common import PAGE_SIZE, cancel_markup, nav_row, on_off, pager_row, paginate, safe_edit

router = Router(name="autodelivery")

#: Названия лотов с Playerok, загруженные для экрана выбора: `{tg_user_id: [название, …]}`.
#: Кэш нужен, чтобы листание страниц и сам выбор не дёргали площадку заново, а короткие
#: callback-данные могли адресовать лот индексом.
_playerok_items_cache: dict[int, list[str]] = {}


class AddLot(StatesGroup):
    name = State()
    stock_file = State()


class AddStock(StatesGroup):
    items = State()


class EditDeliveryText(StatesGroup):
    text = State()


class EditLotDeliveryText(StatesGroup):
    text = State()


def _lot_names(cardinal) -> list[str]:
    return sorted(cardinal.autodelivery_config.lots)


def _lot_by_index(cardinal, index: int) -> tuple[str, AutoDeliveryLot] | None:
    names = _lot_names(cardinal)
    if 0 <= index < len(names):
        name = names[index]
        return name, cardinal.autodelivery_config.lots[name]
    return None


def _save_and_apply(cardinal) -> None:
    save_autodelivery_config(cardinal.autodelivery_config)
    cardinal.apply_autodelivery_config()


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "_", name, flags=re.UNICODE).strip("_")
    return cleaned or "lot"


def create_lot(cardinal, lot_name: str, stock_file: str | None = None) -> str:
    """
    Создаёт лот авто-выдачи в конфиге и заводит для него файл-склад.

    :param lot_name: Точное название лота (как на Playerok).
    :param stock_file: Путь к складу; `None` — сгенерировать `storage/stock/<имя>.txt`.
    :return: Итоговый путь к файлу-складу.
    """
    if not stock_file:
        stock_file = os.path.join("storage", "stock", f"{_sanitize_filename(lot_name)}.txt")
    os.makedirs(os.path.dirname(os.path.abspath(stock_file)), exist_ok=True)
    if not os.path.isfile(stock_file):
        open(stock_file, "w", encoding="utf-8").close()
    cardinal.autodelivery_config.lots[lot_name] = AutoDeliveryLot(stock_file=stock_file)
    _save_and_apply(cardinal)
    return stock_file


def simulate_delivery(manager, item_name: str) -> tuple[str, int] | None:
    """
    Прогоняет настоящий конвейер выдачи «вхолостую»: забирает позицию со склада, форматирует
    текст для покупателя и **возвращает позицию обратно** (журнал выдач не трогается,
    покупателю ничего не отправляется).

    :param manager: `AutoDeliveryManager` Cardinal'а.
    :param item_name: Название лота.
    :return: `(текст, который получил бы покупатель, остаток склада после выдачи)`, либо `None`,
        если выдавать нечего (склад пуст/не настроен или модуль авто-выдачи выключен).
    """
    item_value = manager.reserve(item_name)
    if item_value is None:
        return None
    try:
        text = manager.format_delivery_text(item_value, item_name)
        stock_left = manager.get_stock_size(item_name)
        return text, stock_left
    finally:
        # Товар возвращаем в любом случае — тест не должен «съедать» позицию со склада.
        manager.restore(item_name, item_value)


async def fetch_my_item_names(cardinal, max_pages: int = 5, page_size: int = 50) -> list[str]:
    """
    Забирает названия своих активных лотов с Playerok (постранично, курсором), без повторов.

    Синхронный `Account` вызывается через `asyncio.to_thread` — как везде в Cardinal.
    """
    names: list[str] = []
    seen: set[str] = set()
    after_cursor: str | None = None
    for _ in range(max_pages):
        page = await asyncio.to_thread(cardinal.account.get_my_items,
                                       status=ItemStatuses.APPROVED, count=page_size,
                                       after_cursor=after_cursor)
        if not page or not page.items:
            break
        for item in page.items:
            name = getattr(item, "name", None)
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        page_info = getattr(page, "page_info", None)
        if not page_info or not page_info.has_next_page:
            break
        next_cursor = page_info.end_cursor
        if not next_cursor or next_cursor == after_cursor:
            break  # защита от зацикливания на неподвижном курсоре
        after_cursor = next_cursor
    return names


def build_pick_list(cardinal, names: list[str], page: int = 0) -> tuple[str, object]:
    """Экран выбора лота с Playerok: кнопка на каждый лот (уже настроенные помечены ✅)."""
    l10n = cardinal.l10n
    page_names, page, total_pages, start = paginate(names, page)

    text = l10n("ad_pick_title") if names else l10n("ad_pick_empty")
    builder = InlineKeyboardBuilder()
    for offset, name in enumerate(page_names):
        mark = "✅ " if name in cardinal.autodelivery_config.lots else ""
        builder.button(text=f"{mark}{name}"[:40], callback_data=f"ad:pickadd:{start + offset}")
    builder.adjust(1)
    if pager := pager_row("ad:pickp", page, total_pages):
        builder.row(*pager)
    builder.row(*nav_row(l10n, "ad"))
    return text, builder.as_markup()


def build_lots_list(cardinal, page: int = 0) -> tuple[str, object]:
    l10n = cardinal.l10n
    manager = cardinal.autodelivery_manager
    names = _lot_names(cardinal)
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
    builder.row(InlineKeyboardButton(text=l10n("ad_btn_pick_lot"), callback_data="ad:pick"))
    builder.row(InlineKeyboardButton(text=l10n("ad_btn_add_lot"), callback_data="ad:addlot"))
    builder.row(InlineKeyboardButton(text=l10n("ad_btn_delivery_text"), callback_data="ad:text"))
    builder.row(InlineKeyboardButton(
        text=l10n("ad_btn_toggle_auto_deact",
                  state=on_off(l10n, cardinal.settings.autodelivery.deactivate_on_empty)),
        callback_data="ad:autodeact"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


def build_lot_view(cardinal, index: int) -> tuple[str, object] | None:
    found = _lot_by_index(cardinal, index)
    if found is None:
        return None
    name, lot = found
    l10n = cardinal.l10n
    manager = cardinal.autodelivery_manager
    text = l10n(
        "ad_lot_title",
        name=html.escape(name),
        stock_file=html.escape(lot.stock_file),
        stock=manager.get_stock_size(name) if manager else "?",
        restore=on_off(l10n, lot.restore),
        deactivate=on_off(l10n, lot.deactivate_when_empty),
        own_text=on_off(l10n, bool(lot.delivery_text)),
        auto_deact=on_off(l10n, not lot.disable_deactivate),
    )
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("ad_btn_view_stock"), callback_data=f"ad:view:{index}")
    builder.button(text=l10n("ad_btn_add_stock"), callback_data=f"ad:stock:{index}")
    builder.button(text=l10n("ad_btn_test"), callback_data=f"ad:test:{index}")
    builder.button(text=l10n("ad_btn_lot_delivery_text"), callback_data=f"ad:ltext:{index}")
    builder.button(text=l10n("ad_btn_toggle_restore", state=on_off(l10n, lot.restore)),
                   callback_data=f"ad:restore:{index}")
    builder.button(text=l10n("ad_btn_toggle_deactivate", state=on_off(l10n, lot.deactivate_when_empty)),
                   callback_data=f"ad:deact:{index}")
    builder.button(text=l10n("ad_btn_toggle_lot_deact", state=on_off(l10n, not lot.disable_deactivate)),
                   callback_data=f"ad:nodeact:{index}")
    builder.button(text=l10n("ad_btn_delete_lot"), callback_data=f"ad:del:{index}")
    builder.adjust(1)
    # «Назад» ведёт на страницу списка, где находится этот лот.
    builder.row(*nav_row(l10n, f"ad:p:{index // PAGE_SIZE}"))
    return text, builder.as_markup()


def build_stock_view(cardinal, index: int, limit: int = PAGE_SIZE) -> tuple[str, object] | None:
    """Первые `limit` позиций склада лота (многострочные позиции показываются целиком)."""
    found = _lot_by_index(cardinal, index)
    if found is None:
        return None
    name, lot = found
    l10n = cardinal.l10n

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
async def cb_list(query: CallbackQuery, cardinal) -> None:
    text, markup = build_lots_list(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ad:p:"))
async def cb_list_page(query: CallbackQuery, cardinal) -> None:
    text, markup = build_lots_list(cardinal, page=int(query.data.rsplit(":", 1)[1]))
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ad:lot:"))
async def cb_lot(query: CallbackQuery, cardinal) -> None:
    view = build_lot_view(cardinal, int(query.data.rsplit(":", 1)[1]))
    if view is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()


@router.callback_query(F.data.startswith("ad:view:"))
async def cb_view_stock(query: CallbackQuery, cardinal) -> None:
    view = build_stock_view(cardinal, int(query.data.rsplit(":", 1)[1]))
    if view is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()


# ----------------------------------------------------------------------
# Флаги и удаление
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("ad:restore:"))
async def cb_toggle_restore(query: CallbackQuery, cardinal) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    _, lot = found
    lot.restore = not lot.restore
    _save_and_apply(cardinal)
    await safe_edit(query.message, *build_lot_view(cardinal, index))
    await query.answer()


@router.callback_query(F.data.startswith("ad:deact:"))
async def cb_toggle_deactivate(query: CallbackQuery, cardinal) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    _, lot = found
    lot.deactivate_when_empty = not lot.deactivate_when_empty
    _save_and_apply(cardinal)
    await safe_edit(query.message, *build_lot_view(cardinal, index))
    await query.answer()


@router.callback_query(F.data.startswith("ad:nodeact:"))
async def cb_toggle_lot_deactivate(query: CallbackQuery, cardinal) -> None:
    """Переключает автоснятие ЭТОГО лота с публикации при пустом складе (`disable_deactivate`)."""
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    _, lot = found
    lot.disable_deactivate = not lot.disable_deactivate
    _save_and_apply(cardinal)
    await safe_edit(query.message, *build_lot_view(cardinal, index))
    await query.answer()


@router.callback_query(F.data == "ad:autodeact")
async def cb_toggle_auto_deactivate(query: CallbackQuery, cardinal) -> None:
    """Переключает общую настройку `[autodelivery] deactivate_on_empty`."""
    settings = cardinal.settings.autodelivery
    settings.deactivate_on_empty = not settings.deactivate_on_empty
    save_main_settings(cardinal.settings)
    text, markup = build_lots_list(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ad:del:"))
async def cb_delete_lot_confirm(query: CallbackQuery, cardinal) -> None:
    """Первый шаг удаления: экран подтверждения (удаление лота необратимо для конфига)."""
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(l10n("ad_lot_missing"), show_alert=True)
        return
    name, _ = found
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("ad_btn_delete_yes"), callback_data=f"ad:delyes:{index}"))
    builder.row(*nav_row(l10n, f"ad:lot:{index}"))
    await safe_edit(query.message, l10n("ad_delete_confirm", name=html.escape(name)), builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ad:delyes:"))
async def cb_delete_lot(query: CallbackQuery, cardinal) -> None:
    found = _lot_by_index(cardinal, int(query.data.rsplit(":", 1)[1]))
    if found is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    name, _ = found
    del cardinal.autodelivery_config.lots[name]
    _save_and_apply(cardinal)
    await query.answer(cardinal.l10n("ad_lot_deleted", name=name))
    text, markup = build_lots_list(cardinal)
    await safe_edit(query.message, text, markup)


# ----------------------------------------------------------------------
# Добавление лота (FSM)
# ----------------------------------------------------------------------

@router.callback_query(F.data == "ad:addlot")
async def cb_add_lot(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    await state.set_state(AddLot.name)
    await safe_edit(query.message, cardinal.l10n("ad_enter_lot_name"), cancel_markup(cardinal.l10n))
    await query.answer()


@router.message(AddLot.name, F.text)
async def msg_lot_name(message: Message, state: FSMContext, cardinal) -> None:
    await state.update_data(lot_name=message.text.strip())
    await state.set_state(AddLot.stock_file)
    await message.answer(cardinal.l10n("ad_enter_stock_file"), reply_markup=cancel_markup(cardinal.l10n))


@router.message(AddLot.stock_file, F.text)
async def msg_lot_stock_file(message: Message, state: FSMContext, cardinal) -> None:
    data = await state.get_data()
    await state.clear()
    lot_name = data["lot_name"]

    stock_file = message.text.strip()
    stock_file = create_lot(cardinal, lot_name, None if stock_file == "-" else stock_file)

    await message.answer(cardinal.l10n("ad_lot_added", name=html.escape(lot_name),
                                       stock_file=html.escape(stock_file)))
    text, markup = build_lots_list(cardinal)
    await message.answer(text, reply_markup=markup)


# ----------------------------------------------------------------------
# Выбор лота из списка своих лотов на Playerok
# ----------------------------------------------------------------------

@router.callback_query(F.data == "ad:pick")
async def cb_pick_lot(query: CallbackQuery, cardinal) -> None:
    """Загружает свои лоты с Playerok и показывает их кнопками (ручной ввод остаётся запасным путём)."""
    l10n = cardinal.l10n
    await query.answer(l10n("ad_pick_loading"))
    try:
        names = await fetch_my_item_names(cardinal)
    except Exception as exc:  # noqa: BLE001 — сеть/сессия: показываем причину, а не падаем
        builder = InlineKeyboardBuilder()
        builder.row(*nav_row(l10n, "ad"))
        await safe_edit(query.message, l10n("ad_pick_failed", error=html.escape(str(exc))),
                        builder.as_markup())
        return
    _playerok_items_cache[query.from_user.id] = names
    await safe_edit(query.message, *build_pick_list(cardinal, names))


@router.callback_query(F.data.startswith("ad:pickp:"))
async def cb_pick_lot_page(query: CallbackQuery, cardinal) -> None:
    names = _playerok_items_cache.get(query.from_user.id, [])
    page = int(query.data.rsplit(":", 1)[1])
    await safe_edit(query.message, *build_pick_list(cardinal, names, page))
    await query.answer()


@router.callback_query(F.data.startswith("ad:pickadd:"))
async def cb_pick_lot_add(query: CallbackQuery, cardinal) -> None:
    """Создаёт лот авто-выдачи с точным названием выбранного лота Playerok."""
    l10n = cardinal.l10n
    names = _playerok_items_cache.get(query.from_user.id, [])
    index = int(query.data.rsplit(":", 1)[1])
    if not 0 <= index < len(names):
        await query.answer(l10n("ad_lot_missing"), show_alert=True)
        return
    lot_name = names[index]
    if lot_name in cardinal.autodelivery_config.lots:
        await query.answer(l10n("ad_pick_already", name=lot_name), show_alert=True)
        return
    stock_file = create_lot(cardinal, lot_name)
    await query.answer(l10n("ad_pick_added", name=lot_name))
    await query.message.answer(l10n("ad_lot_added", name=html.escape(lot_name),
                                    stock_file=html.escape(stock_file)))
    await safe_edit(query.message, *build_pick_list(cardinal, names, index // PAGE_SIZE))


# ----------------------------------------------------------------------
# Тест выдачи (без покупки и без сообщения покупателю)
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("ad:test:"))
async def cb_test_delivery(query: CallbackQuery, cardinal) -> None:
    """
    Прогоняет выдачу лота вхолостую: показывает админу, что получил бы покупатель, и
    возвращает товар на склад (покупателю ничего не отправляется, журнал выдач не трогается).
    """
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    manager = cardinal.autodelivery_manager
    if found is None or manager is None:
        await query.answer(l10n("ad_lot_missing"), show_alert=True)
        return
    name, _ = found

    result = await asyncio.to_thread(simulate_delivery, manager, name)
    if result is None:
        await query.answer(l10n("ad_test_empty", name=name), show_alert=True)
        return
    delivery_text, stock_left = result
    await query.answer()
    await query.message.answer(l10n("ad_test_result", name=html.escape(name),
                                    text=html.escape(delivery_text), stock=stock_left))


# ----------------------------------------------------------------------
# Текст выдачи (FSM)
# ----------------------------------------------------------------------

@router.callback_query(F.data == "ad:text")
async def cb_edit_delivery_text(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    await state.set_state(EditDeliveryText.text)
    await safe_edit(query.message,
                    l10n("ad_enter_delivery_text",
                         current=html.escape(cardinal.settings.autodelivery.delivery_text)),
                    cancel_markup(l10n))
    await query.answer()


@router.message(EditDeliveryText.text, F.text)
async def msg_delivery_text(message: Message, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    if "{item}" not in message.text:
        # Без плейсхолдера покупатель не получит сам товар — не даём сохранить.
        await message.answer(l10n("ad_text_needs_item"), reply_markup=cancel_markup(l10n))
        return
    await state.clear()
    cardinal.settings.autodelivery.delivery_text = message.text
    save_main_settings(cardinal.settings)
    if cardinal.autodelivery_manager is not None:
        cardinal.autodelivery_manager.delivery_text_template = message.text
    await message.answer(l10n("ad_delivery_text_saved"))
    text, markup = build_lots_list(cardinal)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("ad:ltext:"))
async def cb_edit_lot_delivery_text(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    """Свой текст выдачи для конкретного лота (перекрывает общий `[autodelivery] delivery_text`)."""
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(l10n("ad_lot_missing"), show_alert=True)
        return
    name, lot = found
    await state.set_state(EditLotDeliveryText.text)
    await state.update_data(lot_name=name)
    current = lot.delivery_text or cardinal.settings.autodelivery.delivery_text
    await safe_edit(query.message,
                    l10n("ad_enter_lot_delivery_text", name=html.escape(name),
                         current=html.escape(current)),
                    cancel_markup(l10n))
    await query.answer()


@router.message(EditLotDeliveryText.text, F.text)
async def msg_lot_delivery_text(message: Message, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    new_text = message.text.strip()
    if new_text != "-" and "{item}" not in message.text:
        # Без плейсхолдера покупатель не получит сам товар — не даём сохранить.
        await message.answer(l10n("ad_text_needs_item"), reply_markup=cancel_markup(l10n))
        return
    data = await state.get_data()
    await state.clear()
    lot_name = data.get("lot_name", "")
    lot = cardinal.autodelivery_config.lots.get(lot_name)
    if lot is None:
        await message.answer(l10n("ad_lot_missing"))
        return

    if new_text == "-":
        lot.delivery_text = None
        answer = l10n("ad_lot_delivery_text_reset", name=html.escape(lot_name))
    else:
        lot.delivery_text = message.text
        answer = l10n("ad_lot_delivery_text_saved", name=html.escape(lot_name))
    _save_and_apply(cardinal)

    await message.answer(answer)
    text, markup = build_lots_list(cardinal)
    await message.answer(text, reply_markup=markup)


# ----------------------------------------------------------------------
# Пополнение склада (FSM: текст или .txt-файл)
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("ad:stock:"))
async def cb_add_stock(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    index = int(query.data.rsplit(":", 1)[1])
    found = _lot_by_index(cardinal, index)
    if found is None:
        await query.answer(cardinal.l10n("ad_lot_missing"), show_alert=True)
        return
    await state.set_state(AddStock.items)
    await state.update_data(lot_name=found[0])
    await safe_edit(query.message, cardinal.l10n("ad_send_stock_items"), cancel_markup(cardinal.l10n))
    await query.answer()


async def _finish_add_stock(message: Message, state: FSMContext, cardinal, text: str) -> None:
    data = await state.get_data()
    await state.clear()
    lot_name = data.get("lot_name", "")
    manager = cardinal.autodelivery_manager
    if lot_name not in cardinal.autodelivery_config.lots or manager is None:
        await message.answer(cardinal.l10n("ad_lot_missing"))
        return
    count = manager.add_stock(lot_name, text)
    await message.answer(cardinal.l10n("ad_stock_added", count=count,
                                       stock=manager.get_stock_size(lot_name)))


@router.message(AddStock.items, F.document)
async def msg_stock_document(message: Message, state: FSMContext, cardinal) -> None:
    file = await message.bot.download(message.document)
    content = file.read().decode("utf-8", errors="replace")
    await _finish_add_stock(message, state, cardinal, content)


@router.message(AddStock.items, F.text)
async def msg_stock_text(message: Message, state: FSMContext, cardinal) -> None:
    await _finish_add_stock(message, state, cardinal, message.text)
