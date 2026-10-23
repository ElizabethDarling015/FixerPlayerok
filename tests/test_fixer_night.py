"""Ночное сообщение: окно через полночь, отправка в чат сделки один раз, только ночью."""
from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace

from fixer.modules.night import NightMessageModule, is_night
from fixer.tg.handlers.menu import build_toggles_menu
from fixer_helpers import make_chat, make_fixer
from playerokapi.common.enums import ItemDealDirections
from playerokapi.updater.events import ItemPaidEvent


def test_window_over_midnight():
    t = datetime.time
    assert is_night(t(22, 0), "22:00", "09:00") and is_night(t(3, 15), "22:00", "09:00")
    assert not is_night(t(9, 0), "22:00", "09:00") and not is_night(t(15, 0), "22:00", "09:00")
    assert is_night(t(13, 0), "12:00", "14:00") and not is_night(t(14, 0), "12:00", "14:00")


def make_module(hour: int):
    fixer = make_fixer()
    fixer.settings.modules.night = True
    tasks = []
    fixer.spawn = lambda coro: tasks.append(asyncio.ensure_future(coro))
    module = NightMessageModule(fixer)
    module.delay = 0
    module._now = lambda: datetime.datetime(2026, 10, 12, hour, 30)
    return module, fixer, tasks


def paid(deal_id="deal-1", direction=ItemDealDirections.OUT):
    deal = SimpleNamespace(id=deal_id, direction=direction, user=SimpleNamespace(username="Solomon"),
                           item=SimpleNamespace(name="LightBurn"), chat=None)
    return ItemPaidEvent(None, make_chat("chat-9"), None, deal)


async def test_sent_at_night_once_with_placeholders():
    module, fixer, tasks = make_module(hour=23)
    fixer.settings.night.text = "Ночь, $username! $item скоро"
    await module.on_event(paid())
    await module.on_event(paid())  # повтор события той же сделки
    await asyncio.gather(*tasks)
    assert fixer.account.sent_messages == [("chat-9", "Ночь, Solomon! LightBurn скоро")]


async def test_not_sent_by_day_when_off_or_for_purchases():
    module, fixer, tasks = make_module(hour=14)
    await module.on_event(paid())
    module, fixer2, tasks2 = make_module(hour=23)
    fixer2.settings.modules.night = False
    await module.on_event(paid())
    module3, fixer3, tasks3 = make_module(hour=23)
    await module3.on_event(paid(direction=ItemDealDirections.IN))
    await asyncio.gather(*tasks, *tasks2, *tasks3)
    assert fixer.account.sent_messages == fixer2.account.sent_messages == fixer3.account.sent_messages == []


def test_toggle_and_text_button_in_global_toggles():
    _, markup = build_toggles_menu(make_fixer())
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert ["mod:night", "night:text"] in rows


class _State:
    def __init__(self, data):
        self.data, self.cleared = dict(data), False

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kw):
        self.data.update(kw)

    async def clear(self):
        self.cleared, self.data = True, {}


class _Bot:
    def __init__(self):
        self.edits = []

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
        self.edits.append((message_id, text))


class _Msg:
    def __init__(self, text, reply=None, bot=None):
        self.text, self.reply_to_message, self.answers = text, reply, []
        self.bot, self.chat, self.message_id, self.deleted = bot or _Bot(), SimpleNamespace(id=1), 77, False

    async def answer(self, text, **_):
        self.answers.append(text)
        return self

    async def delete(self):
        self.deleted = True


async def test_new_text_saved_in_same_message_and_reply_is_let_through(monkeypatch):
    import time

    import pytest
    from aiogram.dispatcher.event.bases import SkipHandler

    from fixer.tg.handlers import night
    saved = []
    monkeypatch.setattr(night, "save_main_settings", lambda s: saved.append(s.night.text))
    fixer = make_fixer()

    bot = _Bot()
    state = _State({"since": time.time(), "panel": [1, 555]})
    msg = _Msg("Доброй ночи, $username!", bot=bot)
    await night.on_night_text(msg, state, fixer)
    assert saved == ["Доброй ночи, $username!"]
    # Ваше сообщение удалено, результат — в том же сообщении бота (id 555), нового нет.
    assert msg.deleted and msg.answers == []
    assert bot.edits[-1][0] == 555 and "сохранён" in bot.edits[-1][1] and "Доброй ночи" in bot.edits[-1][1]

    empty = _Msg("/start", bot=bot)
    await night.on_night_text(empty, state, fixer)
    assert empty.deleted and bot.edits[-1][1].startswith("⚠️") and saved == ["Доброй ночи, $username!"]

    state = _State({"since": time.time(), "panel": [1, 555]})  # reply на уведомление — не текст
    with pytest.raises(SkipHandler):
        await night.on_night_text(_Msg("ответ", reply=object()), state, fixer)
    assert state.cleared and saved == ["Доброй ночи, $username!"]


async def test_chat_missing_in_event_is_loaded_from_deal():
    """Оплату первым заметил поллинг (сделка без чата) — раньше сообщение молча не уходило."""
    module, fixer, tasks = make_module(hour=3)
    fixer.account.get_deal = lambda deal_id: SimpleNamespace(chat=SimpleNamespace(id="chat-from-api"))
    deal = SimpleNamespace(id="deal-7", direction=ItemDealDirections.OUT, user=SimpleNamespace(username="Fox"),
                           item=SimpleNamespace(name="GoLand"), chat=None)
    await module.on_event(ItemPaidEvent(None, None, None, deal))
    await asyncio.gather(*tasks)
    assert [cid for cid, _ in fixer.account.sent_messages] == ["chat-from-api"]


