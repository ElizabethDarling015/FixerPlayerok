"""Уведомления: поддержка, уведомления площадки, сообщения покупателя, новая сделка, выплата,
кнопки «Подтвердить выдачу» / «Свернуть», кэш запросов и чёрный список по ID.
Всё на моках — без сети и Telegram."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from fixer.settings import BlacklistConfig
from fixer.tg import chat_kinds
from fixer.tg.api_cache import TTLCache
from fixer.tg.handlers import deal_actions, menu, replies
from fixer.tg.notifications import Notifier, build_payout_details
from fixer_helpers import FakeTgBot, make_fixer
from playerokapi.common.enums import ChatMessageEvents, ChatTypes, ItemDealStatuses
from playerokapi.updater.events import ItemPaidEvent, NewDealEvent, NewMessageEvent


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Повтор запроса сделки ждёт секунду — в тестах не ждём."""
    real_sleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda *_a, **_k: real_sleep(0))


def user(uid, name, role="USER"):
    return SimpleNamespace(id=uid, username=name, raw_role=role, role=None)


def msg(text="", author=None, event=None, item=None, images=()):
    return SimpleNamespace(id="m1", text=text, user=author, event=event, event_by_user=author if event else None,
                           moderator=None, item=item, deal=None, images=list(images), file=None, buttons=[])


def chat(chat_id="chat-1", type_=None, users=(), deals=()):
    return SimpleNamespace(id=chat_id, type=type_, users=list(users), deals=list(deals))


class PhotoBot(FakeTgBot):
    """Бот, который ещё и запоминает клавиатуры."""

    def __init__(self):
        super().__init__()
        self.markups = []

    async def send_message(self, chat_id, text, **kwargs):
        self.markups.append(kwargs.get("reply_markup"))
        return await super().send_message(chat_id, text, **kwargs)


def make_notifier(fixer=None):
    fixer = fixer or make_fixer()
    fixer.settings.notifications.new_message = True
    bot = PhotoBot()
    return Notifier(fixer, bot, SimpleNamespace(all_ids={1})), fixer, bot


# ----------------------------------------------------------------------
# Кто есть кто
# ----------------------------------------------------------------------

def test_chat_kind_by_type_and_by_profile_ids():
    account = SimpleNamespace(profile=SimpleNamespace(support_chat_id="sup", system_chat_id="sys"))
    assert chat_kinds.chat_kind(chat(type_=ChatTypes.SUPPORT), account) == chat_kinds.SUPPORT
    assert chat_kinds.chat_kind(chat(type_=ChatTypes.NOTIFICATIONS), account) == chat_kinds.SYSTEM
    # В WS-кадре типа нет — узнаём по ID из профиля.
    assert chat_kinds.chat_kind(chat("sup"), account) == chat_kinds.SUPPORT
    assert chat_kinds.chat_kind(chat("sys"), account) == chat_kinds.SYSTEM
    assert chat_kinds.chat_kind(chat("other"), account) == chat_kinds.PM


def test_staff_detected_by_role_not_by_emoji():
    assert chat_kinds.is_staff(user("1", "📦 Роман Х.", "POSTMODERATOR"))
    assert chat_kinds.is_staff(user("2", "⚖️ Виктор Г.", "SECURITY"))
    assert not chat_kinds.is_staff(user("3", "⚠️ хитрый покупатель", "USER"))


def test_chat_titles_in_list():
    account = SimpleNamespace(id="me", profile=SimpleNamespace(support_chat_id=None, system_chat_id=None))
    me = user("me", "Bez Limit")
    assert chat_kinds.chat_title(chat(type_=ChatTypes.SUPPORT), account) == chat_kinds.SUPPORT_TITLE
    assert chat_kinds.chat_title(chat(type_=ChatTypes.NOTIFICATIONS, users=[me]), account) == chat_kinds.SYSTEM_TITLE
    assert chat_kinds.chat_title(chat(type_=ChatTypes.PM, users=[me, user("b", "buyer")]), account) == "👤 buyer"


# ----------------------------------------------------------------------
# Новые сообщения
# ----------------------------------------------------------------------

async def test_staff_started_event_has_its_own_look():
    notifier, fixer, bot = make_notifier()
    staff = user("s", "⚖️ Виктор Г.", "SECURITY")
    event = NewMessageEvent(None, chat("support-chat"), msg(author=staff, event=ChatMessageEvents.CHAT_STARTED))
    await notifier.on_event(event)
    (_, text), = bot.sent
    assert "Смотрим чат" in text and "⚖️ Виктор Г." in text and chat_kinds.SUPPORT_TITLE in text
    assert "{" not in text


