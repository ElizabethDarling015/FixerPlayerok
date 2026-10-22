"""Раздел «👤 Профиль» (главное меню): всё, что Playerok знает о вашем аккаунте.

Данные — запрос `user` по своему ID (`Account.get_full_profile`): ник, ID, email, рейтинг и
отзывы, верификация и блокировка, дата регистрации, подробный баланс. Счётчики лотов, продаж
и покупок бот считает сам — по спискам «Мои товары» и «Мои продажи/покупки» (поле `stats`
в профиле Playerok для своего аккаунта приходит нулевым). Каждое открытие — свежие запросы.
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


#: Статусы сделок для счётчиков продаж.
SALE_ACTIVE = ("PAID", "PENDING", "SENT")
SALE_DONE = ("CONFIRMED", "CONFIRMED_AUTOMATICALLY")
SALE_REFUND = ("ROLLED_BACK",)
#: Размер страницы, если Playerok не вернул totalCount и приходится считать постранично.
COUNT_PAGE = 24
COUNT_MAX_PAGES = 100


def _count(fetch) -> int | None:
    """Сколько всего элементов: `totalCount` первой страницы, иначе — постранично.
    `fetch(count, cursor)` → страница с `total_count`, `page_info` и списком в `deals`/`items`."""
    page = fetch(1, None)
    total = getattr(page, "total_count", None)
    if total is not None:
        return int(total)
    count, cursor = 0, None
    for _ in range(COUNT_MAX_PAGES):
        page = fetch(COUNT_PAGE, cursor)
        if page is None:
            break
        count += len(getattr(page, "deals", None) or getattr(page, "items", None) or [])
        info = getattr(page, "page_info", None)
        nxt = getattr(info, "end_cursor", None)
        if not getattr(info, "has_next_page", False) or not nxt or nxt == cursor:
            break
        cursor = nxt
    return count


def collect_counts(account) -> dict:
    """Счётчики профиля (блокирующий — звать в потоке). Ошибка одного счётчика — «—»."""
    from playerokapi.common.enums import ItemDealDirections

    from ...storefront import ACTIVE_STATUSES, INACTIVE_STATUSES

    from ...deals_in_work import DealsInWork

    def items(statuses):
        return _count(lambda n, c: account.get_my_items(statuses, n, c))

    counts: dict = {}
    jobs = {
        "items_active": lambda: items(ACTIVE_STATUSES),
        "items_inactive": lambda: items(INACTIVE_STATUSES),
        "purchases": lambda: _count(lambda n, c: account.get_deals(count=n, after_cursor=c,
                                                                   direction=ItemDealDirections.IN)),
    }
    for key, job in jobs.items():
        try:
            counts[key] = job()
        except Exception as exc:
            logger.warning("[profile] Счётчик {} не посчитан: {}", key, exc)
            counts[key] = None
    # Продажи — один проход по «Моим продажам» (как раздел «Сделки в работе»), разбивка по статусу.
    try:
        sales = DealsInWork(order_file=None).fetch_sales(account) or []
        raw = [getattr(getattr(d, "raw_status", None), "name", None) for d in sales]
        counts.update(sales_total=len(sales),
                      sales_active=sum(r in SALE_ACTIVE for r in raw),
                      sales_done=sum(r in SALE_DONE for r in raw),
                      sales_refund=sum(r in SALE_REFUND for r in raw))
    except Exception as exc:
        logger.warning("[profile] Продажи не посчитаны: {}", exc)
        counts.update(sales_total=None, sales_active=None, sales_done=None, sales_refund=None)
    return counts


def _n(value) -> str:
    return str(value) if value is not None else "—"


def build_profile(l10n, profile, tz=None, counts: dict | None = None) -> tuple[str, object]:
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

    if counts:
        c = {k: _n(v) for k, v in counts.items()}
        lines += [SEPARATOR,
                  l10n("pf_items", active=c["items_active"], inactive=c["items_inactive"]),
                  l10n("pf_sales", total=c["sales_total"], done=c["sales_done"], active=c["sales_active"],
                       refund=c["sales_refund"]),
                  l10n("pf_purchases", total=c["purchases"])]

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
        profile, counts = await asyncio.gather(
            asyncio.to_thread(fixer.account.get_full_profile),
            asyncio.to_thread(collect_counts, fixer.account),
        )
        if profile is None:
            raise RuntimeError("Playerok вернул пустой профиль")
    except Exception as exc:
        logger.exception("[profile] Не удалось загрузить профиль")
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data="pf"), *nav_row(l10n))
        await safe_edit(query.message, l10n("pf_title") + "\n" + SEPARATOR + "\n"
                        + l10n("pf_failed", error=html.escape(str(exc)[:200])), builder.as_markup())
        return
    text, markup = build_profile(l10n, profile, seller_tz(fixer.settings), counts)
    await safe_edit(query.message, text, markup)
