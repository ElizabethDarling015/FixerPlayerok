"""Связь с Playerok: фоновое подключение после неудачного старта и уведомления об обрыве."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from fixer import playerok_link
from fixer.playerok_link import PlayerokLink
from fixer.tg.notifications import Notifier, playerok_lost_keyboard, playerok_unavailable_keyboard
from fixer_helpers import make_fixer


class FakeBot:
    """Записывает отправку и правку; `missing` — сообщения, которые «закрыл» админ."""

    def __init__(self):
        self.sent, self.edited, self.missing = [], [], set()
        self._id = 100

    async def send_message(self, chat_id, text, reply_markup=None, **_):
        self._id += 1
        self.sent.append((chat_id, text, reply_markup))
        return SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=self._id)

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
        if (chat_id, message_id) in self.missing:
            raise RuntimeError("message to edit not found")
        self.edited.append((chat_id, message_id, text, reply_markup))


def _callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def make_link_fixer(tmp_path, monkeypatch, results):
    """Fixer-заглушка: `connect_playerok` по очереди отдаёт `results` (True/False/"hang")."""
    monkeypatch.chdir(tmp_path)
    fixer = make_fixer()
    fixer.playerok_connected = False
    fixer._playerok_connected = False
    bot = FakeBot()
    fixer.notifier = Notifier(fixer, bot, SimpleNamespace(all_ids=[1]))
    fixer.attempts = 0
    fixer.spawn = lambda coro: asyncio.get_running_loop().create_task(coro)

    async def connect_playerok(attempts=3):
        assert attempts == 1
        fixer.attempts += 1
        result = results.pop(0) if results else True
        if result == "hang":
            await asyncio.sleep(3600)
        if result:
            fixer.playerok_connected = True
            fixer.link.on_connected()
        return {"ok": bool(result), "message": "" if result else "timeout"}

    fixer.connect_playerok = connect_playerok
    fixer.link = PlayerokLink(fixer)
    return fixer, bot


@pytest.fixture
def fast_delays(monkeypatch):
    monkeypatch.setattr(playerok_link, "RECONNECT_DELAYS", (0.01, 0.02, 0.03, 0.05))


def test_schedule_and_thresholds():
    assert playerok_link.RECONNECT_DELAYS == (30, 60, 120, 300)  # дальше — каждые 5 минут
    assert playerok_link.LOST_AFTER == 180


def test_keyboards():
    l10n = make_fixer().l10n
    assert _callbacks(playerok_unavailable_keyboard(l10n)) == ["plk:retry", "close"]
    assert _callbacks(playerok_lost_keyboard(l10n)) == ["plk:logs", "close"]


async def test_reconnect_until_success_then_message_becomes_connected(tmp_path, monkeypatch, fast_delays):
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, [False, False, True])
    fixer.link.start_reconnect("curl: (28) timeout")
    await asyncio.wait_for(fixer.link._loop_task, 2)

    assert fixer.attempts == 3
    (chat, text, markup), = bot.sent
    assert "Playerok недоступен" in text and "curl: (28) timeout" in text
    assert _callbacks(markup) == ["plk:retry", "close"]
    (_, message_id, new_text, new_markup), = bot.edited
    assert message_id == 101 and "Успешное подключение" in new_text
    assert _callbacks(new_markup) == ["close"]


async def test_closed_alert_gets_new_success_message(tmp_path, monkeypatch, fast_delays):
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, [False, True])
    bot.missing.add((1, 101))  # админ нажал «❌ Закрыть»
    fixer.link.start_reconnect("x")
    await asyncio.wait_for(fixer.link._loop_task, 2)
    assert len(bot.sent) == 2 and "Успешное подключение" in bot.sent[1][1]
    assert _callbacks(bot.sent[1][2]) == ["close"]


async def test_retry_interrupts_hanging_attempt(tmp_path, monkeypatch, fast_delays):
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, ["hang", True])
    fixer.account = object()
    fixer.link.start_reconnect("x")
    await asyncio.sleep(0.05)
    assert fixer.attempts == 1 and fixer.link._attempt_task is not None

    assert fixer.link.retry_now((1, 101)) == "retry"
    await asyncio.wait_for(fixer.link._loop_task, 2)
    assert fixer.attempts == 2
    assert fixer.account is None  # новая попытка — с новым Account
    assert len(bot.edited) == 1


async def test_retry_skips_pause(tmp_path, monkeypatch):
    monkeypatch.setattr(playerok_link, "RECONNECT_DELAYS", (3600,))
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, [False, True])
    fixer.link.start_reconnect("x")
    await asyncio.sleep(0.05)
    assert fixer.attempts == 1  # ждёт час
    fixer.link.retry_now()
    await asyncio.wait_for(fixer.link._loop_task, 2)
    assert fixer.attempts == 2


async def test_shutdown_cancels_loop(tmp_path, monkeypatch, fast_delays):
    fixer, _ = make_link_fixer(tmp_path, monkeypatch, ["hang"])
    fixer.link.start_reconnect("x")
    await asyncio.sleep(0.05)
    fixer.link._loop_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await fixer.link._loop_task


async def test_retry_when_connected(tmp_path, monkeypatch):
    fixer, _ = make_link_fixer(tmp_path, monkeypatch, [])
    fixer.playerok_connected = True
    assert fixer.link.retry_now((1, 5)) == "connected"


async def test_lost_after_three_minutes_and_restored(tmp_path, monkeypatch):
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, [])
    fixer.playerok_connected = True
    account = SimpleNamespace(last_response_at=1000.0, last_network_error_at=None)
    fixer.account = account
    link = fixer.link

    await link.check(now=1500)  # тишина без ошибок — не обрыв
    account.last_network_error_at = 1100.0
    await link.check(now=1170)  # ошибки, но меньше 3 минут
    assert not bot.sent

    await link.check(now=1181)
    (_, text, markup), = bot.sent
    assert "Потеряна связь" in text and _callbacks(markup) == ["plk:logs", "close"]
    await link.check(now=1300)  # повторно не шлём
    assert len(bot.sent) == 1

    account.last_response_at = 1310.0
    await link.check(now=1320)
    (_, _, new_text, new_markup), = bot.edited
    assert "восстановлена" in new_text and _callbacks(new_markup) == ["close"]


async def test_disconnected_is_not_lost(tmp_path, monkeypatch):
    fixer, bot = make_link_fixer(tmp_path, monkeypatch, [])
    fixer.account = SimpleNamespace(last_response_at=0.0, last_network_error_at=10.0)
    await fixer.link.check(now=10_000)
    assert not bot.sent


# ----------------------------------------------------------------------
# Старт: обычный запуск без Playerok не падает, --offline не предупреждает
# ----------------------------------------------------------------------

class DeadAccount:
    def __init__(self, **_):
        self.username = None
        self.profile = None

    def get(self):
        from playerokapi.common.exceptions import RequestSendingError
        raise RequestSendingError("https://playerok.com/graphql", "curl: (28) timeout")


async def _run_fixer(tmp_path, monkeypatch, offline):
    monkeypatch.chdir(tmp_path)
    from fixer import core
    from fixer_helpers import make_settings
    monkeypatch.setattr(core, "Account", DeadAccount)
    started = []
    monkeypatch.setattr(PlayerokLink, "start_reconnect",
                        lambda self, reason=None, notify=True: started.append(reason))
    fixer = core.Fixer(make_settings(), offline=offline)
    task = asyncio.create_task(fixer.run())
    await asyncio.sleep(0.3)
    assert not task.done(), task.exception() if task.done() else None
    fixer.request_shutdown()
    await asyncio.wait_for(task, 5)
    return fixer, started


async def test_start_without_playerok_keeps_running(tmp_path, monkeypatch):
    fixer, started = await _run_fixer(tmp_path, monkeypatch, offline=False)
    assert started and "timeout" in started[0]
    assert not fixer.playerok_connected and fixer.account is None


async def test_offline_start_does_not_warn(tmp_path, monkeypatch):
    _, started = await _run_fixer(tmp_path, monkeypatch, offline=True)
    assert started == []