async def test_night_skip_reasons_are_logged(caplog):
    from loguru import logger
    lines = []
    sink = logger.add(lambda m: lines.append(str(m)), level="INFO")
    try:
        module, fixer, tasks = make_module(hour=3)
        fixer.settings.modules.night = False
        await module.on_event(paid("deal-off"))
        module2, fixer2, _ = make_module(hour=3)
        fixer2.account.get_deal = lambda deal_id: None
        deal = SimpleNamespace(id="deal-nochat", direction=ItemDealDirections.OUT, user=None, item=None, chat=None)
        await module2.on_event(ItemPaidEvent(None, None, None, deal))
    finally:
        logger.remove(sink)
    text = "".join(lines)
    assert "deal-off" in text and "выключено" in text
    assert "deal-nochat" in text and "чат сделки не найден" in text


def test_global_toggles_order():
    _, markup = build_toggles_menu(make_fixer())
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows[:3] == [["mod:autoraise", "mod:online"], ["mod:autodelivery", "mod:autoresponse"], ["mod:digest"]]
    assert rows[3] == ["mod:night", "night:text"]


# ----------------------------------------------------------------------
# Покупатель пишет ночью → «я сплю» (не чаще раза в час на чат)
# ----------------------------------------------------------------------

from playerokapi.common.enums import ChatTypes  # noqa: E402
from playerokapi.updater.events import NewMessageEvent  # noqa: E402

BUYER = SimpleNamespace(id="buyer-1", username="Valkuz", raw_role="USER", role=None)
ME = SimpleNamespace(id="me-id", username="seller", raw_role="USER", role=None)


def pm_chat(chat_id="chat-5"):
    return SimpleNamespace(id=chat_id, type=ChatTypes.PM, users=[ME, BUYER], deals=[])


def buyer_msg(text="есть кто?", author=BUYER):
    return SimpleNamespace(id="m1", text=text, user=author, event=None, event_by_user=None, moderator=None,
                           item=None, deal=None, images=[], file=None, buttons=[])


async def test_buyer_writes_at_night_gets_reply_once_an_hour():
    module, fixer, tasks = make_module(hour=3)
    module.reply_delay = 0
    fixer.settings.night.reply_text = "Сплю, $username"
    chat = pm_chat()
    await module.on_event(NewMessageEvent(None, chat, buyer_msg()))
    await module.on_event(NewMessageEvent(None, chat, buyer_msg("алло")))  # спам — без ответа
    await asyncio.gather(*tasks)
    assert fixer.account.sent_messages == [("chat-5", "Сплю, Valkuz")]
    module._last_sent["chat-5"] -= 3601  # прошёл час
    await module.on_event(NewMessageEvent(None, chat, buyer_msg("ну?")))
    await asyncio.gather(*tasks)
    assert len(fixer.account.sent_messages) == 2


async def test_no_reply_by_day_off_own_support_markers():
    module, fixer, tasks = make_module(hour=14)
    module.reply_delay = 0
    await module.on_event(NewMessageEvent(None, pm_chat(), buyer_msg()))  # день
    module2, fixer2, tasks2 = make_module(hour=3)
    module2.reply_delay = 0
    fixer2.settings.modules.night = False
    await module2.on_event(NewMessageEvent(None, pm_chat(), buyer_msg()))  # выключено
    module3, fixer3, tasks3 = make_module(hour=3)
    module3.reply_delay = 0
    await module3.on_event(NewMessageEvent(None, pm_chat(), buyer_msg(author=SimpleNamespace(id="me-id", username="seller"))))
    await module3.on_event(NewMessageEvent(None, pm_chat(), buyer_msg("{{ITEM_PAID}}")))
    support = SimpleNamespace(id="sup", type=ChatTypes.SUPPORT, users=[], deals=[])
    await module3.on_event(NewMessageEvent(None, support, buyer_msg()))
    await asyncio.gather(*tasks, *tasks2, *tasks3)
    assert fixer.account.sent_messages == fixer2.account.sent_messages == fixer3.account.sent_messages == []


async def test_purchase_message_counts_for_cooldown():
    module, fixer, tasks = make_module(hour=3)
    module.reply_delay = 0
    await module.on_event(paid())  # ночное «после покупки» в chat-9
    await module.on_event(NewMessageEvent(None, pm_chat("chat-9"), buyer_msg("спасибо")))
    await asyncio.gather(*tasks)
    assert [cid for cid, _ in fixer.account.sent_messages] == ["chat-9"]


def test_texts_menu_and_edit_both_kinds():
    from fixer.tg.handlers import night as night_ui
    fixer = make_fixer()
    text, markup = night_ui.build_night_texts_menu(fixer)
    assert "После покупки" in text and "Ответ на сообщение" in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows == [["night:edit:buy", "night:edit:reply"], ["night:back"]]
    text, markup = night_ui.build_night_text_view(fixer, "reply")
    assert "раза в час" in text and "$item" not in text
    assert [[b.callback_data for b in row] for row in markup.inline_keyboard] == [["night:reset:reply"], ["night:text"]]
