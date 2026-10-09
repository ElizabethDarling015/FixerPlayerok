"""Раздел «Статистика»: продажи по дням за неделю и итоги за 7/30 дней — из истории Playerok."""
from __future__ import annotations

import datetime
import html

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from ...sales_stats import fmt_rub, sum_totals
from .common import nav_row, safe_edit

router = Router(name="stats")


def _digest_module(fixer):
    return next((m for m in fixer.modules if m.name == "digest"), None)


def build_stats_text(l10n, days: dict, today: datetime.date) -> str:
    """Текст статистики по итогам `{день: DayTotals}` за последние 30 дней."""
    week_since = today - datetime.timedelta(days=6)
    month_since = today - datetime.timedelta(days=29)
    lines = [l10n("st_title")]
    week_days = sorted((d for d in days if d >= week_since), reverse=True)
    if any(days[d].count or days[d].refunds for d in week_days):
        for day in week_days:
            t = days[day]
            if not (t.count or t.refunds):
                continue
            line = l10n("st_line", day=day.strftime("%d.%m"), count=t.count,
                        gross=fmt_rub(t.gross), net=fmt_rub(t.net))
            if t.refunds:
                line += l10n("st_line_refunds", refunds=t.refunds)
            lines.append(line)
    else:
        lines.append(l10n("st_empty"))

    week = sum_totals(days, week_since)
    month = sum_totals(days, month_since)
    lines.append("")
    lines.append(l10n("st_total_week", count=week.count, gross=fmt_rub(week.gross), net=fmt_rub(week.net)))
    lines.append(l10n("st_total_month", count=month.count, gross=fmt_rub(month.gross), net=fmt_rub(month.net)))
    if month.refunds:
        lines.append(l10n("st_refunds_month", refunds=month.refunds))
    return "\n".join(lines)


@router.callback_query(F.data == "st")
async def cb_stats(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    module = _digest_module(fixer)
    if module is None:
        await query.answer(l10n("digest_unavailable"), show_alert=True)
        return
    if fixer.account is None:
        await query.answer(l10n("st_offline"), show_alert=True)
        return
    await query.answer()
    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n))
    try:
        days, today = await module.get_days(30)
        text = build_stats_text(l10n, days, today)
    except Exception as exc:
        logger.exception("[stats] Не удалось загрузить историю продаж")
        text = l10n("st_title") + "\n\n" + l10n("st_failed", error=html.escape(str(exc)[:200]))
    await safe_edit(query.message, text, builder.as_markup())
