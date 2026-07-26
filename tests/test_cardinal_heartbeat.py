"""Тесты вахтёра опроса Playerok (`Cardinal.check_poll_health`) — чистая проверка, без сна."""
from types import SimpleNamespace

from cardinal.core import Cardinal
from cardinal.tg.notifications import Notifier

from cardinal_helpers import FakeTgBot, make_cardinal, make_settings


def make_core(poll_warn_minutes=10, last_success_at=None):
    settings = make_settings(playerok={"cookies": "token=abc; __ddg5_=x",
                                       "poll_warn_minutes": poll_warn_minutes})
    cardinal = Cardinal(settings)
    cardinal.runner = SimpleNamespace(last_success_at=last_success_at)
    cardinal._poll_watch_started_at = 0.0
    return cardinal


def test_warns_once_on_stall_and_reports_recovery():
    cardinal = make_core(poll_warn_minutes=10)

    # Успешных опросов ещё не было: отсчёт от старта вахтёра (0.0).
    assert cardinal.check_poll_health(now=9 * 60) is None
    assert cardinal.check_poll_health(now=10 * 60) == "stalled"
    # Повторно не предупреждает, пока опрос не восстановился.
    assert cardinal.check_poll_health(now=20 * 60) is None

    # Опрос ожил — одно сообщение о восстановлении и сброс флага.
    cardinal.runner.last_success_at = 21 * 60
    assert cardinal.check_poll_health(now=22 * 60) == "recovered"
    assert cardinal.check_poll_health(now=23 * 60) is None

    # Новый простой — новое предупреждение.
    assert cardinal.check_poll_health(now=31 * 60) == "stalled"


def test_counts_from_last_success():
    cardinal = make_core(poll_warn_minutes=5, last_success_at=100 * 60)
    assert cardinal.check_poll_health(now=104 * 60) is None
    assert cardinal.check_poll_health(now=105 * 60) == "stalled"


def test_zero_minutes_disables_watchdog():
    cardinal = make_core(poll_warn_minutes=0)
    assert cardinal.check_poll_health(now=10_000 * 60) is None


def test_no_runner_is_noop():
    cardinal = make_core(poll_warn_minutes=10)
    cardinal.runner = None
    assert cardinal.check_poll_health(now=100 * 60) is None


async def test_notify_poll_stalled_uses_errors_toggle():
    cardinal = make_cardinal()
    bot = FakeTgBot()
    notifier = Notifier(cardinal, bot, SimpleNamespace(all_ids={1}))

    await notifier.notify_poll_stalled(10)
    await notifier.notify_poll_recovered()
    assert len(bot.sent) == 2
    assert "10" in bot.sent[0][1]

    # Канал ошибок выключен — вахтёр молчит.
    cardinal.settings.notifications.errors = False
    await notifier.notify_poll_stalled(10)
    await notifier.notify_poll_recovered()
    assert len(bot.sent) == 2
