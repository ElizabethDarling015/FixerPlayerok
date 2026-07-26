"""Тесты послепродажного модуля Cardinal (`cardinal.modules.postsale`): благодарность за сделку,
реакции на отзывы, дедуп, поиск чата автора отзыва."""
from types import SimpleNamespace

from cardinal.modules.postsale import PostsaleModule
from playerokapi.common.enums import ItemDealDirections
from playerokapi.updater.events import (
    DealConfirmedAutomaticallyEvent,
    DealConfirmedEvent,
    NewReviewEvent,
)

from cardinal_helpers import make_cardinal


def make_module(cardinal=None) -> tuple[PostsaleModule, object]:
    cardinal = cardinal or make_cardinal()
    cardinal.settings.modules.postsale = True
    # «Человеческая» задержка перед ответом выключена — тесты не должны реально спать.
    cardinal.settings.humanize.reply_delay_min = 0.0
    cardinal.settings.humanize.reply_delay_max = 0.0
    return PostsaleModule(cardinal), cardinal


def make_deal(deal_id="deal-1", direction=ItemDealDirections.OUT, buyer="ivan",
              chat_id="chat-1", item_name="Ключ Steam"):
    return SimpleNamespace(
        id=deal_id,
        direction=direction,
        user=SimpleNamespace(username=buyer),
        chat=SimpleNamespace(id=chat_id),
        item=SimpleNamespace(name=item_name),
    )


def make_review(review_id="rev-1", rating=5, buyer_id="buyer-1", buyer="ivan", deal=None):
    return SimpleNamespace(
        id=review_id,
        rating=rating,
        creator=SimpleNamespace(id=buyer_id, username=buyer),
        deal=deal,
    )


def confirmed_event(deal):
    return DealConfirmedEvent(None, deal, previous_status=None, new_status=None)


def auto_confirmed_event(deal):
    return DealConfirmedAutomaticallyEvent(None, deal, previous_status=None, new_status=None)


# ----------------------------------------------------------------------
# Реакция 1: сделка подтверждена
# ----------------------------------------------------------------------

async def test_thanks_once_per_deal_with_variables():
    module, cardinal = make_module()
    cardinal.settings.postsale.confirmed_text = "Спасибо, $username! Оставьте отзыв о «$item_name»."
    deal = make_deal()

    await module.on_event(confirmed_event(deal))
    # Второе событие по той же сделке (автоподтверждение) — дубля быть не должно.
    await module.on_event(auto_confirmed_event(deal))

    assert cardinal.account.sent_messages == [
        ("chat-1", "Спасибо, ivan! Оставьте отзыв о «Ключ Steam»."),
    ]


async def test_purchase_direction_is_skipped():
    module, cardinal = make_module()
    await module.on_event(confirmed_event(make_deal(direction=ItemDealDirections.IN)))
    assert cardinal.account.sent_messages == []


async def test_unknown_direction_is_thanked():
    # direction не заполнен (например, урезанный ответ API) — считаем продажей и благодарим.
    module, cardinal = make_module()
    await module.on_event(confirmed_event(make_deal(direction=None)))
    assert len(cardinal.account.sent_messages) == 1


async def test_blacklisted_buyer_is_skipped():
    module, cardinal = make_module()
    cardinal.blacklist_config.usernames.append("cheater")
    await module.on_event(confirmed_event(make_deal(buyer="cheater")))
    assert cardinal.account.sent_messages == []


async def test_empty_confirmed_text_disables_reaction():
    module, cardinal = make_module()
    cardinal.settings.postsale.confirmed_text = "   "
    await module.on_event(confirmed_event(make_deal()))
    assert cardinal.account.sent_messages == []


async def test_disabled_module_does_nothing():
    module, cardinal = make_module()
    cardinal.settings.modules.postsale = False
    await module.on_event(confirmed_event(make_deal()))
    await module.on_event(NewReviewEvent(None, make_review()))
    assert cardinal.account.sent_messages == []


