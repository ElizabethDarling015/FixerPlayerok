"""Раздел «Автоответчик»: список команд, просмотр/удаление, добавление через FSM-диалог.

Команды — личная библиотека шаблонов продавца: в живом диалоге продавец пишет
``!!команда`` и покупатель получает шаблонный текст (см. chats.py).
"""

from __future__ import annotations

import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import save_autoresponse_config
from .common import PAGE_SIZE, nav_row, pager_row, paginate, safe_edit

router = Router(name="autoresponse")


class AddCommand(StatesGroup):
    command = State()
    response = State()


class EditResponse(StatesGroup):
    response = State()


def _commands(cardinal) -> list[str]:
    return sorted(cardinal.autoresponse_config.commands)


def build_commands_list(cardinal, page: int = 0, notice: str | None = None) -> tuple[str, object]:
    l10n = cardinal.l10n
    commands = _commands(cardinal)
    page_commands, page, total_pages, start = paginate(commands, page)
    text = l10n("ar_title")
    if notice:
        text += "\n" + notice
    text += "\n" + ("\n".join(f"• <code>{html.escape(c)}</code>" for c in page_commands)
                    if page_commands else l10n("ar_no_commands"))

    builder = InlineKeyboardBuilder()
    for offset, command in enumerate(page_commands):
        builder.button(text=command[:40], callback_data=f"ar:v:{start + offset}")
    # Дополняем последний ряд заглушками, чтобы кнопки шли по 3 в ряд
    if page_commands and len(page_commands) % 3:
        for _ in range(3 - len(page_commands) % 3):
            builder.button(text="➖", callback_data="noop")
    builder.adjust(3)
    if pager := pager_row("ar:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("ar_btn_add"), callback_data="ar:add"))
    builder.row(*nav_row(l10n, "sys"))
    return text, builder.as_markup()


def _ar_cancel_markup(l10n) -> object:
    """Своя кнопка «Отмена» для флоу автоответчика: возврат в меню автоответчика."""
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_cancel"), callback_data="ar:cancel")
    return builder.as_markup()


async def _edit_prompt(bot, chat_id: int, message_id: int | None, text: str, reply_markup=None) -> None:
    """Обновляет сообщение-«подсказку» бота на месте (по сохранённому id).

    Если сообщение недоступно (удалено/устарело) — отправляет новое,
    чтобы диалог не завис.
    """
    if message_id is not None:
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id,
                                        reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            pass
    await bot.send_message(chat_id, text, reply_markup=reply_markup)


# ---------- Список команд / просмотр / удаление ----------

@router.callback_query(F.data == "ar")
async def cb_list(query: CallbackQuery, cardinal) -> None:
    text, markup = build_commands_list(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ar:p:"))
async def cb_list_page(query: CallbackQuery, cardinal) -> None:
    text, markup = build_commands_list(cardinal, page=int(query.data.rsplit(":", 1)[1]))
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("ar:v:"))
async def cb_view(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    commands = _commands(cardinal)
    if not (0 <= index < len(commands)):
        await query.answer(l10n("ar_missing"), show_alert=True)
        return
    command = commands[index]
    response = cardinal.autoresponse_config.commands[command]
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("ar_btn_edit"), callback_data=f"ar:edit:{index}")
    builder.button(text=l10n("ar_btn_delete"), callback_data=f"ar:del:{index}")
    builder.adjust(2)
    builder.row(*nav_row(l10n, f"ar:p:{index // PAGE_SIZE}"))
    await safe_edit(query.message,
                    l10n("ar_command_view", command=html.escape(command), response=html.escape(response)),
                    builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ar:del:"))
async def cb_delete(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    commands = _commands(cardinal)
    if not (0 <= index < len(commands)):
        await query.answer(l10n("ar_missing"), show_alert=True)
        return
    command = commands[index]
    del cardinal.autoresponse_config.commands[command]
    save_autoresponse_config(cardinal.autoresponse_config)
    await query.answer(l10n("ar_deleted", command=command))
    text, markup = build_commands_list(cardinal)
    await safe_edit(query.message, text, markup)


# ---------- Флоу добавления ----------

@router.callback_query(F.data == "ar:add")
async def cb_add(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    await state.set_state(AddCommand.command)
    await state.update_data(prompt_message_id=query.message.message_id)
    await safe_edit(query.message, cardinal.l10n("ar_enter_command"), _ar_cancel_markup(cardinal.l10n))
    await query.answer()


@router.message(AddCommand.command, F.text)
async def msg_command(message: Message, state: FSMContext, cardinal) -> None:
    """Шаг 1: пользователь ввёл команду. Удаляем его сообщение,
    переходим к вводу текста ответа в том же сообщении бота."""
    data = await state.get_data()
    prompt_id = data.get("prompt_message_id")
    await state.update_data(command=message.text.strip())
    await state.set_state(AddCommand.response)
    with suppress(Exception):
        await message.delete()
    await _edit_prompt(message.bot, message.chat.id, prompt_id,
                       cardinal.l10n("ar_enter_response"), _ar_cancel_markup(cardinal.l10n))


@router.message(AddCommand.response, F.text)
async def msg_response(message: Message, state: FSMContext, cardinal) -> None:
    """Шаг 2: пользователь ввёл текст ответа. Сохраняем команду, удаляем его
    сообщение, то же сообщение бота превращается в меню автоответчика с уведомлением."""
    data = await state.get_data()
    await state.clear()
    command = data.get("command", "")
    prompt_id = data.get("prompt_message_id")
    if not command:
        return
    cardinal.autoresponse_config.commands[command] = message.text
    save_autoresponse_config(cardinal.autoresponse_config)
    with suppress(Exception):
        await message.delete()
    text, markup = build_commands_list(
        cardinal, notice=cardinal.l10n("ar_added", command=html.escape(command)))
    await _edit_prompt(message.bot, message.chat.id, prompt_id, text, markup)


# ---------- Флоу правки ----------

@router.callback_query(F.data.startswith("ar:edit:"))
async def cb_edit(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    commands = _commands(cardinal)
    if not (0 <= index < len(commands)):
        await query.answer(l10n("ar_missing"), show_alert=True)
        return
    await state.set_state(EditResponse.response)
    await state.update_data(command=commands[index], prompt_message_id=query.message.message_id)
    await safe_edit(query.message, l10n("ar_enter_new_response", command=html.escape(commands[index])),
                    _ar_cancel_markup(l10n))
    await query.answer()


@router.message(EditResponse.response, F.text)
async def msg_edited_response(message: Message, state: FSMContext, cardinal) -> None:
    data = await state.get_data()
    await state.clear()
    command = data.get("command", "")
    prompt_id = data.get("prompt_message_id")
    if command not in cardinal.autoresponse_config.commands:
        await message.answer(cardinal.l10n("ar_missing"))
        return
    cardinal.autoresponse_config.commands[command] = message.text
    save_autoresponse_config(cardinal.autoresponse_config)
    with suppress(Exception):
        await message.delete()
    text, markup = build_commands_list(
        cardinal, notice=cardinal.l10n("ar_edited", command=html.escape(command)))
    await _edit_prompt(message.bot, message.chat.id, prompt_id, text, markup)


# ---------- «Отмена» — возврат в меню автоответчика ----------

@router.callback_query(F.data == "ar:cancel")
async def cb_ar_cancel(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    """Своя отмена: сбрасываем FSM-состояние и превращаем то же сообщение бота
    обратно в меню автоответчика, без пузыря «Действие отменено.»."""
    await state.clear()
    text, markup = build_commands_list(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()