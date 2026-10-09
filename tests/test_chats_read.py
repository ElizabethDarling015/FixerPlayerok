"""Кнопка «Прочитано» в разделе чатов: алерт при быстром ответе Playerok,
обновляемое уведомление при медленном (всё на моках, без сети)."""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from fixer.localization import L10n
from fixer.tg.handlers import chats


class FakeNote:
    def __init__(self, text, reply_markup):
        self.text = text
        self.reply_markup = reply_markup
        self.edits: list[str] = []

    async def edit_text(self, text, reply_markup=None):
        self.edits.append(text)


class FakeMessage:
    def __init__(self):
        self.sent: list[FakeNote] = []

    async def answer(self, text, reply_markup=None):
        note = FakeNote(text, reply_markup)
        self.sent.append(note)
        return note


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()
        self.answers: list[tuple[tuple, dict]] = []

    async def answer(self, *args, **kwargs):
        self.answers.append((args, kwargs))


def make_fixer(delay: float, fail: bool = False):
    def mark(chat_id):
        time.sleep(delay)
        if fail:
            raise RuntimeError("boom")

    return SimpleNamespace(account=SimpleNamespace(mark_chat_as_read=mark), l10n=L10n("ru"))


async def _wait_background():
    while chats._background_tasks:
        await asyncio.gather(*list(chats._background_tasks))


@pytest.fixture(autouse=True)
def short_timeout(monkeypatch):
    monkeypatch.setattr(chats, "READ_SOFT_TIMEOUT", 0.2)


async def test_fast_success_shows_alert():
    q = FakeQuery("chat:read:c1")
    await chats.cb_chat_read(q, make_fixer(0))
    assert q.answers == [(("✅ Чат отмечен прочитанным.",), {"show_alert": True})]
    assert q.message.sent == []


async def test_fast_failure_shows_alert():
    q = FakeQuery("chat:read:c1")
    await chats.cb_chat_read(q, make_fixer(0, fail=True))
    (args, kwargs), = q.answers
    assert args[0].startswith("⚠️ Не удалось") and kwargs == {"show_alert": True}
    assert q.message.sent == []


async def test_slow_success_updates_same_note():
    q = FakeQuery("chat:read:c1")
    await chats.cb_chat_read(q, make_fixer(0.5))
    assert q.answers == [((), {})]          # «часики» сняты без алерта
    note, = q.message.sent
    assert note.text.startswith("⚠️ Playerok не ответил вовремя")
    assert note.reply_markup.inline_keyboard[0][0].callback_data == "close"
    await _wait_background()
    assert len(note.edits) == 1
    first, second = note.edits[0].split("\n")
    assert first == note.text
    assert second.startswith("✅ Ответил, время выполнения")


async def test_slow_failure_updates_same_note():
    q = FakeQuery("chat:read:c1")
    await chats.cb_chat_read(q, make_fixer(0.5, fail=True))
    note, = q.message.sent
    await _wait_background()
    assert note.edits[0].split("\n")[1].startswith("❌ Не удалось")
