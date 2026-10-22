"""Раздел «👤 Профиль» (главное меню): всё, что Playerok знает о вашем аккаунте.

Данные — запрос `user` по своему ID (`Account.get_full_profile`): ник, ID, email, рейтинг и
отзывы, верификация и блокировка, дата регистрации, подробный баланс и счётчики лотов,
продаж и покупок. Каждое открытие и «🔄 Обновить» — свежий запрос.
"""
from __future__ import annotations

import asyncio
import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from ...sales_stats import _parse_dt, fmt_rub, seller_tz
from .common import nav_row, safe_edit

router = Router(name="profile")

SEPARATOR = "━━━━━━━━━━━━━━━━━━━"


def _rub(value) -> str:
    return fmt_rub(value) if value is not None else "—"


def _counts(l10n, stats) -> str:
    """«активные / завершённые / всего»."""
    total = getattr(stats, "total", None)
    finished = getattr(stats, "finished", None)
    if total is None:
        return "—"
    active = total - finished if finished is not None else None
    return l10n("pf_counts", active=active if active is not None else "—",
                finished=finished if finished is not None else "—", total=total)


def build_profile(l10n, profile, tz=None) -> tuple[str, object]:
    lines = [l10n("pf_title"), SEPARATOR]
    lines.append(l10n("pf_name", username=html.escape(profile.username or "?")))
    lines.append(l10n("pf_id", id=html.escape(profile.id or "?")))
    if profile.email:
        lines.append(l10n("pf_email", email=html.escape(profile.email)))
    rating = profile.rating if profile.rating is not None else "—"
    lines.append(l10n("pf_rating", rating=rating, reviews=profile.reviews_count or 0))
    lines.append(l10n("pf_verified_yes" if profile.is_verified else "pf_verified_no"))
    if profile.is_blocked:
        until = _parse_dt(profile.is_blocked_for) if profile.is_blocked_for else None
        lines.append(l10n("pf_blocked_until", until=until.astimezone(tz).strftime("%d.%m.%Y, %H:%M"))
                     if until else l10n("pf_blocked"))
    created = _parse_dt(profile.created_at)
    if created is not None:
        lines.append(l10n("pf_created", date=created.astimezone(tz).strftime("%d.%m.%Y")))

    b = profile.balance
    if b is not None:
        lines += [SEPARATOR,
                  l10n("pf_balance", value=_rub(b.value)),
                  l10n("pf_available", value=_rub(b.available)),
                  l10n("pf_withdrawable", value=_rub(b.withdrawable)),
                  l10n("pf_pending", value=_rub(b.pending_income)),
                  l10n("pf_frozen", value=_rub(b.frozen))]

    stats = profile.stats
    if stats is not None:
        deals = getattr(stats, "deals", None)
        lines += [SEPARATOR,
                  l10n("pf_items", counts=_counts(l10n, getattr(stats, "items", None))),
                  l10n("pf_sales", counts=_counts(l10n, getattr(deals, "outgoing", None))),
                  l10n("pf_purchases", counts=_counts(l10n, getattr(deals, "incoming", None)))]

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data="pf"),
                *nav_row(l10n))
    return "\n".join(lines), builder.as_markup()


@router.callback_query(F.data == "pf")
async def cb_profile(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    if fixer.account is None or not getattr(fixer, "playerok_connected", True):
        with suppress(Exception):
            await query.answer(l10n("pf_offline"), show_alert=True)
        return
    with suppress(Exception):
        await query.answer()
    try:
        profile = await asyncio.to_thread(fixer.account.get_full_profile)
        if profile is None:
            raise RuntimeError("Playerok вернул пустой профиль")
    except Exception as exc:
        logger.exception("[profile] Не удалось загрузить профиль")
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data="pf"), *nav_row(l10n))
        await safe_edit(query.message, l10n("pf_title") + "\n" + SEPARATOR + "\n"
                        + l10n("pf_failed", error=html.escape(str(exc)[:200])), builder.as_markup())
        return
    text, markup = build_profile(l10n, profile, seller_tz(fixer.settings))
    await safe_edit(query.message, text, markup)
