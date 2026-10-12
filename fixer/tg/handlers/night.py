"""«Ночное сообщение» (Глобальные переключатели): просмотр и смена текста.

Сам переключатель — обычный тумблер модуля (`mod:night`). Здесь — кнопка «✏️ Текст»:
бот показывает текущий текст и окно времени и ждёт новый текст сообщением.
"""
from __future__ import annotations

import html
import time

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import DEFAULT_NIGHT_TEXT, save_main_settings
from .common import remember_panel, safe_edit, show_in_panel, with_error
from .menu import build_toggles_menu

router = Router(name="night")

#: Сколько секунд бот ждёт новый текст; позже обычные сообщения снова работают как обычно.
WAIT_SECONDS = 10 * 60
#: Ограничение длины — сообщение Playerok не должно быть простынёй.
MAX_TEXT = 1000


class NightText(StatesGroup):
    text = State()


def build_night_text_view(fixer) -> tuple[str, object]:
    l10n = fixer.l10n
    night = fixer.settings.night
    text = l10n(
        "night_text_view",
        start=night.start, end=night.end,
        tz=html.escape(fixer.settings.digest.timezone or l10n("night_tz_server")),
        text=html.escape(night.text),
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("night_btn_reset"), callback_data="night:reset"))
    builder.row(InlineKeyboardButton(text=l10n("btn_back"), callback_data="night:back"))
    return text, builder.as_markup()


@router.callback_query(F.data == "night:text")
async def cb_night_text(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.set_state(NightText.text)
    await state.update_data(since=time.time())
    await remember_panel(state, query.message)
    text, markup = build_night_text_view(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "night:back")
async def cb_night_back(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.clear()
    text, markup = build_toggles_menu(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "night:reset")
async def cb_night_reset(query: CallbackQuery, state: FSMContext, fixer) -> None:
    fixer.settings.night.text = DEFAULT_NIGHT_TEXT
    save_main_settings(fixer.settings)
    text, markup = build_night_text_view(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer(fixer.l10n("night_text_saved"))


@router.message(StateFilter(NightText.text), F.text)
async def on_night_text(message: Message, state: FSMContext, fixer) -> None:
    l10n = fixer.l10n
    data = await state.get_data()
    # Reply на уведомление или давно забытое ожидание — это не новый текст: отпускаем
    # сообщение дальше (ответ покупателю и т.п.), а ожидание снимаем.
    if message.reply_to_message is not None or time.time() - data.get("since", 0) > WAIT_SECONDS:
        await state.clear()
        raise SkipHandler()
    new_text = (message.text or "").strip()
    error = None
    if not new_text or new_text.startswith("/"):
        error = l10n("night_text_empty")
    elif len(new_text) > MAX_TEXT:
        error = l10n("night_text_too_long", limit=MAX_TEXT)
    if error:
        text, markup = build_night_text_view(fixer)
        await show_in_panel(message, state, with_error(error, text), markup)
        return
    fixer.settings.night.text = new_text
    save_main_settings(fixer.settings)
    # Остаёмся на экране текста: видно, что сохранилось, можно сразу поправить ещё раз.
    await state.update_data(since=time.time())
    text, markup = build_night_text_view(fixer)
    await show_in_panel(message, state, l10n("night_text_saved") + "\n\n" + text, markup)
