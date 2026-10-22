"""«⬆️ Автоподнятие»: окна день/ночь и лимиты, режим по позиции и по интервалу, экран, ввод."""
from __future__ import annotations

import asyncio
import datetime
import time
from types import SimpleNamespace as N

import pytest

from fixer import autoraise as ar
from fixer.settings import AutoRaiseSettings
from fixer.tg.handlers import autoraise as ui
from fixer_helpers import make_fixer

D = datetime.datetime


def cfg(**kw):
    return AutoRaiseSettings(**kw)


# ----------------------------------------------------------------------
# Время
# ----------------------------------------------------------------------

def test_night_window_crosses_midnight():
    c = cfg(night_enabled=True, night_from="23:00", night_to="08:00", day_limit=300, night_limit=100)
    assert ar.is_night(c, D(2026, 10, 22, 23, 30)) and ar.is_night(c, D(2026, 10, 23, 7, 59))
    assert not ar.is_night(c, D(2026, 10, 23, 8, 0))
    w = ar.current_window(c, D(2026, 10, 23, 2, 0))
    assert (w.kind, w.start, w.end, w.limit) == ("night", D(2026, 10, 22, 23, 0), D(2026, 10, 23, 8, 0), 100)
    w = ar.current_window(c, D(2026, 10, 23, 12, 0))
    assert (w.kind, w.start, w.end, w.limit) == ("day", D(2026, 10, 23, 8, 0), D(2026, 10, 23, 23, 0), 300)


def test_without_night_window_is_calendar_day():
    w = ar.current_window(cfg(day_limit=50), D(2026, 10, 23, 2, 0))
    assert (w.kind, w.start, w.limit) == ("all", D(2026, 10, 23, 0, 0), 50)


def test_night_values_replace_day_values():
    c = cfg(night_enabled=True, position=10, night_position=25, interval=3600, night_interval=14400)
    assert ar.target_position(c, D(2026, 10, 23, 1, 0)) == 25 and ar.target_position(c, D(2026, 10, 23, 12, 0)) == 10
    assert ar.current_interval(c, D(2026, 10, 23, 1, 0)) == 14400


def test_old_config_section_still_loads():
    c = AutoRaiseSettings.model_validate({"interval": 14400, "min_balance_reserve": 50})
    assert c.interval == 14400 and c.min_balance_reserve == 50 and c.mode == "position" and c.items == []


# ----------------------------------------------------------------------
# Поднятие (на фейковом аккаунте)
# ----------------------------------------------------------------------

class Account:
    def __init__(self, positions: dict, price=13, available=1000, premium=True):
        self.positions, self.price = positions, price
        self.raised: list[str] = []
        self.profile = N(balance=N(available=available))
        self.premium = premium

    def get_item(self, item_id):
        return N(id=item_id, name=f"Лот {item_id}", price=500, keep_in_sale=True,
                 status=N(name="APPROVED"), priority=N(name="PREMIUM" if self.premium else "DEFAULT"),
                 sequence=self.positions.get(item_id), priority_position=None)

    def get_item_priority_statuses(self, item_id, price):
        return [N(id="free", price=0, type=N(name="DEFAULT")), N(id="prem", price=self.price, type=N(name="PREMIUM"))]

    def get_balance(self):
        return self.profile.balance

    def increase_item_priority_status(self, item_id, status_id, keep_in_sale=None):
        assert status_id == "prem" and keep_in_sale is True
        self.raised.append(item_id)
        self.positions[item_id] = 1


class Notifier:
    def __init__(self):
        self.calls = []

    async def notify_item_raised(self, **kw):
        self.calls.append(("raised", kw))

    async def notify_raise_limit(self, **kw):
        self.calls.append(("limit", kw))

    async def notify_raise_no_balance(self, **kw):
        self.calls.append(("balance", kw))

    async def notify_error(self, text):
        self.calls.append(("error", text))


@pytest.fixture(autouse=True)
def no_gap(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)


