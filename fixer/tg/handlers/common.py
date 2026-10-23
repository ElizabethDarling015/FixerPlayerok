"""Общие помощники хендлеров TG-панели."""
from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from loguru import logger
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    """`edit_text`, не падающий на «message is not modified» (повторное нажатие кнопки)."""
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=reply_markup)


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


# ----------------------------------------------------------------------
# Диалог в одном сообщении: ваш ввод удаляется, ответ — в сообщении бота
# ----------------------------------------------------------------------

async def remember_panel(state, message: Message) -> None:
    """Запоминает сообщение бота, в котором идёт диалог (в FSM-данных, ключ ``panel``)."""
    await state.update_data(panel=[message.chat.id, message.message_id])


async def show_in_panel(message: Message, state, text: str, reply_markup=None) -> None:
    """Удаляет ваше сообщение и показывает `text` в запомненном сообщении бота.

    Если сообщение бота неизвестно или его уже нельзя изменить — присылает новое и
    запоминает его, чтобы дальше работать в нём."""
    with suppress(Exception):
        await message.delete()
    panel = (await state.get_data()).get("panel")
    if panel:
        try:
            await message.bot.edit_message_text(text, chat_id=panel[0], message_id=panel[1],
                                                reply_markup=reply_markup)
            return
        except TelegramBadRequest as exc:
            if "not modified" in str(exc):
                return
            logger.debug("Сообщение диалога не изменить ({}) — шлю новое", exc)
        except Exception as exc:
            logger.debug("Сообщение диалога не изменить ({}) — шлю новое", exc)
    sent = await message.answer(text, reply_markup=reply_markup)
    await remember_panel(state, sent)


def with_error(error: str, text: str) -> str:
    """Ошибка строкой над экраном: «⚠️ …»."""
    return f"⚠️ {error}\n\n{text}"
