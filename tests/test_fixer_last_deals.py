"""Раздел «Последние сделки»: формат списка, разделы лотов, листание (на моках)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fixer.tg.handlers import last_deals
from fixer_helpers import make_fixer
from playerokapi.common.enums import ItemDealDirections


def deal(i, item_id=None, status="CONFIRMED", rating=None, problem=False):
    return SimpleNamespace(
        id=f"d{i}", user=SimpleNamespace(username=f"buyer{i}"),
        item=SimpleNamespace(id=item_id or f"it{i}", name=f"Лот {i}", price=100 + i),
        raw_status=SimpleNamespace(name=status), has_problem=problem,
        review=SimpleNamespace(rating=rating) if rating else None,
    )


def test_list_format_four_lines_and_separator_between_deals():
    l10n = make_fixer().l10n
    text, _ = last_deals.build_last_deals(l10n, [deal(1, rating=5), deal(2)], {"d1": "JetBrains → Подписки"}, 0, False)
    body = text.split("\n\n", 1)[1]
    first, second = body.split(f"\n{last_deals.SEPARATOR}\n")
    assert first.splitlines() == [
        "📂 <b>Раздел:</b> JetBrains → Подписки",
        "🎁 <b>Лот:</b> Лот 1",
        "👤 <b>Покупатель:</b> buyer1 | 💰 <b>Цена:</b> 101 ₽",
        "✅ Завершено · ⭐ 5",
    ]
    assert second.startswith("📂 <b>Раздел:</b> ?")


def test_pagination_buttons():
    l10n = make_fixer().l10n
    _, markup = last_deals.build_last_deals(l10n, [deal(1)], {}, 1, True)
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert callbacks[:3] == ["last_deals:0", "last_deals:2", "last_deals:1"]  # назад, далее, обновить
    assert "menu" in callbacks


def test_empty_list():
    text, _ = last_deals.build_last_deals(make_fixer().l10n, [], {}, 0, False)
    assert "Продаж пока нет" in text


def test_sections_come_from_own_items_list():
    fixer = make_fixer()
    fixer.notifier = None
    fixer.account.get_my_items = lambda status, count: SimpleNamespace(items=[
        SimpleNamespace(id="it1", game=SimpleNamespace(name="JetBrains"), category=SimpleNamespace(name="Подписки")),
    ])
    sections = asyncio.run(last_deals._sections_for(fixer, [deal(1), deal(2)]))
    assert sections == {"d1": "JetBrains → Подписки", "d2": "?"}


class FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append((text, reply_markup))


class FakeQuery:
    def __init__(self, data):
        self.data, self.message, self.from_user, self.answers = data, FakeMessage(), SimpleNamespace(id=1), []

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))


def test_handler_requests_sales_and_shows_them():
    fixer = make_fixer()
    fixer.notifier = None
    asked = []

    def get_deals(count, after_cursor, direction):
        asked.append((count, after_cursor, direction))
        return SimpleNamespace(deals=[deal(1)], page_info=SimpleNamespace(has_next_page=False, end_cursor=None))

    fixer.account.get_deals = get_deals
    fixer.account.get_my_items = lambda status, count: SimpleNamespace(items=[])
    query = FakeQuery("last_deals")
    asyncio.run(last_deals.cb_last_deals(query, fixer))
    assert asked == [(last_deals.DEALS_PER_PAGE, None, ItemDealDirections.OUT)]
    assert "Лот 1" in query.message.edits[0][0]


def test_offline_shows_alert():
    fixer = make_fixer()
    fixer.account = None
    query = FakeQuery("last_deals")
    asyncio.run(last_deals.cb_last_deals(query, fixer))
    assert query.answers and query.answers[0][1] is True and query.message.edits == []


def test_deal_states():
    l10n = make_fixer().l10n
    assert last_deals.deal_state(l10n, deal(1, status="ROLLED_BACK")) == "↩️ Возврат"
    assert last_deals.deal_state(l10n, deal(1, status="SENT")) == "⏳ Не подтвердил"
    assert last_deals.deal_state(l10n, deal(1, status="CONFIRMED_AUTOMATICALLY")) == "✅ Завершено автоматически"
    assert last_deals.deal_state(l10n, deal(1, status="PAID")) == "💰 Оплачено, ждёт выдачи"
    assert last_deals.deal_state(l10n, deal(1, status="SENT", problem=True)) == "⚠️ Проблема в сделке"


def test_own_items_requested_like_the_site():
    """Без фильтра статусов Playerok отвечает на items 403 — шлём набор, как сайт."""
    from unittest.mock import MagicMock
    from playerokapi.account import Account
    account = Account.__new__(Account)
    account.id = "u1"
    account._persisted_query = MagicMock(return_value={"items": {"edges": [], "pageInfo": {}}})
    account.get_my_items(None, 100)
    flt = account._persisted_query.call_args.args[1]["filter"]
    assert flt == {"userId": "u1", "status": ["APPROVED", "PENDING_MODERATION", "PENDING_APPROVAL"],
                   "withOfficial": False}
