"""Тесты уведомлений Cardinal (`cardinal.tg.notifications.Notifier`) на фейковом боте."""
from types import SimpleNamespace

from cardinal.tg.notifications import Notifier
from playerokapi.updater.events import ItemPaidEvent, NewDealEvent, NewMessageEvent, NewReviewEvent

from cardinal_helpers import FakeTgBot, make_cardinal, make_chat, make_chat_message


def make_notifier(admin_ids={1, 2}) -> tuple[Notifier, object, FakeTgBot]:
    cardinal = make_cardinal()
    bot = FakeTgBot()
    admins = SimpleNamespace(all_ids=set(admin_ids))
    return Notifier(cardinal, bot, admins), cardinal, bot


def make_deal(item_name="Лот", deal_id="deal-1"):
    return SimpleNamespace(
        id=deal_id,
        item=SimpleNamespace(name=item_name),
        user=SimpleNamespace(username="buyer"),
        raw_status=SimpleNamespace(name="PAID"),
    )


async def test_new_deal_sent_to_all_admins():
    notifier, cardinal, bot = make_notifier()
    await notifier.on_event(NewDealEvent(None, make_deal()))
    assert len(bot.sent) == 2
    assert {chat_id for chat_id, _ in bot.sent} == {1, 2}
    assert "Лот" in bot.sent[0][1]


async def test_toggle_disables_notification():
    notifier, cardinal, bot = make_notifier()
    cardinal.settings.notifications.new_deal = False
    await notifier.on_event(NewDealEvent(None, make_deal()))
    assert bot.sent == []


async def test_new_message_disabled_by_default():
    notifier, cardinal, bot = make_notifier()
    event = NewMessageEvent(None, make_chat("pk-chat"), make_chat_message("привет"))
    await notifier.on_event(event)
    assert bot.sent == []  # new_message по умолчанию выключен


async def test_new_message_fills_reply_map():
    notifier, cardinal, bot = make_notifier(admin_ids={7})
    cardinal.settings.notifications.new_message = True
    event = NewMessageEvent(None, make_chat("pk-chat"), make_chat_message("привет <b>жирный</b>"))

    await notifier.on_event(event)

    assert len(bot.sent) == 1
    chat_id, text = bot.sent[0]
    assert "&lt;b&gt;" in text  # HTML экранирован
    # Соответствие TG-сообщение → чат Playerok сохранено для ответа reply'ем.
    assert notifier.reply_map == {(7, 1): "pk-chat"}


async def test_own_messages_not_notified():
    notifier, cardinal, bot = make_notifier()
    cardinal.settings.notifications.new_message = True
    own = make_chat_message("моё", user_id=cardinal.account.id)
    await notifier.on_event(NewMessageEvent(None, make_chat(), own))
    assert bot.sent == []


async def test_item_paid_with_delivery_notification():
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    # Журнал говорит «sent» — значит Runner уже выдал товар: ждём два уведомления.
    cardinal.autodelivery_manager = SimpleNamespace(
        ledger=SimpleNamespace(get_state=lambda deal_id: "sent"),
        get_stock_size=lambda name: 4,
    )
    deal = make_deal()
    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, deal))

    assert len(bot.sent) == 2
    assert "оплачен" in bot.sent[0][1].lower()
    assert "4" in bot.sent[1][1]


async def test_item_paid_without_delivery():
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    cardinal.autodelivery_manager = SimpleNamespace(
        ledger=SimpleNamespace(get_state=lambda deal_id: "seen_paid"),
        get_stock_size=lambda name: 4,
    )
    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal()))
    assert len(bot.sent) == 1  # только «оплачен», без «выдан»


async def test_new_review():
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    review = SimpleNamespace(rating=5, text="топ", creator=SimpleNamespace(username="ivan"))
    await notifier.on_event(NewReviewEvent(None, review))
    assert "5" in bot.sent[0][1] and "ivan" in bot.sent[0][1]


async def test_notify_started():
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    await notifier.notify_started()
    text = bot.sent[0][1]
    assert "seller" in text and "100" in text


async def test_notify_error_respects_toggle():
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    await notifier.notify_error("boom")
    assert len(bot.sent) == 1
    cardinal.settings.notifications.errors = False
    await notifier.notify_error("boom2")
    assert len(bot.sent) == 1


async def test_notify_restore_respects_toggle():
    """Уведомления автовосстановления управляются тумблером restore (раньше слались всегда)."""
    notifier, cardinal, bot = make_notifier(admin_ids={1})
    await notifier.notify_restore_ok("Лот", "id-1")
    assert len(bot.sent) == 1

    cardinal.settings.notifications.restore = False
    await notifier.notify_restore_ok("Лот", "id-2")
    await notifier.notify_restore_failed("Лот", "ошибка")
    await notifier.notify_restore_premium_fallback("Лот", "id-3", "не хватило баланса")
    assert len(bot.sent) == 1


async def test_send_failure_to_one_admin_does_not_break_others():
    notifier, cardinal, bot = make_notifier(admin_ids={1, 2})

    original = bot.send_message

    async def flaky(chat_id, text, **kwargs):
        if chat_id == 1:
            raise RuntimeError("blocked")
        return await original(chat_id, text, **kwargs)

    bot.send_message = flaky
    await notifier.notify_error("boom")
    assert [chat_id for chat_id, _ in bot.sent] == [2]