async def test_support_chat_message_is_rendered_not_raw_template():
    notifier, fixer, bot = make_notifier()
    staff = user("s", "🔰 Лилия Д.", "SUPPORT")
    await notifier.on_event(NewMessageEvent(None, chat("support-chat"), msg("Передали заявку", staff)))
    (_, text), = bot.sent
    assert "Поддержка Playerok" in text and "🔰 Лилия Д." in text and "Передали заявку" in text
    assert "{username}" not in text and "{item}" not in text


async def test_staff_in_deal_chat_shows_buyer_and_lot():
    notifier, fixer, bot = make_notifier()
    staff = user("s", "📦 Роман Х.", "POSTMODERATOR")
    deal = SimpleNamespace(item=SimpleNamespace(name="WebStorm"), user=user("b", "buyer"))
    the_chat = chat("deal-chat", users=[user("me-id", "seller"), user("b", "buyer"), staff], deals=[deal])
    await notifier.on_event(NewMessageEvent(None, the_chat, msg("Предоставьте доступ", staff)))
    (_, text), = bot.sent
    assert "Поддержка в сделке" in text and "buyer" in text and "WebStorm" in text


async def test_system_notice_with_lot_link():
    notifier, fixer, bot = make_notifier()
    item = SimpleNamespace(name="DataSpell", slug="abc-dataspell")
    await notifier.on_event(NewMessageEvent(None, chat("system-chat"), msg("Ваш товар заблокирован.", None, item=item)))
    (_, text), = bot.sent
    assert "Уведомление Playerok" in text and "Ваш товар заблокирован." in text
    assert "https://playerok.com/products/abc-dataspell" in text
    assert "Bez Limit" not in text and "Лот:</b> ?" not in text


async def test_buyer_message_has_lot_and_hidden_chat_link():
    notifier, fixer, bot = make_notifier()
    deal = SimpleNamespace(item=SimpleNamespace(name="LightBurn"), user=user("b", "Solomon3333"))
    the_chat = chat("pm-1", users=[user("b", "Solomon3333")], deals=[deal])
    await notifier.on_event(NewMessageEvent(None, the_chat, msg("да помогла", user("b", "Solomon3333"))))
    (_, text), = bot.sent
    assert "LightBurn" in text and "да помогла" in text
    assert 'href="https://playerok.com/chats/pm-1"' in text  # reply переживёт перезапуск


async def test_own_and_marker_messages_are_skipped():
    notifier, fixer, bot = make_notifier()
    await notifier.on_event(NewMessageEvent(None, chat(), msg("привет", user("me-id", "seller"))))
    await notifier.on_event(NewMessageEvent(None, chat(), msg("{{ITEM_SENT}}", user("b", "buyer"))))
    assert bot.sent == []


def test_reply_finds_chat_in_hidden_link():
    url = "https://playerok.com/chats/1f1c3a2f-1080-6930-f8c2-403cc292c1c9"
    assert replies._extract_chat_id(url) == "1f1c3a2f-1080-6930-f8c2-403cc292c1c9"


# ----------------------------------------------------------------------
# Новая сделка
# ----------------------------------------------------------------------

def paid_deal(item="WebStorm", buyer="homoSanyok", status="PAID"):
    return SimpleNamespace(
        id="deal-1", item=SimpleNamespace(name=item, price=330), user=user("b", buyer),
        raw_status=SimpleNamespace(name=status), chat=SimpleNamespace(id="chat-9"),
    )


async def test_new_deal_without_status_and_buttons_only_when_paid():
    notifier, fixer, bot = make_notifier()
    await notifier.on_event(NewDealEvent(None, paid_deal()))
    (_, text), = bot.sent
    assert "Статус" not in text and "Оплачено" not in text and "PAID" not in text
    assert "Ответ на сообщение" not in text
    assert "homoSanyok\n━━━" in text and "330 ₽\n🆔" in text  # без пустых строк
    assert "Авто-выдача активна" not in text  # для лота выдача ботом не настроена
    buttons = [b.callback_data for b in bot.markups[0].inline_keyboard[0]]
    assert buttons == ["dl:ok:deal-1", "dl:min"]


