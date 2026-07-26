"""
Раздел «Статистика»: продажи по дням за неделю, итоги за 7/30 дней (из базы сводки)
и блок «Работа бота» — сколько бот сделал сам (выдачи, поднятия, автоответы) из `StatsStore`.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...stats_store import ACTION_AUTORESPONSE, ACTION_DELIVERY, ACTION_GREETING, ACTION_RAISE
from .common import nav_row, safe_edit

router = Router(name="stats")


def _digest_module(cardinal):
    return next((m for m in cardinal.modules if m.name == "digest"), None)


#: Максимальная длина мини-графика продаж (в блоках) в строке дня.
BAR_WIDTH = 8


def sales_bar(count: int, max_count: int, width: int = BAR_WIDTH) -> str:
    """Мини-график `▰▰▰▱▱` — доля продаж дня от лучшего дня недели."""
    if max_count <= 0 or count <= 0:
        return "▱" * width
    filled = max(1, round(count / max_count * width))
    return "▰" * filled + "▱" * (width - filled)


def _pretty_day(day: str) -> str:
    """ISO-день `2026-07-21` → `21.07`."""
    return f"{day[8:10]}.{day[5:7]}" if len(day) >= 10 else day


def build_bot_work_lines(cardinal) -> list[str]:
    """
    Строки блока «Работа бота»: сегодня / 7 дней / всего по каждому счётчику `StatsStore`
    (автоответы и приветствия показываются одной суммой). Пустой список, если хранилища нет.
    """
    stats = getattr(cardinal, "stats", None)
    if stats is None:
        return []
    l10n = cardinal.l10n
    lines = ["", l10n("st_bot_title")]
    for key, actions in (
        ("st_bot_delivered", (ACTION_DELIVERY,)),
        ("st_bot_raised", (ACTION_RAISE,)),
        ("st_bot_responses", (ACTION_AUTORESPONSE, ACTION_GREETING)),
    ):
        lines.append(l10n(
            key,
            today=sum(stats.for_period(action, 1) for action in actions),
            week=sum(stats.for_period(action, 7) for action in actions),
            total=sum(stats.totals(action) for action in actions),
        ))
    return lines


def build_stats_view(cardinal) -> tuple[str, object] | None:
    """Текст статистики + клавиатура (`None`, если модуль сводки недоступен)."""
    l10n = cardinal.l10n
    module = _digest_module(cardinal)
    if module is None:
        return None

    month = module.get_last_days(30)
    week_cutoff = {day for day, _, _ in module.get_last_days(7)}

    lines = [l10n("st_title")]
    week_rows = [(day, count, revenue) for day, count, revenue in month if day in week_cutoff]
    if week_rows:
        max_count = max(count for _, count, _ in week_rows)
        lines += [l10n("st_line", day=_pretty_day(day), bar=sales_bar(count, max_count),
                       count=count, revenue=f"{revenue:.2f}")
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
    lines += build_bot_work_lines(cardinal)

    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n))
    return "\n".join(lines), builder.as_markup()


@router.callback_query(F.data == "st")
async def cb_stats(query: CallbackQuery, cardinal) -> None:
    view = build_stats_view(cardinal)
    if view is None:
        await query.answer(cardinal.l10n("digest_unavailable"), show_alert=True)
        return
    await safe_edit(query.message, *view)
    await query.answer()
