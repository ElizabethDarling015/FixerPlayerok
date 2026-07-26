"""Тесты вахдога сессии Runner: `SessionExpiredEvent` при смерти сессии (без сети и потоков)."""
from types import SimpleNamespace

import pytest

from conftest import FakeAccount, drain_events

from playerokapi.common.exceptions import RequestFailedError, RequestPlayerokError, UnauthorizedError
from playerokapi.updater import events
from playerokapi.updater.runner import Runner


def make_runner(account=None):
    return Runner(account or FakeAccount())


def make_failed_response(status_code):
    """Лёгкий объект «ответа» для RequestFailedError (нужны только status_code/text/url)."""
    return SimpleNamespace(status_code=status_code, text="", url="https://playerok.com/graphql")


def make_graphql_error(code, message="нет доступа"):
    """Лёгкий объект «ответа» для RequestPlayerokError с GraphQL-кодом ошибки."""
    return SimpleNamespace(
        json=lambda: {"errors": [{"extensions": {"code": code}, "message": message}]},
        url="https://playerok.com/graphql",
    )


def session_expired_events(runner):
    return [e for e in drain_events(runner) if isinstance(e, events.SessionExpiredEvent)]


def fail_get_with(account, exc):
    def failing_get():
        raise exc
    account.get = failing_get


def test_unauthorized_emits_event_once():
    account = FakeAccount()
    runner = make_runner(account)
    fail_get_with(account, UnauthorizedError("HTTP 401"))

    runner._poll_once()
    emitted = session_expired_events(runner)
    assert len(emitted) == 1
    assert emitted[0].cause == "HTTP 401"

    # Повторные опросы той же мёртвой сессии не спамят событиями.
    runner._poll_once()
    runner._poll_once()
    assert session_expired_events(runner) == []


def test_new_event_after_recovery_and_new_death():
    account = FakeAccount()
    runner = make_runner(account)
    fail_get_with(account, UnauthorizedError("HTTP 401"))
    runner._poll_once()
    assert len(session_expired_events(runner)) == 1

    # Сессия ожила (например, cookies заменили): успешный опрос сбрасывает флаг и счётчики.
    account.get = lambda: account
    runner._poll_once()
    assert runner.last_success_at is not None
    assert runner._session_fail_streak == 0

    # Новая смерть — новое событие.
    fail_get_with(account, UnauthorizedError("HTTP 403"))
    runner._poll_once()
    emitted = session_expired_events(runner)
    assert len(emitted) == 1 and emitted[0].cause == "HTTP 403"


def test_forbidden_streak_needs_three_in_a_row():
    account = FakeAccount()
    runner = make_runner(account)
    fail_get_with(account, RequestFailedError(make_failed_response(403)))

    runner._poll_once()
    runner._poll_once()
    assert session_expired_events(runner) == []  # два подряд — ещё не смерть

    runner._poll_once()
    emitted = session_expired_events(runner)
    assert len(emitted) == 1
    assert emitted[0].cause == "HTTP 403"


def test_success_resets_suspicious_streak():
    account = FakeAccount()
    runner = make_runner(account)
    error = RequestPlayerokError(make_graphql_error("UNAUTHENTICATED"))

    fail_get_with(account, error)
    runner._poll_once()
    runner._poll_once()

    # Успешный опрос между «подозрительными» ошибками обнуляет серию.
    account.get = lambda: account
    runner._poll_once()

    fail_get_with(account, error)
    runner._poll_once()
    runner._poll_once()
    assert session_expired_events(runner) == []

    runner._poll_once()  # третья подряд после сброса
    assert len(session_expired_events(runner)) == 1


def test_ordinary_errors_do_not_trigger_watchdog():
    account = FakeAccount()
    runner = make_runner(account)

    for exc in (RuntimeError("сеть моргнула"), RequestFailedError(make_failed_response(500))):
        fail_get_with(account, exc)
        for _ in range(5):
            runner._poll_once()
    assert session_expired_events(runner) == []
    # Неуспешные циклы не двигают last_success_at.
    assert runner.last_success_at is None


def test_last_success_at_updated_after_successful_poll():
    account = FakeAccount()
    runner = make_runner(account)
    assert runner.last_success_at is None
    runner._poll_once()
    first = runner.last_success_at
    assert first is not None
    runner._poll_once()
    assert runner.last_success_at >= first


def test_watchdog_does_not_break_ignore_exceptions_false():
    account = FakeAccount()
    runner = make_runner(account)
    runner._ignore_exceptions = False
    fail_get_with(account, UnauthorizedError("HTTP 401"))

    # Исключение по-прежнему пробрасывается наружу, но событие уже в очереди.
    with pytest.raises(UnauthorizedError):
        runner._poll_once()
    assert len(session_expired_events(runner)) == 1