# ----------------------------------------------------------------------
# Реакция 2: новый отзыв
# ----------------------------------------------------------------------

def make_review_with_chat(**kwargs):
    """Отзыв с заполненной сделкой — чат находится напрямую, без перебора get_chats."""
    deal = SimpleNamespace(chat=SimpleNamespace(id="chat-rev"))
    return make_review(deal=deal, **kwargs)


async def test_good_review_gets_good_text():
    module, cardinal = make_module()
    cardinal.settings.postsale.review_good_text = "Спасибо за $rating★, $username!"
    await module.on_event(NewReviewEvent(None, make_review_with_chat(rating=5)))
    assert cardinal.account.sent_messages == [("chat-rev", "Спасибо за 5★, ivan!")]


async def test_bad_review_gets_bad_text():
    module, cardinal = make_module()
    cardinal.settings.postsale.review_bad_text = "$username, что не так? Решим!"
    await module.on_event(NewReviewEvent(None, make_review_with_chat(rating=2)))
    assert cardinal.account.sent_messages == [("chat-rev", "ivan, что не так? Решим!")]


async def test_review_dedup():
    module, cardinal = make_module()
    review = make_review_with_chat(rating=5)
    await module.on_event(NewReviewEvent(None, review))
    await module.on_event(NewReviewEvent(None, review))
    assert len(cardinal.account.sent_messages) == 1


async def test_empty_review_text_disables_reaction():
    module, cardinal = make_module()
    cardinal.settings.postsale.review_good_text = ""
    await module.on_event(NewReviewEvent(None, make_review_with_chat(rating=5)))
    assert cardinal.account.sent_messages == []
    # Реакция на плохие отзывы при этом продолжает работать.
    await module.on_event(NewReviewEvent(None, make_review_with_chat(review_id="rev-2", rating=1)))
    assert len(cardinal.account.sent_messages) == 1


async def test_blacklisted_reviewer_is_skipped():
    module, cardinal = make_module()
    cardinal.blacklist_config.usernames.append("cheater")
    await module.on_event(NewReviewEvent(None, make_review_with_chat(buyer="cheater")))
    assert cardinal.account.sent_messages == []


async def test_review_chat_found_via_get_chats():
    # Обычный случай: parser.review не заполняет deal — чат ищется перебором get_chats.
    module, cardinal = make_module()
    page = SimpleNamespace(
        chats=[
            SimpleNamespace(id="chat-other", users=[SimpleNamespace(id="other", username="petr")]),
            SimpleNamespace(id="chat-buyer", users=[SimpleNamespace(id="buyer-1", username="ivan")]),
        ],
        page_info=SimpleNamespace(has_next_page=False, end_cursor=None),
    )
    cardinal.account.get_chats = lambda count=50, after_cursor=None: page

    await module.on_event(NewReviewEvent(None, make_review(rating=5)))

    assert len(cardinal.account.sent_messages) == 1
    assert cardinal.account.sent_messages[0][0] == "chat-buyer"


async def test_review_chat_not_found_is_skipped_without_error():
    module, cardinal = make_module()
    cardinal.account.get_chats = lambda count=50, after_cursor=None: SimpleNamespace(
        chats=[], page_info=SimpleNamespace(has_next_page=False, end_cursor=None),
    )
    await module.on_event(NewReviewEvent(None, make_review(rating=5)))
    assert cardinal.account.sent_messages == []


# ----------------------------------------------------------------------
# Статистика
# ----------------------------------------------------------------------

async def test_stats_recorded_for_both_reactions():
    module, cardinal = make_module()
    recorded = []
    cardinal.stats = SimpleNamespace(record=lambda action: recorded.append(action))

    await module.on_event(confirmed_event(make_deal()))
    await module.on_event(NewReviewEvent(None, make_review_with_chat(rating=5)))

    assert recorded == ["postsale", "postsale"]
