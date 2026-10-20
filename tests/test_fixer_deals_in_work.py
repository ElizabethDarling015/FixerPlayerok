"""«⏳ Сделки в работе»: что попадает в раздел, порядок, число в меню, кнопки, выдача со склада."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from fixer.deals_in_work import DealsInWork, is_in_work
from fixer.tg.handlers import deals_in_work as dw
from fixer.tg.handlers import last_deals
from fixer.tg.handlers.menu import build_main_menu
from fixer_helpers import make_fixer
from playerokapi.autodelivery import AutoDeliveryManager
from playerokapi.common.enums import EventTypes, ItemDealDirections


def deal(i, status="PAID", problem=False, direction=ItemDealDirections.OUT, name=None):
    return SimpleNamespace(
        id=f"d{i}", user=SimpleNamespace(username=f"buyer{i}"),
        item=SimpleNamespace(id=f"it{i}", name=name or f"Лот {i}", price=100 + i),
        raw_status=SimpleNamespace(name=status) if status else None, has_problem=problem,
        direction=direction, chat=SimpleNamespace(id=f"chat-{i}"),
        created_at="2026-10-20T00:14:00.000Z",
    )


def ids(tracker):
    return [d.id for d in tracker.deals()]


def event(kind, d):
    return SimpleNamespace(type=kind, deal=d)


# ----------------------------------------------------------------------
# Что попадает в раздел и в каком порядке
# ----------------------------------------------------------------------

def test_rules():
    assert is_in_work("PAID", False)
    assert is_in_work("SENT", True)  # спор после подтверждения
    assert not is_in_work("SENT", False)
    for final in ("CONFIRMED", "CONFIRMED_AUTOMATICALLY", "ROLLED_BACK"):
        assert not is_in_work(final, True)


def test_events_keep_order_of_appearance():
    t = DealsInWork(order_file=None)
    t.on_event(event(EventTypes.NEW_DEAL, deal(1)))
    t.on_event(event(EventTypes.ITEM_PAID, deal(2, status=None)))  # WS: статуса нет, но это оплата
    t.on_event(event(EventTypes.NEW_DEAL, deal(3)))
    assert ids(t) == ["d1", "d2", "d3"]
    # Спор по сделке, которая уже в разделе, — остаётся на месте.
    t.on_event(event(EventTypes.DEAL_HAS_PROBLEM, deal(1, problem=True)))
    assert ids(t) == ["d1", "d2", "d3"] and t.has_problem("d1")
    # Подтвердили выдачу на сайте — уходит.
    t.on_event(event(EventTypes.ITEM_SENT, deal(2, status="SENT")))
    assert ids(t) == ["d1", "d3"]
    # Спор открыт позже, по уже подтверждённой сделке, — встаёт в конец.
    t.on_event(event(EventTypes.DEAL_HAS_PROBLEM, deal(2, status="SENT", problem=True)))
    assert ids(t) == ["d1", "d3", "d2"]
    # Спор после подтверждения закрыт — уходит; возврат — уходит.
    t.on_event(event(EventTypes.DEAL_PROBLEM_RESOLVED, deal(2, status="SENT")))
    t.on_event(event(EventTypes.DEAL_ROLLED_BACK, deal(1, status="ROLLED_BACK", problem=True)))
    assert ids(t) == ["d3"] and t.count == 1


def test_purchases_and_other_events_ignored():
    t = DealsInWork(order_file=None)
    t.on_event(event(EventTypes.NEW_DEAL, deal(1, direction=ItemDealDirections.IN)))
    t.on_event(event(EventTypes.NEW_MESSAGE, deal(2)))
    assert t.count == 0


def test_mark_sent_removes_and_stale_paid_does_not_return():
    t = DealsInWork(order_file=None)
    t.observe(deal(1))
    t.observe(deal(2, problem=True))
    t.mark_sent("d1")
    t.mark_sent("d2")
    assert ids(t) == ["d2"] and t.is_sent("d2")  # спор — остаётся, но выдача уже подтверждена
    # Playerok ещё несколько секунд отдаёт старый PAID — сделка не возвращается.
    t.observe(deal(1))
    t.replace_all([deal(2, problem=True), deal(1)])
    assert ids(t) == ["d2"] and t.is_sent("d2")


def test_first_sync_oldest_first_then_new_at_the_end(tmp_path):
    order = tmp_path / "order.json"
    t = DealsInWork(order_file=str(order))
    # Сайт отдаёт сначала новые.
    t.replace_all([deal(3), deal(2, status="CONFIRMED"), deal(1), deal(0, status="SENT", problem=True)])
    assert ids(t) == ["d0", "d1", "d3"] and t.synced
    t.replace_all([deal(4), deal(3), deal(1), deal(0, status="SENT", problem=True)])
    assert ids(t) == ["d0", "d1", "d3", "d4"]
    # После перезапуска порядок берётся из файла.
    t.observe(deal(5, status="SENT", problem=True))
    t2 = DealsInWork(order_file=str(order))
    t2.replace_all([deal(5, status="SENT", problem=True), deal(4), deal(3), deal(1),
                    deal(0, status="SENT", problem=True)])
    assert ids(t2) == ["d0", "d1", "d3", "d4", "d5"]


def test_resync_reads_all_sales_pages():
    fixer = make_fixer()
    pages = {None: ([deal(2), deal(1)], "c1"), "c1": ([deal(0, status="CONFIRMED")], None)}
    asked = []

    def get_deals(count, after_cursor, direction):
        asked.append((after_cursor, direction))
        items, nxt = pages[after_cursor]
        return SimpleNamespace(deals=items, page_info=SimpleNamespace(has_next_page=nxt is not None, end_cursor=nxt))

    fixer.account.get_deals = get_deals
    t = DealsInWork(order_file=None)
    assert asyncio.run(t.resync(fixer))
    assert asked == [(None, ItemDealDirections.OUT), ("c1", ItemDealDirections.OUT)]
    assert ids(t) == ["d1", "d2"]


# ----------------------------------------------------------------------
# Меню, список, карточка
# ----------------------------------------------------------------------

def test_main_menu_first_row_and_counter():
    fixer = make_fixer()
    fixer.deals_in_work = DealsInWork(order_file=None)
    _, markup = build_main_menu(fixer)
    first = markup.inline_keyboard[0]
    assert [b.callback_data for b in first] == ["chats", "dw"]
    assert first[1].text == "⏳ Сделки в работе"
    fixer.deals_in_work.observe(deal(1))
    fixer.deals_in_work.observe(deal(2))
    _, markup = build_main_menu(fixer)
    assert markup.inline_keyboard[0][1].text == "⏳ Сделки в работе (2)"


def test_list_text_and_buttons():
    l10n = make_fixer().l10n
    deals = [deal(1), deal(2, problem=True, name="Очень длинное название лота, которое не влезет")]
    text, markup = dw.build_list(l10n, deals, 0, {"d1": "Gemini → Подписки"}, {"d1": "20.10.2026, 05:14"})
    assert "\n\n━" not in text  # нет пустой строки перед разделителем
    lines = text.splitlines()
    assert lines[0] == "⏳ <b>Сделки в работе: 2</b>" and lines[1].startswith("━")
    assert "1. <b>Лот 1</b>" in text and "📂 Gemini → Подписки" in text
    assert "🕒 20.10.2026, 05:14" in text and "· ⚠️ Спор" in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows[0] == ["dw:o:d1"] and rows[1] == ["dw:o:d2"]
    assert markup.inline_keyboard[1][0].text.startswith("2. ⚠️ ") and markup.inline_keyboard[1][0].text.endswith("…")
    assert rows[-1] == ["menu"]


def test_empty_list():
    text, _ = dw.build_list(make_fixer().l10n, [], 0)
    assert "Всё подтверждено" in text


def test_card_rows():
    l10n = make_fixer().l10n
    text, markup = dw.build_card(l10n, deal(1), section="S", date="D", chat_id="chat-1",
                                 sent=False, give_state="none")
    assert "\n\n━" not in text and "🆔 <code>chat-1</code>" in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows == [["dw:ok:d1", "dw:give:d1"], ["dw:back", "menu"]]
    # Спор после подтверждения: вместо «Подтвердить» — заглушка.
    _, markup = dw.build_card(l10n, deal(1, status="SENT", problem=True), section="S", date="D",
                              chat_id="c", sent=True, give_state="given")
    assert markup.inline_keyboard[0][0].callback_data == "dw:sent:d1"
    assert markup.inline_keyboard[0][1].text == "📦 Товар выдан"
    # Только что подтверждено — остаётся навигация.
    text, markup = dw.build_card(l10n, deal(1), section="S", date="D", chat_id="c", sent=True,
                                 give_state="none", done=True)
    assert text.startswith("✅ <b>Выдача подтверждена</b>")
    assert [[b.callback_data for b in row] for row in markup.inline_keyboard] == [["dw:back", "menu"]]


# ----------------------------------------------------------------------
# Кнопки (на фейках)
# ----------------------------------------------------------------------

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


@pytest.fixture
def fixer(monkeypatch, tmp_path):
    monkeypatch.setattr(last_deals, "DATES_FILE", str(tmp_path / "dates.json"))
    f = make_fixer()
    f.deals_in_work = DealsInWork(order_file=None)
    f.account.get_my_items = lambda status, count: SimpleNamespace(items=[])
    return f


def test_confirm_button_sends_sent_and_removes_deal(fixer):
    calls = []
    fixer.account.update_deal = lambda deal_id, status: calls.append((deal_id, status.name))
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dw:ok:d1")
    asyncio.run(dw.cb_confirm(query, fixer))
    assert calls == [("d1", "SENT")]
    assert fixer.deals_in_work.count == 0
    assert query.answers[-1] == ("✅ Выдача подтверждена.", True)
    assert query.message.edits[-1][0].startswith("✅ <b>Выдача подтверждена</b>")


def test_new_deal_button_also_updates_counter(fixer):
    from fixer.tg.handlers import deal_actions
    fixer.account.update_deal = lambda deal_id, status: None
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dl:ok:d1")
    query.message = None  # сворачивать нечего
    asyncio.run(deal_actions.cb_confirm(query, fixer))
    assert fixer.deals_in_work.count == 0


def test_give_stub_when_no_stock(fixer):
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dw:give:d1")
    asyncio.run(dw.cb_give(query, fixer))
    assert query.answers == [("📦 Автовыдача для этого лота не настроена.", True)]
    assert fixer.account.sent_messages == []


def _with_stock(fixer, tmp_path, stock="KEY-1\nKEY-2\n"):
    from fixer.settings import AutoDeliveryLot
    path = tmp_path / "stock.txt"
    path.write_text(stock, encoding="utf-8")
    fixer.autodelivery_config.lots["Лот 1"] = AutoDeliveryLot(stock_file=str(path))
    fixer.autodelivery_manager = AutoDeliveryManager(
        config={"Лот 1": str(path)}, delivery_text_template="Ваш товар: {item}",
        ledger_path=str(tmp_path / "ledger.db"),
    )
    return path


def test_give_from_stock_once_even_with_autodelivery_off(fixer, tmp_path):
    fixer.settings.modules.autodelivery = False
    path = _with_stock(fixer, tmp_path)
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dw:give:d1")
    asyncio.run(dw.cb_give(query, fixer))
    assert fixer.account.sent_messages == [("chat-1", "Ваш товар: KEY-1")]
    assert query.answers[0] == ("📦 Товар отправлен покупателю в чат сделки.", True)
    assert path.read_text(encoding="utf-8").strip() == "KEY-2"
    # Повторно — уже выдано, второй ключ не уходит; кнопка подписана «Товар выдан».
    query = FakeQuery("dw:give:d1")
    asyncio.run(dw.cb_give(query, fixer))
    assert query.answers == [("📦 Товар по этой сделке уже выдан.", True)]
    assert len(fixer.account.sent_messages) == 1
    # Выдачу не подтверждает: сделка в работе.
    assert fixer.deals_in_work.count == 1


def test_give_failure_returns_item_to_stock(fixer, tmp_path):
    path = _with_stock(fixer, tmp_path, "KEY-1\n")

    def boom(chat_id, text=None, **_):
        raise RuntimeError("нет связи")

    fixer.account.send_message = boom
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dw:give:d1")
    asyncio.run(dw.cb_give(query, fixer))
    assert query.answers[0][0].startswith("❌ Товар не отправлен: нет связи")
    assert path.read_text(encoding="utf-8").strip() == "KEY-1"
    assert dw.give_state(fixer, deal(1)) == "ready"


def test_empty_stock_stub(fixer, tmp_path):
    _with_stock(fixer, tmp_path, "")
    fixer.deals_in_work.observe(deal(1))
    query = FakeQuery("dw:give:d1")
    asyncio.run(dw.cb_give(query, fixer))
    assert query.answers == [("📦 Склад этого лота пуст.", True)]


def test_gone_deal_shows_list(fixer):
    query = FakeQuery("dw:o:d9")
    asyncio.run(dw.cb_open(query, fixer))
    assert query.answers[0] == ("Этой сделки уже нет в работе.", True)
    assert query.message.edits and "Сделки в работе: 0" in query.message.edits[-1][0]
