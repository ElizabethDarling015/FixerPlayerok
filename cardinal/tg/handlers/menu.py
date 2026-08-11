"""Главное меню панели: статус аккаунта, разделы и подменю «Глобальные переключатели»."""
from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import save_main_settings
from .common import cancel_markup, nav_row, on_off, safe_edit

router = Router(name="menu")

#: Порядок модулей в подменю переключателей (имена совпадают с полями `ModulesSettings`).
MODULE_NAMES = ("autodelivery", "autoraise", "autoresponse", "autorestore", "greeting", "online", "digest")


class EditGreeting(StatesGroup):
    text = State()


def build_main_menu(cardinal) -> tuple[str, object]:
    l10n = cardinal.l10n
    account = cardinal.account
    profile = getattr(account, "profile", None)
    balance = profile.balance.value if profile is not None and profile.balance is not None else "?"
    text = l10n(
        "menu_title",
        username=account.username if account is not None else "?",
        balance=balance,
        uptime=cardinal.uptime,
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("menu_section_toggles"), callback_data="gl")
    builder.button(text=l10n("menu_section_autodelivery"), callback_data="ad")
    builder.button(text=l10n("menu_section_autoresponse"), callback_data="ar")
    builder.button(text=l10n("menu_section_blacklist"), callback_data="bl")
    builder.button(text=l10n("menu_section_notifications"), callback_data="nt")
    builder.button(text=l10n("menu_section_plugins"), callback_data="pl")
    builder.button(text=l10n("menu_section_stats"), callback_data="st")
    builder.button(text=l10n("menu_section_system"), callback_data="sys")
    builder.button(text=l10n("menu_btn_digest"), callback_data="digest:now")
    builder.adjust(1, 2, 2, 2, 2, 1)
    return text, builder.as_markup()


def build_toggles_menu(cardinal) -> tuple[str, object]:
    """Подменю «Глобальные переключатели»: тумблеры всех модулей + текст приветствия."""
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    for name in MODULE_NAMES:
        enabled = getattr(cardinal.settings.modules, name)
        builder.button(text=f"{on_off(l10n, enabled)} {l10n('module_' + name)}", callback_data=f"mod:{name}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=l10n("gl_btn_greeting_text"), callback_data="gl:greet"))
    builder.row(*nav_row(l10n))
    return l10n("gl_title"), builder.as_markup()


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_menu(message: Message, cardinal) -> None:
    text, markup = build_main_menu(cardinal)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "menu")
async def cb_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_main_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "gl")
async def cb_toggles_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_toggles_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("mod:"))
async def cb_toggle_module(query: CallbackQuery, cardinal) -> None:
    name = query.data.split(":", 1)[1]
    if name not in MODULE_NAMES:
        await query.answer()
        return
    l10n = cardinal.l10n
    was_enabled = getattr(cardinal.settings.modules, name)
    setattr(cardinal.settings.modules, name, not was_enabled)
    save_main_settings(cardinal.settings)
    await query.answer(l10n("module_toggled_off" if was_enabled else "module_toggled_on",
                            module=l10n("module_" + name)))
    text, markup = build_toggles_menu(cardinal)
    await safe_edit(query.message, text, markup)


# ----------------------------------------------------------------------
# Текст приветствия (FSM)
# ----------------------------------------------------------------------

@router.callback_query(F.data == "gl:greet")
async def cb_edit_greeting(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    await state.set_state(EditGreeting.text)
    await safe_edit(query.message,
                    l10n("gl_enter_greeting", current=html.escape(cardinal.settings.greeting.text)),
                    cancel_markup(l10n))
    await query.answer()


@router.message(EditGreeting.text, F.text)
async def msg_greeting_text(message: Message, state: FSMContext, cardinal) -> None:
    await state.clear()
    cardinal.settings.greeting.text = message.text
    save_main_settings(cardinal.settings)
    await message.answer(cardinal.l10n("gl_greeting_saved"))
    text, markup = build_toggles_menu(cardinal)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "digest:now")
async def cb_digest_now(query: CallbackQuery, cardinal) -> None:
    """Кнопка «Сводка сейчас»: строит и присылает сводку, не дожидаясь расписания."""
    print("=" * 50)
    print("ОБРАБОТЧИК digest:now ВЫЗВАН")
    print("=" * 50)

    import asyncio
    module = next((m for m in cardinal.modules if m.name == "digest"), None)
    if module is None:
        await query.answer(cardinal.l10n("digest_unavailable"), show_alert=True)
        return
    text = await asyncio.to_thread(module.build_digest)

    # Создаём клавиатуру с кнопкой "На главную"
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n))
    markup = builder.as_markup()

    # Редактируем текущее сообщение вместо отправки нового
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(query: CallbackQuery) -> None:
    """Кнопка-индикатор страницы «2/5» — никуда не ведёт."""
    await query.answer()


@router.callback_query(F.data == "close")
async def cb_close(query: CallbackQuery) -> None:
    await query.message.delete()
    await query.answer()


@router.callback_query(F.data == "fsm:cancel")
async def cb_fsm_cancel(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    await state.clear()
    await safe_edit(query.message, cardinal.l10n("cancelled"))
    await query.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, cardinal) -> None:
    await state.clear()
    await message.answer(cardinal.l10n("cancelled"))
