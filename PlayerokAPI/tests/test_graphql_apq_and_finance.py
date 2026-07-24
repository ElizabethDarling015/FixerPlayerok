"""Тесты APQ-фолбэка и новых seller/finance методов Account."""
from unittest.mock import MagicMock

import pytest

from playerokapi.account import Account
from playerokapi.common.exceptions import PersistedQueryNotFoundError
from playerokapi import parser


class FakeResponse:
    status_code = 200
    url = "https://playerok.com/graphql"
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def make_account():
    return Account(cookies="token=x", max_requests_retries=1, backoff_factor=0)


def test_apq_fallback_posts_full_text_on_persisted_query_not_found():
    account = make_account()
    calls = []

    def fake_request(method, url="https://playerok.com/graphql", headers=None, payload=None,
                     files=None, idempotent=True):
        calls.append((method, payload, idempotent))
        if method == "get":
            response = FakeResponse({
                "errors": [{"message": "PersistedQueryNotFound",
                            "extensions": {"code": "PERSISTED_QUERY_NOT_FOUND"}}],
            })
            raise PersistedQueryNotFoundError(response, "viewerBalance")
        return FakeResponse({"data": {"viewerBalance": {"value": 10, "available": 10,
                                                          "frozen": 0, "withdrawable": 10,
                                                          "pendingIncome": 0}}})

    account.request = fake_request
    data = account._persisted_query("viewerBalance", {})
    assert data["viewerBalance"]["value"] == 10
    assert calls[0][0] == "get"
    assert calls[1][0] == "post"
    assert "query" in calls[1][1]
    assert calls[1][1]["extensions"]["persistedQuery"]["version"] == 1
    assert calls[1][2] is True  # idempotent


def test_remove_item_passes_show_forbidden_image():
    account = make_account()
    account._query = MagicMock(return_value={"removeItem": {"id": "i1", "status": "DRAFT"}})
    assert account.remove_item("i1") is True
    assert account._query.call_args.args == ("removeItem", {"id": "i1", "showForbiddenImage": True})


def test_update_deal_passes_show_forbidden_image():
    account = make_account()
    account._query = MagicMock(return_value={"updateDeal": {"id": "d1", "status": "CONFIRMED"}})
    account.update_deal("d1", "CONFIRMED")
    assert account._query.call_args.args[1]["showForbiddenImage"] is True


def test_increase_priority_passes_show_forbidden_image():
    account = make_account()
    account._query = MagicMock(return_value={"increaseItemPriorityStatus": None})
    account.increase_item_priority_status("i1", "prio-1")
    assert account._query.call_args.args[1]["showForbiddenImage"] is True


def test_create_deal_parses_transaction():
    account = make_account()
    account._query = MagicMock(return_value={
        "createDeal": {
            "id": "tx-1", "operation": "BUY", "direction": "OUT", "providerId": "LOCAL",
            "status": "PENDING", "value": 100, "fee": 5, "createdAt": "2026-01-01",
        },
    })
    tx = account.create_deal("item-1")
    assert tx is not None
    assert tx.id == "tx-1"
    assert tx.value == 100
    assert account._query.call_args.args[0] == "createDeal"


def test_count_deals_and_chats():
    account = make_account()
    account._query = MagicMock(side_effect=[
        {"countDeals": 7},
        {"countChats": 3},
    ])
    assert account.count_deals({"userId": "u1"}) == 7
    assert account.count_chats() == 3


def test_finance_methods_shapes():
    account = make_account()
    account._query = MagicMock(return_value={
        "transactions": {"edges": [{"node": {"id": "tx-1", "value": 50, "status": "CONFIRMED"}}],
                         "pageInfo": {}, "totalCount": 1},
    })
    page = account.get_transactions(count=5)
    assert page is not None
    assert page.transactions[0].id == "tx-1"
    assert account._query.call_args.args[0] == "transactions"
    assert account._query.call_args.args[1]["hasSupportAccess"] is False

    account._query = MagicMock(return_value={"createPaymentURL": "https://pay.example/1"})
    assert account.create_payment_url(100, "SBP") == "https://pay.example/1"

    account._query = MagicMock(return_value={"setChosenCard": True})
    assert account.set_chosen_card("card-1") is True


def test_verified_card_and_viewer_profile():
    profile = parser.account_profile({
        "id": "u1",
        "username": "seller",
        "chosenVerifiedCard": {
            "id": "card-1", "cardFirstSix": "220220", "cardLastFour": "1234",
            "cardType": "MIR", "isChosen": True,
        },
        "balance": {"value": 1},
    })
    assert profile.chosen_verified_card is not None
    assert profile.chosen_verified_card.card_last_four == "1234"


def test_my_item_extra_fields():
    item = parser.my_item({
        "id": "i1", "name": "Лот", "dealsCounter": 3, "mayBePublished": True,
        "isAutomated": False, "multiple": True, "postModerationCheckedAt": "2026-01-02",
    })
    assert item.deals_counter == 3
    assert item.may_be_published is True
    assert item.multiple is True


def test_query_texts_cover_all_persisted():
    from playerokapi.graphql_queries import PERSISTED_QUERIES, QUERY_TEXTS, QUERIES
    assert set(QUERY_TEXTS) == set(PERSISTED_QUERIES)
    assert "chosenVerifiedCard" in QUERIES["viewer"]
    assert "createDeal" in QUERIES
    assert "requestWithdrawal" in QUERIES
    assert "itemUpdated" in QUERIES
