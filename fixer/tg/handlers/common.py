"""Общие помощники хендлеров TG-панели."""
from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    """`edit_text`, не падающий на «message is not modified» (повторное нажатие кнопки)."""
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=reply_markup)


def back_button(l10n, callback_data: str = "menu") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=l10n("btn_back"), callback_data=callback_data)


def nav_row(l10n, back_cb: str | None = None) -> list[InlineKeyboardButton]:
    """
    Нижний ряд навигации экрана.

    Для вложенных экранов (указан `back_cb`) — две кнопки: «Назад» (на уровень выше)
    и «Главное меню». Для разделов первого уровня (`back_cb` не указан или "menu") —
    одна кнопка «Главное меню».
    """
    if back_cb and back_cb != "menu":
        return [InlineKeyboardButton(text=l10n("btn_back"), callback_data=back_cb),
                InlineKeyboardButton(text=l10n("btn_home"), callback_data="menu")]
    return [InlineKeyboardButton(text=l10n("btn_home"), callback_data="menu")]


#: Размер страницы списков в панели (лоты, команды, ЧС, плагины).
PAGE_SIZE = 10


def paginate(items: list, page: int, page_size: int = PAGE_SIZE) -> tuple[list, int, int, int]:
    """
    Возвращает срез списка для страницы `page` (нумерация с 0, значение зажимается
    в допустимые границы): `(элементы_страницы, страница, всего_страниц, индекс_первого)`.
    """
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start:start + page_size], page, total_pages, start


def pager_row(prefix: str, page: int, total_pages: int) -> list[InlineKeyboardButton]:
    """
    Ряд пагинации `[◀️] [2/5] [▶️]` (пустой список, если страница одна).

    `prefix` — префикс callback-данных: страница N кодируется как `{prefix}:{N}`.
    Кнопка-индикатор по центру никуда не ведёт (callback "noop").
    """
    if total_pages <= 1:
        return []
    return [
        InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{max(0, page - 1)}"),
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{min(total_pages - 1, page + 1)}"),
    ]


def cancel_markup(l10n):
    """Клавиатура с одной кнопкой «Отмена» для FSM-диалогов."""
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_cancel"), callback_data="fsm:cancel")
    return builder.as_markup()


def on_off(l10n, value: bool) -> str:
    return "🟢" if value else "🔴"
