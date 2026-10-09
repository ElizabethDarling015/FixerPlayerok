"""Меню «Настройки → Тесты»: две страницы, у каждого настоящего уведомления есть образец,
каждая кнопка открывает образец без сырых {подстановок}."""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from fixer.tg.handlers import system
from fixer.tg.handlers.system import TEST_PAGES, build_tests_menu
from fixer_helpers import make_fixer

ROOT = Path(__file__).resolve().parents[1]
#: Вспомогательные куски шаблонов — сами по себе уведомлениями не являются.
HELPER_KEYS = {"notif_new_deal_autodelivery", "notif_place_deal_chat", "notif_system_lot", "notif_new_deal_short"}


def _callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def _handlers() -> dict[str, object]:
    source = (ROOT / "fixer/tg/handlers/system.py").read_text(encoding="utf-8")
    found = re.findall(r'@router\.callback_query\(F\.data == "(test:[a-z_]+)"\)\nasync def (\w+)', source)
    return {cb: getattr(system, name) for cb, name in found}


class FakeMessage:
    def __init__(self):
        self.edited, self.sent = [], []

    async def edit_text(self, text, reply_markup=None, **_):
        self.edited.append((text, reply_markup))

    async def answer(self, text, reply_markup=None, **_):
        self.sent.append((text, reply_markup))


class FakeQuery:
    def __init__(self, data):
        self.data, self.message, self.alerts = data, FakeMessage(), []

    async def answer(self, text=None, **_):
        self.alerts.append(text)


def test_two_pages_with_pager():
    fixer = make_fixer()
    assert len(TEST_PAGES) == 2
    _, first = build_tests_menu(fixer, 0)
    _, second = build_tests_menu(fixer, 1)
    assert "sys:tests:1" in _callbacks(first) and "1/2" in [b.text for r in first.inline_keyboard for b in r]
    assert "sys:tests:0" in _callbacks(second)
    page1 = {cb for _, cb in TEST_PAGES[0]}
    page2 = {cb for _, cb in TEST_PAGES[1]}
    assert page1.issubset(_callbacks(first)) and page2.issubset(_callbacks(second))
    assert not page1 & page2


def test_every_real_notification_has_a_sample():
    used = set(re.findall(r'"(notif_[a-z_]+)"', (ROOT / "fixer/tg/notifications.py").read_text(encoding="utf-8")))
    samples = (ROOT / "fixer/tg/handlers/system.py").read_text(encoding="utf-8")
    missing = {key for key in used - HELPER_KEYS if f'"{key}"' not in samples}
    # Эти два собираются функциями (build_started_text / build_new_deal_text) — у них свои образцы.
    missing -= {"notif_started", "notif_new_deal"}
    assert not missing, missing
    assert {"test:started", "test:new_deal"} <= set(_handlers())


def test_every_button_has_label_and_handler():
    fixer = make_fixer()
    handlers = _handlers()
    for page in TEST_PAGES:
        for key, cb in page:
            assert fixer.l10n(key) != key, key
            assert cb in handlers, cb


@pytest.mark.parametrize("callback", [cb for page in TEST_PAGES for _, cb in page if cb != "test:photo"])
async def test_sample_renders_and_back_returns_to_its_page(callback):
    fixer = make_fixer()
    query = FakeQuery(callback)
    await _handlers()[callback](query, fixer)
    shown = query.message.edited or query.message.sent
    assert shown, callback
    text, markup = shown[0]
    assert not re.search(r"\{[a-z_]+\}", text), text
    if query.message.edited:  # образец на месте меню — «Назад» ведёт на его страницу
        page = 1 if any(cb == callback for _, cb in TEST_PAGES[1]) else 0
        assert _callbacks(markup) == ["sys:tests:1" if page else "sys:tests"]
