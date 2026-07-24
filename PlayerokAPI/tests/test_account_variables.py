"""Тесты формы variables persisted-запросов (снята с реального трафика playerok.com)."""
from unittest.mock import MagicMock

from playerokapi.account import Account
from playerokapi.common.enums import ItemStatuses


def make_account():
    account = Account(cookies="token=x")
    account.id = "user-1"
    account._persisted_query = MagicMock(return_value={})
    return account


def test_user_chats_variables_include_user_filter():
    account = make_account()
    account.get_chats(count=10)

    operation, variables = account._persisted_query.call_args.args
    assert operation == "userChats"
    assert variables == {"pagination": {"first": 10}, "filter": {"userId": "user-1"},
                         "hasSupportAccess": False}


def test_deals_variables_include_required_filter():
    """deals: filter (ItemDealFilter!) обязателен — без него сервер отвечает 500."""
    account = make_account()
    account.get_deals(count=50)

    operation, variables = account._persisted_query.call_args.args
    assert operation == "deals"
    assert variables["filter"] == {"userId": "user-1"}
    assert variables["showForbiddenImage"] is True


def test_reviews_variables_include_has_support_access():
    account = make_account()
    account.get_user_reviews("user-1", count=20)

    operation, variables = account._persisted_query.call_args.args
    assert operation == "testimonials"
    assert variables["hasSupportAccess"] is False


def test_chat_messages_variables_shape():
    account = make_account()
    account.get_chat_messages("chat-1", count=10)

    operation, variables = account._persisted_query.call_args.args
    assert operation == "chatMessages"
    assert variables == {
        "pagination": {"first": 10},
        "filter": {"chatId": "chat-1"},
        "hasSupportAccess": False,
        "showForbiddenImage": True,
    }


def test_items_single_status_wrapped_into_list():
    account = make_account()
    account.get_items(user_id="user-1", status=ItemStatuses.APPROVED, count=16)

    operation, variables = account._persisted_query.call_args.args
    assert operation == "items"
    assert variables["filter"]["status"] == ["APPROVED"]
    assert variables["showForbiddenImage"] is True


def test_items_accepts_status_list_and_with_official():
    account = make_account()
    account.get_items(
        user_id="user-1",
        status=[ItemStatuses.APPROVED, ItemStatuses.PENDING_MODERATION, "PENDING_APPROVAL"],
        with_official=False,
    )

    _, variables = account._persisted_query.call_args.args
    assert variables["filter"]["status"] == ["APPROVED", "PENDING_MODERATION", "PENDING_APPROVAL"]
    assert variables["filter"]["withOfficial"] is False


def test_pagination_cursor_passed_through():
    account = make_account()
    account.get_chats(count=10, after_cursor="cursor-1")
    _, variables = account._persisted_query.call_args.args
    assert variables["pagination"] == {"first": 10, "after": "cursor-1"}