async def test_new_deal_shows_autodelivery_only_when_configured():
    fixer = make_fixer()
    fixer.autodelivery_config.lots["WebStorm"] = SimpleNamespace(stock_file="x.txt")
    notifier, fixer, bot = make_notifier(fixer)
    await notifier.on_event(NewDealEvent(None, paid_deal()))
    assert "Авто-выдача активна" in bot.sent[0][1]


async def test_pending_deal_has_only_collapse_button():
    notifier, fixer, bot = make_notifier()
    await notifier.on_event(NewDealEvent(None, paid_deal(status="PENDING")))
    assert [b.callback_data for b in bot.markups[0].inline_keyboard[0]] == ["dl:min"]


async def test_one_toggle_controls_new_deal():
    notifier, fixer, bot = make_notifier()
    fixer.settings.notifications.new_deal = False
    await notifier.on_event(ItemPaidEvent(None, chat(), None, paid_deal()))
    assert not any("Новая сделка" in t for _, t in bot.sent)


async def test_deal_details_requested_once_thanks_to_cache():
    notifier, fixer, bot = make_notifier()
    calls = []
    full = SimpleNamespace(chat=SimpleNamespace(id="chat-9"),
                           item=SimpleNamespace(game=SimpleNamespace(name="JetBrains"),
                                                category=SimpleNamespace(name="Подписки")))
    fixer.account.get_deal = lambda deal_id: calls.append(deal_id) or full
    deal = paid_deal()
    deal.chat = None
    assert await notifier._resolve_section_via_deal_api(deal) == "JetBrains → Подписки"
    assert await notifier._resolve_deal_chat_id(deal) == "chat-9"
    assert calls == ["deal-1"]


# ----------------------------------------------------------------------
# Свернуть / Подтвердить выдачу
# ----------------------------------------------------------------------

FULL_TEXT = (
    "🛒 Новая сделка\n\n📂 Раздел: JetBrains → Подписки\n"
    "🎁 Лот: 🌐 WebStorm — Лицензия навсегда | Lifetime [Автовыдача 24/7]\n"
    "👤 Покупатель: homoSanyok\n📋 Статус: Оплачено\n\n━━━━━━━━━━━━━━━━━━━\n💰 Цена: 330 ₽\n\n"
    "💬 Ответ на сообщение, отвечает в чат\n🆔 1f1c3b0d-05ec-6c10-17d6-9d024a8906ae"
)


def test_collapsed_text_is_five_lines():
    short = deal_actions.build_collapsed_text(make_fixer().l10n, FULL_TEXT)
    assert short.count("\n") == 4
    assert "JetBrains → Подписки" in short and "Купил:</b> homoSanyok" in short
    assert "330 ₽" in short and "1f1c3b0d-05ec-6c10-17d6-9d024a8906ae" in short
    assert "🌐 WebStorm — Лицензия навсегда | Lifetime [Автовыдача 24/7]" in short


class FakeMessage:
    def __init__(self, photo=False):
        self.photo = [object()] if photo else None
        self.caption = FULL_TEXT if photo else None
        self.text = None if photo else FULL_TEXT
        self.edits = []

    async def edit_caption(self, caption, reply_markup=None):
        self.edits.append(("caption", caption, reply_markup))

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append(("text", text, reply_markup))

    async def delete(self):
        from aiogram.exceptions import TelegramBadRequest
        raise TelegramBadRequest(method=None, message="message can't be deleted for everyone")


class FakeQuery:
    def __init__(self, data, message):
        self.data, self.message, self.answers = data, message, []

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))


async def test_collapse_keeps_photo_and_removes_buttons():
    message = FakeMessage(photo=True)
    await deal_actions.cb_collapse(FakeQuery("dl:min", message), make_fixer())
    kind, text, markup = message.edits[0]
    assert kind == "caption" and markup is None and text.startswith("🛒 <b>Раздел:</b>")


async def test_confirm_marks_deal_sent_then_collapses():
    fixer = make_fixer()
    calls = []
    fixer.account.update_deal = lambda deal_id, status: calls.append((deal_id, status))
    query = FakeQuery("dl:ok:deal-1", FakeMessage())
    await deal_actions.cb_confirm(query, fixer)
    assert calls == [("deal-1", ItemDealStatuses.SENT)]
    assert query.answers[0] == ("✅ Выдача подтверждена.", True)
    assert query.message.edits and query.message.edits[0][2] is None


