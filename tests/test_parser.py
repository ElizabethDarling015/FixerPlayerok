"""Тесты парсера: account_profile, valueRangeLimit, ChatMessage.file, фильтрация None-узлов."""
from playerokapi import parser


def test_account_profile_reads_root_fields():
    data = {
        "id": "user-1",
        "username": "seller",
        "createdAt": "2024-01-01T00:00:00Z",
        "supportChatId": "support-1",
        "systemChatId": "system-1",
        "profile": {"avatarURL": "https://cdn/avatar.png", "testimonialCounter": 5},
    }
    profile = parser.account_profile(data)

    # Раньше эти поля читались только из вложенного profile и всегда были None.
    assert profile.created_at == "2024-01-01T00:00:00Z"
    assert profile.support_chat_id == "support-1"
    assert profile.system_chat_id == "system-1"
    assert profile.avatar_url == "https://cdn/avatar.png"
    assert profile.reviews_count == 5


def test_account_profile_reads_verification_fields():
    """Поля верификации из живого `viewer` (canPublishItems и т.п.) доходят до профиля."""
    data = {
        "id": "user-1",
        "canPublishItems": False,
        "hasConfirmedPhoneNumber": False,
        "isFundsProtectionActive": True,
    }
    profile = parser.account_profile(data)
    assert profile.can_publish_items is False
    assert profile.has_confirmed_phone_number is False
    assert profile.is_funds_protection_active is True


def test_chat_auto_response_list_parsed():
    data = {
        "edges": [{"node": {"id": "a1", "question": "Как купить?", "answer": "Нажмите «Купить».",
                            "sequence": 1}}],
        "pageInfo": None,
        "totalCount": 1,
    }
    result = parser.chat_auto_response_list(data)
    assert result.total_count == 1
    assert result.chat_auto_responses[0].question == "Как купить?"
    assert result.chat_auto_responses[0].answer == "Нажмите «Купить»."


def test_account_profile_falls_back_to_nested_profile():
    data = {"id": "user-1", "profile": {"createdAt": "2023-05-05", "supportChatId": "s"}}
    profile = parser.account_profile(data)
    assert profile.created_at == "2023-05-05"
    assert profile.support_chat_id == "s"


def test_value_range_limit_parsed_as_object():
    option = parser.game_category_option({
        "id": "opt-1",
        "label": "Количество",
        "valueRangeLimit": {"min": 1, "max": 100},
    })
    assert option.value_range_limit.min == 1
    assert option.value_range_limit.max == 100


def test_value_range_limit_non_dict_is_none():
    option = parser.game_category_option({"id": "opt-1", "valueRangeLimit": 5})
    assert option.value_range_limit is None


def test_chat_message_file_parsed():
    message = parser.chat_message({
        "id": "msg-1",
        "text": "держите файл",
        "file": {"id": "file-1", "url": "https://cdn/file.png", "filename": "file.png",
                 "mime": "image/png"},
    })
    assert message.file is not None
    assert message.file.url == "https://cdn/file.png"
    assert message.file.mime == "image/png"


def test_chat_message_without_file():
    message = parser.chat_message({"id": "msg-1", "text": "привет"})
    assert message.file is None


def test_list_builders_filter_empty_nodes():
    data = {
        "edges": [
            {"node": None},
            {"node": {"id": "chat-1"}},
            None,
        ],
        "pageInfo": {"hasNextPage": False},
        "totalCount": 2,
    }
    chat_list = parser.chat_list(data)
    assert len(chat_list.chats) == 1
    assert chat_list.chats[0].id == "chat-1"


def test_review_list_filters_empty_nodes():
    data = {"edges": [{"node": {"id": "review-1"}}, {"node": None}], "pageInfo": None,
            "totalCount": 1}
    review_list = parser.review_list(data)
    assert [r.id for r in review_list.reviews] == ["review-1"]
