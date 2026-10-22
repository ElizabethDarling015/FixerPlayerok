"""«👤 Профиль» и «📈 Статистика» со сводкой дня."""
from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace as N
from unittest.mock import MagicMock

from fixer.tg.handlers import profile as pf
from fixer.tg.handlers import stats
from fixer_helpers import make_fixer
from playerokapi import parser
from playerokapi.account import Account


USER = {
    "id": "u1", "username": "BezLimit", "email": "a@b.c", "isVerified": True, "isBlocked": False,
    "balance": {"value": 15230, "available": 12000, "withdrawable": 11000, "pendingIncome": 2000, "frozen": 1230},
    "profile": {"username": "BezLimit", "rating": 4.9, "testimonialCounter": 312,
                "createdAt": "2025-03-12T10:00:00.000Z"},
    "stats": {"items": {"total": 40, "finished": 28},
              "deals": {"incoming": {"total": 3, "finished": 3}, "outgoing": {"total": 500, "finished": 497}}},
}


def test_full_profile_uses_user_query_by_own_id():
    account = Account.__new__(Account)
    account.id = "u1"
    account._persisted_query = MagicMock(return_value={"user": USER})
    profile = account.get_full_profile()
    account._persisted_query.assert_called_once_with("user", {"id": "u1", "hasSupportAccess": False})
    assert profile.email == "a@b.c" and profile.stats.items.total == 40 and profile.balance.withdrawable == 11000


COUNTS = {"items_active": 12, "items_inactive": 5, "sales_total": 40, "sales_active": 2, "sales_done": 36,
          "sales_refund": 2, "purchases": None}


def test_profile_screen():
    l10n = make_fixer().l10n
    text, markup = pf.build_profile(l10n, parser.account_profile(USER), counts=COUNTS)
    assert "\n\n" not in text
    for part in ("👤 <b>BezLimit</b>", "<code>u1</code>", "a@b.c", "4.9", "312", "✅ Верифицирован",
                 "15 230 ₽", "11 000 ₽", "❄️ Заморожено: 1 230 ₽",
                 "📦 Лоты: в продаже <b>12</b> · сняты и истекли <b>5</b>",
                 "🛒 Продажи: <b>40</b> · ✅ завершено 36 · ⏳ в работе 2 · ↩️ возвратов 2",
                 "🛍 Покупки: <b>—</b>"):
        assert part in text, part
    assert [b.callback_data for b in markup.inline_keyboard[0]] == ["pf", "menu"]


def test_blocked_profile_line():
    data = {**USER, "isBlocked": True, "isBlockedFor": "2026-11-01T10:00:00.000Z"}
    text, _ = pf.build_profile(make_fixer().l10n, parser.account_profile(data), datetime.timezone.utc)
    assert "⛔ <b>Заблокирован до 01.11.2026, 10:00</b>" in text


class FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append(text)


def test_stats_include_digest_with_one_history_request():
    fixer = make_fixer()
    calls = []
    today = datetime.date(2026, 10, 22)

    async def get_days(n):
        calls.append(n)
        return {}, today

    async def build_digest(days=None, today_=None, **_):
        assert days is not None  # переданы готовые итоги — второго запроса нет
        return "📊 <b>Сводка за 22.10.2026</b>"

    fixer.modules = [N(name="digest", get_days=get_days, build_digest=build_digest)]
    answers = []

    async def answer(*a, **k):
        answers.append(a)

    query = N(data="st", message=FakeMessage(), answer=answer)
    asyncio.run(stats.cb_stats(query, fixer))
    text = query.message.edits[0]
    assert calls == [30]
    assert "Статистика продаж" in text and f"\n{stats.SEPARATOR}\n📊 <b>Сводка за 22.10.2026</b>" in text


def test_counts_from_lists_not_from_zero_stats():
    """stats в профиле Playerok для своего аккаунта — нули; бот считает по спискам."""
    def deal(status):
        return N(raw_status=N(name=status), direction=None)

    sales = [deal("CONFIRMED")] * 30 + [deal("CONFIRMED_AUTOMATICALLY")] * 3 + [deal("SENT"), deal("PAID")] + [deal("ROLLED_BACK")]

    def get_deals(count=20, after_cursor=None, status=None, direction=None):
        if direction.name == "IN":
            return N(deals=[], page_info=None, total_count=0)
        return N(deals=sales, page_info=N(has_next_page=False, end_cursor=None), total_count=None)

    def get_my_items(statuses, count, cursor=None):
        active = statuses[0].name == "APPROVED"
        return N(items=[], page_info=None, total_count=7 if active else 4)

    account = N(get_deals=get_deals, get_my_items=get_my_items)
    assert pf.collect_counts(account) == {"items_active": 7, "items_inactive": 4, "purchases": 0, "sales_total": 36,
                                          "sales_active": 2, "sales_done": 33, "sales_refund": 1}


def test_count_falls_back_to_pages_without_total():
    pages = {None: (["a"] * 24, "c1"), "c1": (["b"] * 5, None)}

    def fetch(n, cursor):
        if n == 1:
            return N(items=["a"], total_count=None, page_info=None)
        items, nxt = pages[cursor]
        return N(items=items, total_count=None, page_info=N(has_next_page=nxt is not None, end_cursor=nxt))

    assert pf._count(fetch) == 29
