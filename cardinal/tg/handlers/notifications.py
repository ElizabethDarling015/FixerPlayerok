"""Раздел «Уведомления»: тумблеры по каждому типу уведомлений (пишутся в main.toml)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...settings import NotificationsSettings, save_main_settings
from .common import nav_row, on_off, safe_edit

router = Router(name="notifications")

#: Все тумблеры уведомлений (поля `NotificationsSettings`).
NOTIFICATION_KEYS = tuple(NotificationsSettings.model_fields)


def build_notifications_menu(cardinal) -> tuple[str, object]:
    l10n = cardinal.l10n
    toggles = cardinal.settings.notifications
    builder = InlineKeyboardBuilder()
    for key in NOTIFICATION_KEYS:
        builder.button(text=f"{on_off(l10n, getattr(toggles, key))} {l10n('nt_' + key)}",
                       callback_data=f"nt:t:{key}")
    builder.adjust(2)
    builder.row(*nav_row(l10n, "sys"))
    return l10n("nt_title"), builder.as_markup()


@router.callback_query(F.data == "nt")
async def cb_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_notifications_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("nt:t:"))
async def cb_toggle(query: CallbackQuery, cardinal) -> None:
    key = query.data.rsplit(":", 1)[1]
    if key not in NOTIFICATION_KEYS:
        await query.answer()
        return
    toggles = cardinal.settings.notifications
    setattr(toggles, key, not getattr(toggles, key))
    save_main_settings(cardinal.settings)
    text, markup = build_notifications_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()