async def test_confirm_error_keeps_buttons():
    fixer = make_fixer()

    def boom(deal_id, status):
        raise RuntimeError("сделка уже подтверждена")
    fixer.account.update_deal = boom
    query = FakeQuery("dl:ok:deal-1", FakeMessage())
    await deal_actions.cb_confirm(query, fixer)
    text, alert = query.answers[0]
    assert alert and "сделка уже подтверждена" in text
    assert query.message.edits == []


async def test_close_falls_back_when_message_too_old():
    message = FakeMessage()
    query = FakeQuery("close", message)
    await menu.cb_close(query, make_fixer())
    assert message.edits == [("text", "✖️ Меню закрыто.", None)]


# ----------------------------------------------------------------------
# Выплата, чёрный список, кэш
# ----------------------------------------------------------------------

def test_payout_hides_unknown_fields():
    l10n = make_fixer().l10n
    details = build_payout_details(l10n, amount=None, method=None, status=None, date=None, balance=41.8)
    assert "Сумма" not in details and "Способ" not in details and "41.8 ₽" in details
    full = build_payout_details(l10n, amount=5100, method="СБП", status="✅", date="d", balance=1)
    assert "-5 100 ₽" in full and "--" not in full and "₽ ₽" not in full


def test_blacklist_remembers_id_and_survives_rename():
    config = BlacklistConfig(usernames=["cheater"])
    assert config.contains("cheater", "uid-1")
    assert config.remember_id("cheater", "uid-1")
    assert config.contains("new_nick", "uid-1")
    config.remove("cheater")
    assert not config.contains("new_nick", "uid-1")


def test_ttl_cache_expiry_and_size():
    now = [0.0]
    cache = TTLCache(ttl=10, maxsize=2, clock=lambda: now[0])
    cache.set("a", 1)
    cache.set("b", None)  # None не кэшируется
    assert cache.get("a") == 1 and cache.get("b") is None
    now[0] = 11
    assert cache.get("a") is None
    for key in "xyz":
        cache.set(key, key)
    assert len(cache) == 2 and cache.get("x") is None


async def test_cached_getters_call_the_api_once():
    notifier, fixer, bot = make_notifier()
    calls = []
    fixer.account.get_item = lambda item_id=None, slug=None: calls.append(("item", item_id, slug)) or SimpleNamespace(name="L")
    fixer.account.get_my_items = lambda cursor, count: calls.append(("my", count)) or SimpleNamespace(items=[])
    fixer.account.get_chat = lambda chat_id: calls.append(("chat", chat_id)) or SimpleNamespace(id=chat_id, deals=[], users=[])
    for _ in range(3):
        await notifier._get_item("i1")
        await notifier._get_item(slug="s1")
        await notifier._get_my_items()
        await notifier._get_chat("c1")
    assert calls == [("item", "i1", None), ("item", None, "s1"), ("my", 100), ("chat", "c1")]


async def test_incomplete_deal_is_not_requested_in_a_loop():
    notifier, fixer, bot = make_notifier()
    calls = []
    fixer.account.get_deal = lambda deal_id: calls.append(deal_id) or SimpleNamespace(chat=None, item=None)
    deal = paid_deal()
    deal.chat = None
    await notifier._resolve_section_via_deal_api(deal)
    await notifier._resolve_deal_chat_id(deal)
    assert len(calls) == 2  # первая попытка + одна повторная, дальше — из кэша


async def test_payout_taken_from_withdraw_transactions():
    from playerokapi import parser
    notifier, fixer, bot = make_notifier()
    raw = {"edges": [
        {"node": {"id": "new", "operation": "WITHDRAW", "value": 2000, "status": "PENDING",
                  "createdAt": "2026-10-09T11:26:24Z", "provider": {"id": "SBP", "name": "СБП"}}},
        {"node": {"id": "done", "operation": "WITHDRAW", "value": 3100, "status": "CONFIRMED",
                  "createdAt": "2026-09-30T14:12:54Z", "provider": {"id": "SBP", "name": "СБП"}}},
    ], "pageInfo": {}}
    asked = []
    fixer.account.get_transactions = lambda count, cursor, flt: asked.append(flt) or parser.transaction_list(raw)
    info = await notifier._fetch_latest_payout()
    assert asked == [{"operation": ["WITHDRAW"]}]
    # «Выплата успешно проведена» — про проведённую, а не про только что созданную заявку.
    assert info["amount"] == 3100 and info["method"] == "СБП" and info["status"].name == "CONFIRMED"


