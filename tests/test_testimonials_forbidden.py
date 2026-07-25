"""Регрессия: testimonials FORBIDDEN не валит seller-бота."""
from unittest.mock import MagicMock

import pytest

from playerokapi.account import Account
from playerokapi.common.exceptions import RequestFailedError, RequestPlayerokError


class FakeResponse:
    url = "https://playerok.com/graphql?operationName=testimonials"

    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = __import__("json").dumps(payload)

    def json(self):
        return self._payload


def _forbidden_payload():
    return {
        "errors": [{
            "message": "У вас нет доступа на выполнение данной операции",
            "path": ["testimonials"],
            "extensions": {"code": "FORBIDDEN", "statusCode": 403},
        }],
        "data": None,
    }


def test_request_raises_playerok_error_on_http_403_graphql_forbidden():
    """Playerok отдаёт FORBIDDEN как HTTP 403 + JSON errors — это RequestPlayerokError, не RequestFailedError."""
    account = Account(cookies="token=x", max_requests_retries=1, backoff_factor=0)
    response = FakeResponse(403, _forbidden_payload())
    session = MagicMock()
    session.get.return_value = response
    account._session = session

    with pytest.raises(RequestPlayerokError) as exc_info:
        account.request("get", payload={"operationName": "testimonials", "variables": "{}"})
    assert exc_info.value.error_code == "FORBIDDEN"


def test_get_user_reviews_degrades_on_forbidden():
    account = Account(cookies="token=x")
    account.id = "user-1"

    def raise_forbidden(operation_name, variables):
        assert operation_name == "testimonials"
        response = FakeResponse(403, _forbidden_payload())
        raise RequestPlayerokError(response)

    account._persisted_query = raise_forbidden
    page = account.get_user_reviews("user-1", count=20)
    assert page is not None
    assert page.reviews == []
    assert page.total_count == 0
    assert account._testimonials_forbidden is True


def test_get_user_reviews_skips_api_after_forbidden():
    account = Account(cookies="token=x")
    account.id = "user-1"
    account._testimonials_forbidden = True
    account._persisted_query = MagicMock(side_effect=AssertionError("не должны ходить в API"))

    page = account.get_my_reviews(count=5)
    assert page.reviews == []
    account._persisted_query.assert_not_called()


def test_http_403_html_still_request_failed_error():
    """Антибот/HTML 403 остаётся RequestFailedError (не GraphQL)."""
    account = Account(cookies="token=x", max_requests_retries=1, backoff_factor=0)
    response = FakeResponse(403, {"not": "graphql"})
    response.text = "<html>DDoS-Guard</html>"
    response.json = MagicMock(side_effect=ValueError("not json"))
    session = MagicMock()
    session.get.return_value = response
    account._session = session

    with pytest.raises(RequestFailedError):
        account.request("get", payload={"operationName": "viewer", "variables": "{}"})