def make(account, **settings):
    fixer = make_fixer()
    fixer.account = account
    fixer.notifier = Notifier()
    fixer.settings.modules.autoraise = True
    for key, value in settings.items():
        setattr(fixer.settings.autoraise, key, value)
    fixer.autoraise = ar.AutoRaise(fixer, state_file=None)
    return fixer


def run(coro):
    return asyncio.run(coro)


def test_position_mode_needs_streak_then_raises_and_notifies():
    acc = Account({"a": 14, "b": 3})
    fixer = make(acc, items=["a", "b"], position=10, streak=2, day_limit=300)
    s = fixer.autoraise
    run(s.check_positions())
    assert acc.raised == [] and s.state["positions"]["a"]["streak"] == 1
    run(s.check_positions())
    assert acc.raised == ["a"] and s.state["positions"]["a"]["pos"] == 1
    kind, kw = fixer.notifier.calls[0]
    assert kind == "raised" and kw["before"] == 14 and kw["spent"] == 13 and kw["total"] == 13 and kw["limit"] == 300


def test_streak_one_raises_immediately_and_cooldown_blocks_repeat():
    acc = Account({"a": 30})
    fixer = make(acc, items=["a"], position=10, streak=1, cooldown=600)
    run(fixer.autoraise.check_positions())
    acc.positions["a"] = 30  # снова упал
    run(fixer.autoraise.check_positions())
    assert acc.raised == ["a"]  # второй раз — кулдаун


def test_limit_stops_spending_and_notifies_once():
    acc = Account({"a": 30, "b": 30}, price=13)
    fixer = make(acc, items=["a", "b"], streak=1, cooldown=0, day_limit=20)
    run(fixer.autoraise.check_positions())
    assert acc.raised == ["a"]
    acc.positions["a"] = 30
    run(fixer.autoraise.check_positions())
    limits = [c for c in fixer.notifier.calls if c[0] == "limit"]
    assert acc.raised == ["a"] and len(limits) == 1 and limits[0][1]["spent"] == 13


def test_reserve_and_balance():
    acc = Account({"a": 30}, price=13, available=60)
    fixer = make(acc, items=["a"], streak=1, min_balance_reserve=50)
    run(fixer.autoraise.check_positions())
    assert acc.raised == [] and fixer.notifier.calls[0][0] == "balance"


def test_regular_item_never_raised():
    acc = Account({"a": 30}, premium=False)
    fixer = make(acc, items=["a"], streak=1)
    run(fixer.autoraise.check_positions())
    assert acc.raised == [] and fixer.autoraise.state["positions"]["a"]["note"] == "not_premium"


def test_interval_mode_counts_from_enabling():
    acc = Account({"a": 5, "b": 50})
    fixer = make(acc, items=["a", "b"], mode="interval", interval=3600)
    s = fixer.autoraise
    run(s.tick())
    assert acc.raised == [] and s.state["last_interval_run"]  # отсчёт начался, ничего не куплено
    s.state["last_interval_run"] = time.time() - 3601
    run(s.tick())
    assert acc.raised == ["a", "b"]


def test_disabled_or_no_items_does_nothing():
    acc = Account({"a": 30})
    fixer = make(acc, items=[], streak=1)
    run(fixer.autoraise.tick())
    fixer.settings.autoraise.items = ["a"]
    fixer.settings.modules.autoraise = False
    run(fixer.autoraise.tick())
    assert acc.raised == []


def test_state_survives_restart(tmp_path):
    acc = Account({"a": 30})
    fixer = make(acc, items=["a"], streak=1, day_limit=100)
    fixer.autoraise = ar.AutoRaise(fixer, state_file=str(tmp_path / "s.json"))
    run(fixer.autoraise.check_positions())
    again = ar.AutoRaise(fixer, state_file=str(tmp_path / "s.json"))
    assert again.spent_in(again.window()) == 13 and "a" in again.state["last_raised"]


# ----------------------------------------------------------------------
# Экран и ввод
# ----------------------------------------------------------------------

