"""Регрессия: при ignore_exceptions=False ошибка фонового потока доходит до listen()."""
import pytest

from conftest import FakeAccount

from playerokapi.updater.runner import Runner


def test_background_error_reraised_from_listen():
    account = FakeAccount()
    runner = Runner(account)
    # Не ходим в сеть: WS-поток подменяем на no-op.
    runner._ws_loop = lambda: None

    def failing_poll():
        raise RuntimeError("boom in poll thread")

    runner._poll_once = failing_poll

    generator = runner.listen(requests_delay=0.05, ignore_exceptions=False)
    with pytest.raises(RuntimeError, match="boom in poll thread"):
        next(generator)
    # Runner остановлен после ошибки.
    assert runner._stop_event.is_set()


def test_background_error_swallowed_when_ignoring():
    account = FakeAccount()
    runner = Runner(account)

    calls = {"count": 0}

    def failing_poll():
        calls["count"] += 1
        raise RuntimeError("boom")

    runner._poll_once = failing_poll
    # ignore_exceptions=True (по умолчанию): _report_thread_error не завершает поток.
    assert runner._report_thread_error(RuntimeError("boom"), "тест") is False
    assert runner._event_queue.empty()

    runner._ignore_exceptions = False
    error = RuntimeError("boom-2")
    assert runner._report_thread_error(error, "тест") is True
    assert runner._event_queue.get_nowait() is error
