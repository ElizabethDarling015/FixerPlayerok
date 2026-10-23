"""«Ночное сообщение» (Глобальные переключатели): просмотр и смена текстов.

Сам переключатель — обычный тумблер модуля (`mod:night`). «✏️ Текст» открывает оба ночных
текста: «🛒 После покупки» и «💬 Ответ на сообщение». Выбрали один — бот показывает его и ждёт
новый текст сообщением (ваше сообщение удаляется, итог — в том же сообщении бота).
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

from ...settings import DEFAULT_NIGHT_REPLY_TEXT, DEFAULT_NIGHT_TEXT, save_main_settings
from .common import remember_panel, safe_edit, show_in_panel, with_error
from .menu import build_toggles_menu

router = Router(name="night")

#: Сколько секунд бот ждёт новый текст; позже обычные сообщения снова работают как обычно.
WAIT_SECONDS = 10 * 60
#: Ограничение длины — сообщение Playerok не должно быть простынёй.
MAX_TEXT = 1000


class NightText(StatesGroup):
    text = State()


#: Какой текст правим: ключ → (поле `[night]`, текст по умолчанию, ключ описания).
KINDS = {
    "buy": ("text", DEFAULT_NIGHT_TEXT, "night_kind_buy"),
    "reply": ("reply_text", DEFAULT_NIGHT_REPLY_TEXT, "night_kind_reply"),
}


def _tz(fixer, l10n) -> str:
    return html.escape(fixer.settings.digest.timezone or l10n("night_tz_server"))


def build_night_texts_menu(fixer) -> tuple[str, object]:
    """Оба ночных текста и выбор, какой править."""
    l10n = fixer.l10n
    night = fixer.settings.night
    text = l10n("night_texts_menu", start=night.start, end=night.end, tz=_tz(fixer, l10n),
                buy=html.escape(night.text), reply=html.escape(night.reply_text))
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("night_btn_edit_buy"), callback_data="night:edit:buy"),
                InlineKeyboardButton(text=l10n("night_btn_edit_reply"), callback_data="night:edit:reply"))
    builder.row(InlineKeyboardButton(text=l10n("btn_back"), callback_data="night:back"))
    return text, builder.as_markup()


def build_night_text_view(fixer, kind: str = "buy") -> tuple[str, object]:
    l10n = fixer.l10n
    night = fixer.settings.night
    attr, _, desc = KINDS[kind]
    text = l10n(
        "night_text_view",
        title=l10n(desc + "_title"),
        about=l10n(desc, start=night.start, end=night.end, tz=_tz(fixer, l10n)),
        text=html.escape(getattr(night, attr)),
        placeholders=l10n("night_placeholders_" + kind),
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("night_btn_reset"), callback_data=f"night:reset:{kind}"))
    builder.row(InlineKeyboardButton(text=l10n("btn_back"), callback_data="night:text"))
    return text, builder.as_markup()


@router.callback_query(F.data == "night:text")
async def cb_night_texts(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.clear()
    text, markup = build_night_texts_menu(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.in_({"night:edit:buy", "night:edit:reply"}))
async def cb_night_text(query: CallbackQuery, state: FSMContext, fixer) -> None:
    kind = query.data.rsplit(":", 1)[1]
    await state.set_state(NightText.text)
    await state.update_data(since=time.time(), kind=kind)
    await remember_panel(state, query.message)
    text, markup = build_night_text_view(fixer, kind)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "night:back")
async def cb_night_back(query: CallbackQuery, state: FSMContext, fixer) -> None:
    await state.clear()
    text, markup = build_toggles_menu(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.in_({"night:reset:buy", "night:reset:reply"}))
async def cb_night_reset(query: CallbackQuery, state: FSMContext, fixer) -> None:
    kind = query.data.rsplit(":", 1)[1]
    attr, default, _ = KINDS[kind]
    setattr(fixer.settings.night, attr, default)
    save_main_settings(fixer.settings)
    text, markup = build_night_text_view(fixer, kind)
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
    kind = data.get("kind") if data.get("kind") in KINDS else "buy"
    if error:
        text, markup = build_night_text_view(fixer, kind)
        await show_in_panel(message, state, with_error(error, text), markup)
        return
    setattr(fixer.settings.night, KINDS[kind][0], new_text)
    save_main_settings(fixer.settings)
    # Остаёмся на экране текста: видно, что сохранилось, можно сразу поправить ещё раз.
    await state.update_data(since=time.time())
    text, markup = build_night_text_view(fixer, kind)
    await show_in_panel(message, state, l10n("night_text_saved") + "\n\n" + text, markup)
