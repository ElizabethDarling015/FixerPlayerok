"""Тесты retry-политики Account.request: GET повторяется, мутации — нет."""
from unittest.mock import MagicMock

import pytest

from playerokapi.account import Account
from playerokapi.common.exceptions import (
    NotInitiatedError,
    RequestSendingError,
    UnauthorizedError,
)


class FailingSession:
    """Фейковая curl_cffi-сессия: каждый запрос падает сетевой ошибкой."""

    def __init__(self):
        self.get_calls = 0
        self.post_calls = 0

    def get(self, url, **kwargs):
        self.get_calls += 1
        raise ConnectionError("network down")

    def post(self, url, **kwargs):
        self.post_calls += 1
        raise ConnectionError("network down")


class FakeResponse:
    status_code = 200
    url = "https://playerok.com/graphql"
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def make_account():
    # backoff_factor=0 — без задержек между попытками в тестах.
    return Account(cookies="token=x", max_requests_retries=3, backoff_factor=0)


def test_idempotent_get_is_retried():
    account = make_account()
    session = FailingSession()
    account._session = session

    with pytest.raises(RequestSendingError):
        account.request("get", payload={"operationName": "user"})

    assert session.get_calls == 3


def test_non_idempotent_post_is_not_retried():
    account = make_account()
    session = FailingSession()
    account._session = session

    with pytest.raises(RequestSendingError):
        account.request("post", payload={"operationName": "createChatMessage"}, idempotent=False)

    # Мутация после неоднозначной ошибки не повторяется — иначе возможен дубль.
    assert session.post_calls == 1


def test_query_sends_idempotent_false():
    account = make_account()
    account.request = MagicMock(return_value=FakeResponse({"data": {"markChatAsRead": None}}))

    account._query("markChatAsRead", {"input": {"chatId": "c1"}})

    assert account.request.call_args.kwargs.get("idempotent") is False


def test_get_uses_full_text_viewer_query():
    """get() авторизуется полнотекстовым запросом viewer (persisted `user` требует id/username)."""
    account = make_account()
    viewer = {"id": "u1", "username": "seller", "role": "USER",
              "balance": {"value": 100}, "profile": {"avatarURL": None}}
    account._query = MagicMock(return_value={"viewer": viewer})

    account.get()

    assert account._query.call_args.args[0] == "viewer"
    # Запрос на чтение — должен повторяться при сетевых сбоях.
    assert account._query.call_args.kwargs.get("idempotent") is True
    assert account.id == "u1"
    assert account.username == "seller"


def test_get_still_raises_unauthorized_on_empty_user():
    account = make_account()
    account._query = MagicMock(return_value={"user": None, "viewer": None})
    with pytest.raises(UnauthorizedError, match="токен просрочен"):
        account.get()


def test_unauthorized_error_shows_http_cause():
    """UnauthorizedError показывает исходную причину (иначе в логе только «проверьте cookies»)."""
    from playerokapi.common.exceptions import RequestFailedError

    account = make_account()
    response = FakeResponse({})
    response.status_code = 403
    response.text = "<html>DDoS-Guard</html>"

    def raise_failed(operation_name, variables, idempotent=False):
        raise RequestFailedError(response)

    account._query = raise_failed
    with pytest.raises(UnauthorizedError) as exc_info:
        account.get()
    text = str(exc_info.value)
    assert "HTTP 403" in text
    assert "DDoS-Guard" in text
    assert "прокси" in text  # подсказка про блокировку IP


def test_unauthorized_error_shows_graphql_cause():
    from playerokapi.common.exceptions import RequestPlayerokError

    account = make_account()
    response = FakeResponse({"errors": [{"extensions": {"code": "UNAUTHENTICATED"},
                                         "message": "Unauthorized access"}]})

    def raise_gql(operation_name, variables, idempotent=False):
        raise RequestPlayerokError(response)

    account._query = raise_gql
    with pytest.raises(UnauthorizedError, match="Unauthorized access"):
        account.get()


def test_uninitialized_account_guards():
    account = make_account()
    with pytest.raises(NotInitiatedError):
        account.get_chats()
    with pytest.raises(NotInitiatedError):
        account.get_my_items()
    with pytest.raises(NotInitiatedError):
        account.get_my_reviews()
