"""Клиент Playerok для лотов: формат как у сайта (HAR 12.10.2026)."""
from unittest.mock import MagicMock

from playerokapi import parser
from playerokapi.account import Account
from playerokapi.common.enums import ItemStatuses


def make_account():
    account = Account(cookies="token=x", max_requests_retries=1, backoff_factor=0)
    account._query = MagicMock(return_value={})
    return account


def test_publish_and_raise_use_site_input_format():
    account = make_account()
    account.publish_item("item-1", "prio-1", keep_in_sale=True)
    name, variables = account._query.call_args.args
    assert name == "publishItem"
    assert variables["input"] == {"itemId": "item-1", "priorityStatuses": ["prio-1"],
                                  "transactionProviderId": "LOCAL",
                                  "transactionProviderData": {"paymentMethodId": None}, "keepInSale": True}
    account.increase_item_priority_status("item-1", "prio-2")
    name, variables = account._query.call_args.args
    assert name == "increaseItemPriorityStatus" and variables["showForbiddenImage"] is True
    assert variables["input"]["priorityStatuses"] == ["prio-2"] and "keepInSale" not in variables["input"]


def test_update_item_keep_in_sale():
    account = make_account()
    account.update_item("item-1", keep_in_sale=False)
    assert account._query.call_args.args[1]["input"] == {"id": "item-1", "keepInSale": False}


def test_discontinue_and_republish_post_to_rest_api():
    account = make_account()
    calls = []

    def fake_request(method, url=None, payload=None, idempotent=True, **_):
        calls.append((method, url, payload, idempotent))
        response = MagicMock()
        response.json.return_value = {"success": True, "status": "DISCONTINUED"}
        return response

    account.request = fake_request
    assert account.discontinue_item("abc")["status"] == "DISCONTINUED"
    account.republish_item("abc")
    assert calls == [
        ("post", "https://playerok.com/rest-api/public/item/abc/discontinue", None, False),
        ("post", "https://playerok.com/rest-api/public/item/abc/republish", None, False),
    ]


def test_list_and_card_fields_are_parsed():
    profile = parser.item_profile({
        "id": "i1", "name": "PhpStorm", "status": "DISCONTINUED", "keepInSale": True,
        "statusExpirationDate": "2026-11-08T05:29:00.418Z", "dealsCounter": 4,
        "game": {"id": "g", "name": "JetBrains"}, "category": {"id": "c", "name": "Другое"},
    })
    assert profile.status is ItemStatuses.DISCONTINUED and profile.keep_in_sale is True
    assert profile.game.name == "JetBrains" and profile.category.name == "Другое" and profile.deals_counter == 4
    card = parser.my_item({"id": "i1", "keepInSale": False, "pauseAvailable": True, "republishAvailable": False,
                           "keepInSaleAvailable": True})
    assert card.keep_in_sale is False and card.pause_available is True and card.republish_available is False
