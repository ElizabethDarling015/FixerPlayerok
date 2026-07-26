"""
Тесты «человечности» бота: задержки перед автоответами (`cardinal.modules.humanize`),
секция `[humanize]` в настройках и джиттер интервалов поллинга (`playerokapi.updater.runner`).
"""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from cardinal.modules.autoresponse import AutoResponseModule
from cardinal.modules.greeting import GreetingModule
from cardinal.modules.humanize import FULL_DELAY_TEXT_LENGTH, compute_reply_delay, sleep_before_reply
from cardinal.settings import HumanizeSettings
from playerokapi.updater.events import NewMessageEvent
from playerokapi.updater.runner import _JITTER, _jittered

from cardinal_helpers import make_cardinal, make_chat, make_chat_message


def make_humanize(delay_min: float, delay_max: float) -> HumanizeSettings:
    return HumanizeSettings(reply_delay_min=delay_min, reply_delay_max=delay_max)


# ----------------------------------------------------------------------
# compute_reply_delay: границы, рост с длиной текста, выключение
# ----------------------------------------------------------------------

def test_delay_respects_bounds():
    settings = make_humanize(2.0, 8.0)
    for text in ("", "хай", "т" * 100, "т" * 1000):
        for _ in range(200):
            delay = compute_reply_delay(settings, text)
            assert 2.0 <= delay <= 8.0


def test_delay_grows_with_text_length(monkeypatch):
    # Случайность фиксируем на середине диапазона uniform — остаётся чистая опорная точка.
    monkeypatch.setattr("cardinal.modules.humanize.random",
                        SimpleNamespace(uniform=lambda a, b: (a + b) / 2))
    settings = make_humanize(2.0, 8.0)
    short = compute_reply_delay(settings, "ок")
    medium = compute_reply_delay(settings, "т" * (FULL_DELAY_TEXT_LENGTH // 2))
    long = compute_reply_delay(settings, "т" * FULL_DELAY_TEXT_LENGTH)
    longer = compute_reply_delay(settings, "т" * (FULL_DELAY_TEXT_LENGTH * 10))
    assert short < medium < long
    assert long == longer == 8.0  # длина за пределами лимита — clamp к max
    assert short == pytest.approx(2.0 + 6.0 * (2 / FULL_DELAY_TEXT_LENGTH))


def test_delay_zero_when_disabled():
    settings = make_humanize(0.0, 0.0)
    for text in ("", "привет", "т" * 500):
        assert compute_reply_delay(settings, text) == 0.0


def test_delay_zero_without_settings():
    assert compute_reply_delay(None, "привет") == 0.0


def test_delay_equal_min_max_is_constant():
    settings = make_humanize(3.0, 3.0)
    for _ in range(50):
        assert compute_reply_delay(settings, "т" * 100) == 3.0


def test_delay_handles_none_text():
    settings = make_humanize(2.0, 8.0)
    assert 2.0 <= compute_reply_delay(settings, None) <= 8.0


# ----------------------------------------------------------------------
# Валидация секции [humanize]
# ----------------------------------------------------------------------

def test_humanize_settings_defaults():
    settings = HumanizeSettings()
    assert settings.reply_delay_min == 2.0
    assert settings.reply_delay_max == 8.0


def test_humanize_settings_rejects_max_less_than_min():
    with pytest.raises(ValidationError):
        HumanizeSettings(reply_delay_min=5.0, reply_delay_max=2.0)


def test_humanize_settings_rejects_negative():
    with pytest.raises(ValidationError):
        HumanizeSettings(reply_delay_min=-1.0, reply_delay_max=8.0)


# ----------------------------------------------------------------------
# sleep_before_reply: реальное ожидание через asyncio.sleep
# ----------------------------------------------------------------------

@pytest.fixture
def sleep_calls(monkeypatch):
    """Подменяет asyncio.sleep в модуле humanize, собирая запрошенные задержки."""
    calls: list[float] = []

    async def fake_sleep(delay):
        calls.append(delay)

    monkeypatch.setattr("cardinal.modules.humanize.asyncio.sleep", fake_sleep)
    return calls


async def test_sleep_before_reply_sleeps_within_bounds(sleep_calls):
    delay = await sleep_before_reply(make_humanize(2.0, 8.0), "привет")
    assert sleep_calls == [delay]
    assert 2.0 <= delay <= 8.0


async def test_sleep_before_reply_disabled_does_not_sleep(sleep_calls):
    delay = await sleep_before_reply(make_humanize(0.0, 0.0), "привет")
    assert delay == 0.0
    assert sleep_calls == []


# ----------------------------------------------------------------------
# Модули: автоответчик и приветствие реально ждут перед отправкой
# ----------------------------------------------------------------------

def set_humanize(cardinal, delay_min: float, delay_max: float) -> None:
    cardinal.settings.humanize.reply_delay_min = delay_min
    cardinal.settings.humanize.reply_delay_max = delay_max


async def test_autoresponse_waits_before_reply(sleep_calls):
    cardinal = make_cardinal()
    set_humanize(cardinal, 2.0, 8.0)
    cardinal.autoresponse_config.commands = {"!цена": "100 руб."}
    module = AutoResponseModule(cardinal)

    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("!цена")))

    assert cardinal.account.sent_messages == [("chat-1", "100 руб.")]
    assert len(sleep_calls) == 1 and 2.0 <= sleep_calls[0] <= 8.0


async def test_autoresponse_no_wait_when_disabled(sleep_calls):
    cardinal = make_cardinal()
    set_humanize(cardinal, 0.0, 0.0)
    cardinal.autoresponse_config.commands = {"!цена": "100 руб."}
    module = AutoResponseModule(cardinal)

    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("!цена")))

    assert len(cardinal.account.sent_messages) == 1
    assert sleep_calls == []


async def test_greeting_waits_before_reply(tmp_path, sleep_calls):
    cardinal = make_cardinal()
    cardinal.settings.modules.greeting = True
    set_humanize(cardinal, 2.0, 8.0)
    module = GreetingModule(cardinal, db_path=str(tmp_path / "greeting.sqlite3"))

    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("привет")))

    assert len(cardinal.account.sent_messages) == 1
    assert len(sleep_calls) == 1 and 2.0 <= sleep_calls[0] <= 8.0


async def test_greeting_no_wait_when_disabled(tmp_path, sleep_calls):
    cardinal = make_cardinal()
    cardinal.settings.modules.greeting = True
    set_humanize(cardinal, 0.0, 0.0)
    module = GreetingModule(cardinal, db_path=str(tmp_path / "greeting.sqlite3"))

    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("привет")))

    assert len(cardinal.account.sent_messages) == 1
    assert sleep_calls == []


# ----------------------------------------------------------------------
# Джиттер интервалов Runner
# ----------------------------------------------------------------------

def test_jittered_within_25_percent():
    for _ in range(500):
        value = _jittered(10.0)
        assert 10.0 * (1 - _JITTER) <= value <= 10.0 * (1 + _JITTER)


def test_jittered_is_not_constant():
    values = {round(_jittered(10.0), 6) for _ in range(50)}
    assert len(values) > 1  # интервалы не должны быть идеально ровными