def test_screen_position_mode():
    acc = Account({"a": 14})
    fixer = make(acc, items=["a"], position=10, streak=2, day_limit=300)
    fixer.autoraise.state["positions"]["a"] = {"name": "GoLand навсегда", "pos": 14, "streak": 1}
    text, markup = ui.build_screen(fixer, D(2026, 10, 22, 12, 0))
    assert "\n\n━" not in text
    assert "держать в топ-<b>10</b>" in text and "GoLand навсегда — 14 место ⬆️ (1 из 2)" in text
    assert "лимит 300 ₽" in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows[0] == ["up:on", "up:mode"] and ["up:in:pos", "up:in:chk"] in rows
    assert ["up:in:cd", "up:streak"] in rows and rows[-1] == ["sys", "menu"]
    assert "up:in:nf" not in sum(rows, [])  # ночь выключена — её кнопок нет


def test_screen_interval_and_night_buttons():
    fixer = make(Account({}), items=[], mode="interval", night_enabled=True)
    text, markup = ui.build_screen(fixer, D(2026, 10, 22, 12, 0))
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert ["up:in:int"] in rows and ["up:in:nf", "up:in:nt"] in rows and ["up:in:nint", "up:in:nl"] in rows
    assert "up:in:pos" not in sum(rows, [])
    assert "Лоты не отмечены" in text


@pytest.mark.parametrize("key, raw, value, error", [
    ("pos", "12", 12, None),
    ("pos", "0", None, "up_err_range"),
    ("chk", "2", 120, None),
    ("cd", "0", 0, None),
    ("int", "90", 5400, None),
    ("dl", "300 ₽", 300, None),
    ("dl", "abc", None, "up_err_number"),
    ("nf", "23.30", "23:30", None),
    ("nt", "25:00", None, "up_err_time"),
])
def test_parse_value(key, raw, value, error):
    assert ui.parse_value(key, raw) == (value, error)


class FakeState:
    def __init__(self, data):
        self.data, self.cleared = dict(data), False

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.cleared = True
        self.data = {}


class Bot:
    def __init__(self):
        self.edits = []

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
        self.edits.append(text)


class Msg:
    def __init__(self, text):
        self.text, self.deleted, self.bot, self.chat = text, False, Bot(), N(id=1)

    async def delete(self):
        self.deleted = True


def test_input_saves_and_deletes_message(monkeypatch):
    saved = []
    monkeypatch.setattr(ui, "save_main_settings", lambda s: saved.append(s))
    fixer = make(Account({}), items=[])
    msg = Msg("15")
    state = FakeState({"field": "pos", "panel": [1, 5]})
    asyncio.run(ui.on_input(msg, state, fixer))
    assert msg.deleted and fixer.settings.autoraise.position == 15 and saved and state.cleared
    assert "топ-<b>15</b>" in msg.bot.edits[-1]


def test_bad_input_shows_error_and_keeps_waiting(monkeypatch):
    monkeypatch.setattr(ui, "save_main_settings", lambda s: pytest.fail("сохранять нечего"))
    fixer = make(Account({}), items=[])
    msg = Msg("сто")
    state = FakeState({"field": "pos", "panel": [1, 5]})
    asyncio.run(ui.on_input(msg, state, fixer))
    assert msg.deleted and not state.cleared and "⚠️ Нужно целое число." in msg.bot.edits[-1]


def test_lots_screen_only_active_premium_and_lost_marked():
    l10n = make_fixer().l10n
    lots = [("a", "Премиум A", True, True), ("b", "Обычный", False, True), ("c", "Снятый премиум", True, False)]
    text, markup = ui.build_lots_screen(l10n, lots, ["a", "c"], 0, {"c": "Снятый премиум"})
    buttons = [b.text for row in markup.inline_keyboard for b in row]
    assert "✅ Премиум A" in buttons and "✅ Снятый премиум ⚠️" in buttons
    assert not any("Обычный" in b for b in buttons) and "Обычных лотов не показано: 1" in text
