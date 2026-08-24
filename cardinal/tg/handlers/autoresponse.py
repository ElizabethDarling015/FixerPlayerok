"""Раздел «Автоответчик»: список команд, просмотр/удаление, добавление через FSM-диалог."""
from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import save_autoresponse_config
from .common import PAGE_SIZE, cancel_markup, nav_row, pager_row, paginate, safe_edit

router = Router(name="autoresponse")


class AddCommand(StatesGroup):
    command = State()
    response = State()


class EditResponse(StatesGroup):
    response = State()


def _commands(cardinal) -> list[str]:
    return sorted(cardinal.autoresponse_config.commands)


def build_commands_list(cardinal, page: int = 0) -> tuple[str, object]:
    l10n = cardinal.l10n
    commands = _commands(cardinal)
    page_commands, page, total_pages, start = paginate(commands, page)

    text = l10n("ar_title") + "\n" + ("\n".join(f"• <code>{html.escape(c)}</code>" for c in page_commands)
                                      if page_commands else l10n("ar_no_commands"))
    builder = InlineKeyboardBuilder()
    for offset, command in enumerate(page_commands):
        builder.button(text=command[:40], callback_data=f"ar:v:{start + offset}")
    builder.adjust(2)
    if pager := pager_row("ar:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("ar_btn_add"), callback_data="ar:add"))
    builder.row(*nav_row(l10n, "sys"))
    return text, builder.as_markup()


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
    # «Назад» ведёт на страницу списка, где находится эта команда.
    builder.row(*nav_row(l10n, f"ar:p:{index // PAGE_SIZE}"))
    await safe_edit(query.message,
                    l10n("ar_command_view", command=html.escape(command), response=html.escape(response)),
                    builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ar:edit:"))
async def cb_edit(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    index = int(query.data.rsplit(":", 1)[1])
    commands = _commands(cardinal)
    if not (0 <= index < len(commands)):
        await query.answer(l10n("ar_missing"), show_alert=True)
        return
    await state.set_state(EditResponse.response)
    await state.update_data(command=commands[index])
    await safe_edit(query.message, l10n("ar_enter_new_response", command=html.escape(commands[index])),
                    cancel_markup(l10n))
    await query.answer()


@router.message(EditResponse.response, F.text)
async def msg_edited_response(message: Message, state: FSMContext, cardinal) -> None:
    data = await state.get_data()
    await state.clear()
    command = data.get("command", "")
    if command not in cardinal.autoresponse_config.commands:
        await message.answer(cardinal.l10n("ar_missing"))
        return
    cardinal.autoresponse_config.commands[command] = message.text
    save_autoresponse_config(cardinal.autoresponse_config)
    await message.answer(cardinal.l10n("ar_edited", command=html.escape(command)))
    text, markup = build_commands_list(cardinal)
    await message.answer(text, reply_markup=markup)


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


@router.callback_query(F.data == "ar:add")
async def cb_add(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    await state.set_state(AddCommand.command)
    await safe_edit(query.message, cardinal.l10n("ar_enter_command"), cancel_markup(cardinal.l10n))
    await query.answer()


@router.message(AddCommand.command, F.text)
async def msg_command(message: Message, state: FSMContext, cardinal) -> None:
    await state.update_data(command=message.text.strip())
    await state.set_state(AddCommand.response)
    await message.answer(cardinal.l10n("ar_enter_response"), reply_markup=cancel_markup(cardinal.l10n))


@router.message(AddCommand.response, F.text)
async def msg_response(message: Message, state: FSMContext, cardinal) -> None:
    data = await state.get_data()
    await state.clear()
    command = data["command"]
    cardinal.autoresponse_config.commands[command] = message.text
    save_autoresponse_config(cardinal.autoresponse_config)
    await message.answer(cardinal.l10n("ar_added", command=html.escape(command)))
    text, markup = build_commands_list(cardinal)
    await message.answer(text, reply_markup=markup)
