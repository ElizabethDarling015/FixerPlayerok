"""Реакции на ваши сообщения (👍 / 🤷 / 🤬) и на уведомления о сделке (⚡ / 🤔 / 👎)."""
from __future__ import annotations

from types import SimpleNamespace

from fixer.tg import reactions
from fixer.tg.handlers import replies
from fixer.tg.notifications import Notifier
from fixer_helpers import FakeTgBot, make_fixer
from playerokapi.common.exceptions import RequestSendingError


class ReactBot(FakeTgBot):
    def __init__(self):
        super().__init__()
        self.reactions: list[tuple[int, int, str]] = []

    async def set_message_reaction(self, chat_id, message_id, reaction):
        self.reactions.append((chat_id, message_id, reaction[0].emoji))
        return True


class FakeMessage:
    def __init__(self, bot, text="привет", reply_to=None):
        self.bot, self.text, self.reply_to_message = bot, text, reply_to
        self.chat = SimpleNamespace(id=1)
        self.message_id = 50
        self.answers: list[str] = []

    async def answer(self, text, **_):
        self.answers.append(text)


def online_fixer():
    fixer = make_fixer()
    fixer.playerok_connected = True
    return fixer


def emojis(bot):
    return [r[2] for r in bot.reactions]


async def test_sent_message_gets_thumbs_up():
    bot, fixer = ReactBot(), online_fixer()
    message = FakeMessage(bot)
    assert await reactions.deliver(message, fixer, "pm-1", "привет")
    assert fixer.account.sent_messages == [("pm-1", "привет")]
    assert emojis(bot) == ["👍"] and message.answers == []


async def test_wrong_chat_gets_shrug_and_nothing_is_sent():
    bot, fixer = ReactBot(), online_fixer()
    for chat_id in (None, "system-chat"):  # не определён / «Уведомления Playerok»
        message = FakeMessage(bot)
        assert not await reactions.deliver(message, fixer, chat_id, "привет")
    assert fixer.account.sent_messages == []
    assert emojis(bot) == ["🤷", "🤷"]


async def test_offline_or_connection_error_gets_angry_face():
    bot, fixer = ReactBot(), online_fixer()
    fixer.playerok_connected = False
    assert not await reactions.deliver(FakeMessage(bot), fixer, "pm-1", "привет")
    assert fixer.account.sent_messages == []

    fixer.playerok_connected = True

    def broken(*_a, **_k):
        raise RequestSendingError("https://playerok.com/graphql", "timeout")

    fixer.account.send_message = broken
    message = FakeMessage(bot)
    assert not await reactions.deliver(message, fixer, "pm-1", "привет")
    assert emojis(bot) == ["🤬", "🤬"] and message.answers == []


async def test_playerok_refusal_gets_shrug_and_log_hint():
    bot, fixer = ReactBot(), online_fixer()

    def refused(*_a, **_k):
        raise RuntimeError("CHAT_CLOSED")

    fixer.account.send_message = refused
    message = FakeMessage(bot)
    assert not await reactions.deliver(message, fixer, "pm-1", "привет")
    assert emojis(bot) == ["🤷"]
    assert len(message.answers) == 1 and "лог" in message.answers[0].lower()


async def test_reply_to_message_without_chat_gets_shrug():
    bot, fixer = ReactBot(), online_fixer()
    notifier = SimpleNamespace(reply_map={})
    state = SimpleNamespace(get_state=_none)
    quoted = SimpleNamespace(message_id=7, entities=None, caption_entities=None, text="📊 Сводка за день", caption=None)
    message = FakeMessage(bot, reply_to=quoted)
    await replies.on_reply(message, state, fixer, notifier)
    assert emojis(bot) == ["🤷"] and fixer.account.sent_messages == []


async def _none():
    return None


async def test_deal_reaction_waits_for_notification_and_survives_restart(tmp_path):
    bot = ReactBot()
    store = reactions.DealReactions(str(tmp_path / "r.json"))
    await store.set(bot, "deal-1", "⚡")          # восстановили раньше, чем ушло уведомление
    assert bot.reactions == []
    await store.add_messages(bot, "deal-1", [(1, 10)])
    assert bot.reactions == [(1, 10, "⚡")]

    again = reactions.DealReactions(str(tmp_path / "r.json"))  # после перезапуска
    await again.set(bot, "deal-1", "🤔")
    assert bot.reactions[-1] == (1, 10, "🤔")


async def test_new_deal_notification_gets_restore_reaction():
    fixer = make_fixer()
    fixer.settings.notifications.new_deal = True
    bot = ReactBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))
    deal = SimpleNamespace(id="deal-7", item=SimpleNamespace(id="it", name="Лот", price=100),
                           user=SimpleNamespace(username="buyer", id="b"), raw_status=SimpleNamespace(name="PAID"),
                           chat=SimpleNamespace(id="chat-7"))
    await notifier._notify_new_deal(deal)
    assert len(bot.sent) == 1 and bot.reactions == []   # новая покупка — без реакции
    await notifier.react_deal("deal-7", "⚡")
    assert emojis(bot) == ["⚡"]