async def test_support_bot_answer_in_support_chat():
    notifier, fixer, bot = make_notifier()
    await notifier.on_event(NewMessageEvent(None, chat("support-chat"), msg("🎃 Сделка проходит по этапам", None)))
    (_, text), = bot.sent
    assert "Поддержка Playerok" in text and chat_kinds.SUPPORT_BOT in text and "Сделка проходит" in text


def test_pinned_chats_on_top_and_not_duplicated():
    from fixer.tg.handlers.chats import build_chats_list
    fixer = make_fixer()
    me = user("me-id", "seller")
    support = chat("support-chat", type_=ChatTypes.SUPPORT)
    system = chat("system-chat", type_=ChatTypes.NOTIFICATIONS, users=[me])
    for c in (support, system):
        c.unread_messages_counter = 0
    buyers = []
    for i in range(3):
        c = chat(f"pm-{i}", type_=ChatTypes.PM, users=[me, user(f"b{i}", f"buyer{i}")])
        c.unread_messages_counter = 0
        buyers.append(c)
    page = SimpleNamespace(chats=[buyers[0], system, buyers[1], buyers[2]])
    _, markup = build_chats_list(fixer, page, 0, False, pinned=[support, system])
    titles = [row[0].text for row in markup.inline_keyboard[:-1]]
    assert titles == [chat_kinds.SUPPORT_TITLE, chat_kinds.SYSTEM_TITLE, "👤 buyer0", "👤 buyer1", "👤 buyer2"]
    # На следующих страницах закреплённых нет, и в общем списке они не повторяются.
    _, markup = build_chats_list(fixer, SimpleNamespace(chats=[system, buyers[2]]), 1, False)
    chat_buttons = [b.callback_data for row in markup.inline_keyboard for b in row
                    if b.callback_data.startswith("chat:view:")]
    assert chat_buttons == ["chat:view:pm-2"]


def _callbacks(markup):
    return [b.callback_data for row in (markup.inline_keyboard if markup else []) for b in row]


async def test_support_and_system_messages_have_close_button():
    """Под сообщениями поддержки (оба чата: поддержка и уведомления площадки) — «❌ Закрыть»."""
    notifier, fixer, bot = make_notifier()
    staff = user("s", "🔰 Лилия Д.", "SUPPORT")
    await notifier.on_event(NewMessageEvent(None, chat("support-chat"), msg("Передали заявку", staff)))
    await notifier.on_event(NewMessageEvent(None, chat("system-chat"), msg("Ваш товар заблокирован.", None)))
    assert len(bot.markups) == 2
    for markup in bot.markups:
        assert _callbacks(markup) == ["close"]
        assert markup.inline_keyboard[0][0].text == "❌ Закрыть"


async def test_buyer_message_new_template_without_close():
    notifier, fixer, bot = make_notifier()
    deal = SimpleNamespace(item=SimpleNamespace(name="LightBurn"), user=user("b", "Solomon3333"))
    the_chat = chat("pm-1", users=[user("b", "Solomon3333")], deals=[deal])
    await notifier.on_event(NewMessageEvent(None, the_chat, msg("да помогла", user("b", "Solomon3333"))))
    (_, text), = bot.sent
    body = text.split("</a>", 1)[-1] if "</a>" in text else text
    assert "Сообщение от Solomon3333!" in body
    assert body.index("💬:да помогла") < body.index("🎁 <b>Лот:</b> LightBurn")
    assert "━━━" not in body and "Ответ на сообщение" not in body
    assert "close" not in _callbacks(bot.markups[0])


async def test_buyer_message_sent_without_photo():
    notifier, fixer, bot = make_notifier()
    item = SimpleNamespace(id="it-1", name="LightBurn", attachment=SimpleNamespace(url="https://img/x.png"))
    deal = SimpleNamespace(item=item, user=user("b", "Solomon3333"))
    the_chat = chat("pm-1", users=[user("b", "Solomon3333")], deals=[deal])
    photos = []

    async def send_photo(chat_id, photo, **kwargs):
        photos.append(photo)
        return SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=99)

    bot.send_photo = send_photo
    await notifier.on_event(NewMessageEvent(None, the_chat, msg("привет", user("b", "Solomon3333"), item=item)))
    assert len(bot.sent) == 1 and photos == []
