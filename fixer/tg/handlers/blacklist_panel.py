"""Раздел «Чёрный список»: ники покупателей, которых игнорируют модули Fixer."""
from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import save_blacklist_config
from .common import cancel_markup, nav_row, pager_row, paginate, safe_edit

router = Router(name="blacklist")


class AddUser(StatesGroup):
    username = State()


def build_blacklist_menu(fixer, page: int = 0) -> tuple[str, object]:
    l10n = fixer.l10n
    usernames = sorted(fixer.blacklist_config.usernames, key=str.casefold)
    page_usernames, page, total_pages, start = paginate(usernames, page)
    text = l10n("bl_title") + "\n" + ("\n".join(f"• <code>{html.escape(u)}</code>" for u in page_usernames)
                                     if page_usernames else l10n("bl_empty"))
    builder = InlineKeyboardBuilder()
    for offset, username in enumerate(page_usernames):
        builder.button(text=f"❌ {username[:32]}", callback_data=f"bl:del:{start + offset}")
    builder.adjust(2)
    if pager := pager_row("bl:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("bl_btn_add"), callback_data="bl:add"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


@router.callback_query(F.data == "bl")
async def cb_menu(query: CallbackQuery, fixer) -> None:
    text, markup = build_blacklist_menu(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("bl:p:"))
async def cb_menu_page(query: CallbackQuery, fixer) -> None:
    text, markup = build_blacklist_menu(fixer, page=int(query.data.rsplit(":", 1)[1]))
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("bl:del:"))
async def cb_delete(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    index = int(query.data.rsplit(":", 1)[1])
    usernames = sorted(fixer.blacklist_config.usernames, key=str.casefold)
    if not (0 <= index < len(usernames)):
        await query.answer(l10n("bl_missing"), show_alert=True)
        return
    username = usernames[index]
    fixer.blacklist_config.usernames = [u for u in fixer.blacklist_config.usernames if u != username]
    save_blacklist_config(fixer.blacklist_config)
    await query.answer(l10n("bl_removed", username=username))
    text, markup = build_blacklist_menu(fixer)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "bl:add")
async def cb_add(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.set_state(AddUser.username)
    await safe_edit(query.message, fixer.l10n("bl_enter_username"), cancel_markup(fixer.l10n))
    await query.answer()


@router.message(AddUser.username, F.text)
async def msg_username(message: Message, state: FSMContext, fixer) -> None:
    await state.clear()
    l10n = fixer.l10n
    username = message.text.strip().lstrip("@")
    if not username:
        await message.answer(l10n("bl_enter_username"))
        return
    if fixer.blacklist_config.contains(username):
        await message.answer(l10n("bl_already", username=html.escape(username)))
    else:
        fixer.blacklist_config.usernames.append(username)
        save_blacklist_config(fixer.blacklist_config)
        await message.answer(l10n("bl_added", username=html.escape(username)))
    text, markup = build_blacklist_menu(fixer)
    await message.answer(text, reply_markup=markup)
