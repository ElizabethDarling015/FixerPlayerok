"""Раздел «Статистика»: продажи по дням за неделю и итоги за 7/30 дней (из базы сводки)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .common import nav_row, safe_edit

router = Router(name="stats")


def _digest_module(fixer):
    return next((m for m in fixer.modules if m.name == "digest"), None)


def build_stats_view(fixer) -> tuple[str, object] | None:
    """Текст статистики + клавиатура (`None`, если модуль сводки недоступен)."""
    l10n = fixer.l10n
    module = _digest_module(fixer)
    if module is None:
        return None

    month = module.get_last_days(30)
    week_cutoff = {day for day, _, _ in module.get_last_days(7)}

    lines = [l10n("st_title")]
    week_rows = [(day, count, revenue) for day, count, revenue in month if day in week_cutoff]
    if week_rows:
        lines += [l10n("st_line", day=day, count=count, revenue=f"{revenue:.2f}")
                  for day, count, revenue in week_rows]
    else:
        lines.append(l10n("st_empty"))

    week_count = sum(count for _, count, _ in week_rows)
    week_revenue = sum(revenue for _, _, revenue in week_rows)
    month_count = sum(count for _, count, _ in month)
    month_revenue = sum(revenue for _, _, revenue in month)
    lines.append("")
    lines.append(l10n("st_total_week", count=week_count, revenue=f"{week_revenue:.2f}"))
    lines.append(l10n("st_total_month", count=month_count, revenue=f"{month_revenue:.2f}"))

    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n))
    return "\n".join(lines), builder.as_markup()


@router.callback_query(F.data == "st")
async def cb_stats(query: CallbackQuery, fixer) -> None:
    view = build_stats_view(fixer)
    if view is None:
        await query.answer(fixer.l10n("digest_unavailable"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()
