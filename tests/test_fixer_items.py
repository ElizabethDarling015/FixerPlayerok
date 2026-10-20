"""Раздел «🛍 Товары» и проверки витрины после продажи (на моках)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fixer.modules.showcase import ShowcaseModule
from fixer.settings import AutoDeliveryLot
from fixer.tg.handlers import items as items_panel
from fixer_helpers import make_chat, make_fixer
from playerokapi.common.enums import ItemDealDirections, ItemStatuses, PriorityTypes
from playerokapi.updater.events import ItemPaidEvent


def lot(i, section=("JetBrains", "Подписки"), status=ItemStatuses.APPROVED, keep=True, **extra):
    data = dict(id=f"it-{i}", name=f"Лот {i}", price=330, status=status, keep_in_sale=keep,
                game=SimpleNamespace(name=section[0]), category=SimpleNamespace(name=section[1]),
                priority=PriorityTypes.PREMIUM, slug=f"slug-{i}", views_counter=72, deals_counter=4,
                status_expiration_date="2026-11-08T05:29:00.418Z", comment="Ссылка: https://x",
                status_description=None, pause_available=status is ItemStatuses.APPROVED,
                republish_available=status is ItemStatuses.DISCONTINUED, keep_in_sale_available=True,
                is_editable=True)
    data.update(extra)
    return SimpleNamespace(**data)


def callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_sections_grouped_with_counts():
    l10n = make_fixer().l10n
    items = [lot(1), lot(2), lot(3, ("JetBrains", "Другое")),
             lot(4, status=ItemStatuses.PENDING_MODERATION)]
    text, markup = items_panel.build_sections(l10n, items)
    texts = [b.text for row in markup.inline_keyboard for b in row]
    assert "JetBrains → Другое (1)" in texts and "JetBrains → Подписки (3)" in texts
    assert "В продаже: <b>3</b>" in text and "На модерации: <b>1</b>" in text
    assert "it:x:0" in callbacks(markup) and "it:r" in callbacks(markup)


def test_section_items_show_status_and_autorelist_mark():
    l10n = make_fixer().l10n
    text, markup = items_panel.build_section_items(l10n, [lot(1), lot(2, keep=False)], 0)
    texts = [b.text for row in markup.inline_keyboard for b in row]
    assert "🟢 Лот 1 · 330 ₽ 🔁" in texts and "🟢 Лот 2 · 330 ₽" in texts
    assert "it:v:it-1" in callbacks(markup)


def test_card_buttons_depend_on_status():
    l10n = make_fixer().l10n
    text, markup = items_panel.build_item_card(l10n, lot(1), "выкл")
    cbs = callbacks(markup)
    assert {"it:k:it-1", "it:c:it-1", "it:$:it-1", "it:up:it-1", "it:off:it-1"} <= set(cbs)
    assert "🔁 Автовыставление: вкл" in text and "🚀 Премиум" in text and "В продаже до" in text
    assert "Просмотров: 72" in text and "Продаж: 4" in text

    _, markup = items_panel.build_item_card(l10n, lot(2, status=ItemStatuses.DISCONTINUED), "выкл")
    assert "it:on:it-2" in callbacks(markup) and "it:up:it-2" not in callbacks(markup)

    text, markup = items_panel.build_item_card(
        l10n, lot(3, status=ItemStatuses.BLOCKED, status_description="не та категория"), "выкл")
    assert "Причина" in text and "не та категория" in text

    _, markup = items_panel.build_item_card(l10n, lot(4, status=ItemStatuses.EXPIRED), "выкл")
    assert "it:pub:it-4" in callbacks(markup)


class FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append((text, reply_markup))


class FakeQuery:
    def __init__(self, data, user_id=1):
        self.data, self.message, self.alerts = data, FakeMessage(), []
        self.from_user = SimpleNamespace(id=user_id)

    async def answer(self, text=None, **_):
        self.alerts.append(text)


def fixer_with_item(item):
    fixer = make_fixer()
    account = fixer.account
    account.calls = []
    account.get_item = lambda id=None, slug=None: item
    def update_item(item_id, **kw):
        account.calls.append(("update", item_id, kw))
        if "keep_in_sale" in kw:
            item.keep_in_sale = kw["keep_in_sale"]
        return item

    account.update_item = update_item
    account.get_item_priority_statuses = lambda item_id, price: [
        SimpleNamespace(id="prem", price=9, type=PriorityTypes.PREMIUM),
        SimpleNamespace(id="free", price=0, type=PriorityTypes.DEFAULT),
    ]
    account.increase_item_priority_status = lambda *a, **kw: account.calls.append(("raise", a, kw))
    account.publish_item = lambda *a, **kw: account.calls.append(("publish", a, kw))
    return fixer


async def test_keep_in_sale_toggle_updates_playerok_and_reports_real_state():
    item = lot(1, keep=True)
    fixer = fixer_with_item(item)
    query = FakeQuery("it:k:it-1")
    await items_panel.cb_keep(query, fixer)
    assert fixer.account.calls == [("update", "it-1", {"keep_in_sale": False})]
    assert query.alerts[-1] == "🔁 Автовыставление выключено"
    query = FakeQuery("it:k:it-1")
    await items_panel.cb_keep(query, fixer)  # второе нажатие — обратно
    assert fixer.account.calls[-1] == ("update", "it-1", {"keep_in_sale": True})
    assert query.alerts[-1] == "🔁 Автовыставление включено"


async def test_keep_toggle_refuses_when_state_unknown():
    """Ответ Playerok без keepInSale (как было со старым запросом) — не переключаем вслепую."""
    item = lot(1, keep=None)
    fixer = fixer_with_item(item)
    query = FakeQuery("it:k:it-1")
    await items_panel.cb_keep(query, fixer)
    assert fixer.account.calls == [] and "ничего не меняю" in query.alerts[-1]


def test_item_queries_ask_for_keep_in_sale():
    from playerokapi.graphql_queries import QUERY_TEXTS
    assert isinstance(QUERY_TEXTS["items"], str)  # раньше по ошибке был кортеж
    for field in ("keepInSale", "pauseAvailable", "republishAvailable", "keepInSaleAvailable"):
        assert field in QUERY_TEXTS["item"], field
    assert "... on MyItemProfile" in QUERY_TEXTS["items"] and "keepInSale" in QUERY_TEXTS["items"]


async def test_raise_needs_confirmation_and_offers_only_premium():
    item = lot(1)
    fixer = fixer_with_item(item)
    query = FakeQuery("it:up:it-1")
    await items_panel.cb_pay_prepare(query, fixer)
    assert fixer.account.calls == []  # без подтверждения ничего не списано
    text, markup = query.message.edits[-1]
    assert "Поднять в топ" in text and callbacks(markup)[:1] == ["it:go:0"] and "it:go:1" not in callbacks(markup)
    await items_panel.cb_pay_go(FakeQuery("it:go:0"), fixer)
    assert fixer.account.calls == [("raise", ("it-1", "prem"), {"keep_in_sale": True})]
    # Повторное нажатие не списывает второй раз.
    await items_panel.cb_pay_go(FakeQuery("it:go:0"), fixer)
    assert len(fixer.account.calls) == 1


# ----------------------------------------------------------------------
# Витрина после продажи и истёкшие лоты
# ----------------------------------------------------------------------

class FakeNotifier:
    def __init__(self):
        self.reactions, self.stock_empty, self.expired = [], [], []

    async def react_deal(self, deal_id, emoji):
        self.reactions.append((deal_id, emoji))

    async def notify_stock_empty(self, name, paused=False):
        self.stock_empty.append((name, paused))

    async def notify_item_expired(self, item):
        self.expired.append(item.id)


def showcase(storefront_items, stock=None, deactivate=False):
    fixer = make_fixer()
    fixer.notifier = FakeNotifier()
    fixer.account.discontinued = []
    fixer.account.get_my_items = lambda status, count, cursor: SimpleNamespace(
        items=[it for it in storefront_items if it.status in status], page_info=None)
    fixer.account.discontinue_item = lambda item_id: fixer.account.discontinued.append(item_id)
    if stock is not None:
        fixer.autodelivery_config.lots["Лот 1"] = AutoDeliveryLot(stock_file="a.txt", deactivate_when_empty=deactivate)
        fixer.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: stock)
    return ShowcaseModule(fixer), fixer


def deal(name="Лот 1"):
    return SimpleNamespace(id="deal-1", direction=ItemDealDirections.OUT, item=SimpleNamespace(name=name))


async def test_reaction_lightning_when_lot_stays_on_sale_and_thumb_down_when_gone():
    module, fixer = showcase([lot(1)])
    await module.check_after_sale(deal())
    assert fixer.notifier.reactions == [("deal-1", "⚡")]
    module, fixer = showcase([])
    await module.check_after_sale(deal())
    assert fixer.notifier.reactions == [("deal-1", "👎")]


async def test_empty_stock_pauses_lot_when_enabled():
    module, fixer = showcase([lot(1)], stock=0, deactivate=True)
    await module.check_after_sale(deal())
    assert fixer.account.discontinued == ["it-1"]
    assert fixer.notifier.stock_empty == [("Лот 1", True)] and fixer.notifier.reactions == [("deal-1", "👎")]

    module, fixer = showcase([lot(1)], stock=0, deactivate=False)
    await module.check_after_sale(deal())
    assert fixer.account.discontinued == [] and fixer.notifier.stock_empty == [("Лот 1", False)]
    assert fixer.notifier.reactions == [("deal-1", "⚡")]


async def test_paid_event_checked_once_after_delay():
    module, fixer = showcase([lot(1)])
    module.delay = 0
    tasks = []
    fixer.spawn = lambda coro: tasks.append(asyncio.ensure_future(coro))
    event = ItemPaidEvent(None, make_chat(), None, deal())
    await module.on_event(event)
    await module.on_event(event)
    await asyncio.gather(*tasks)
    assert fixer.notifier.reactions == [("deal-1", "⚡")]


async def test_expired_first_run_silent_then_new_ones_notified():
    old = lot(1, status=ItemStatuses.EXPIRED)
    module, fixer = showcase([old])
    assert await module.check_expired() == [] and fixer.notifier.expired == []
    new = lot(2, status=ItemStatuses.EXPIRED)
    module, fixer2 = showcase([old, new])
    await module.check_expired()
    assert fixer2.notifier.expired == ["it-2"]
    await module.check_expired()  # второй раз о том же — молчим
    assert fixer2.notifier.expired == ["it-2"]


async def test_price_edit_deletes_your_message_and_updates_card_in_place():
    import time

    item = lot(1)
    fixer = fixer_with_item(item)
    edits = []

    class Bot:
        async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
            edits.append((message_id, text))

    class State:
        def __init__(self):
            self.data, self.state = {"item_id": "it-1", "since": time.time(), "panel": [1, 900]}, \
                items_panel.ItemEdit.price.state

        async def get_data(self):
            return dict(self.data)

        async def get_state(self):
            return self.state

        async def update_data(self, **kw):
            self.data.update(kw)

        async def clear(self):
            self.data, self.state = {}, None

    class Msg:
        def __init__(self, text):
            self.text, self.reply_to_message, self.bot, self.deleted, self.sent = text, None, Bot(), False, []
            self.chat, self.message_id = SimpleNamespace(id=1), 5

        async def delete(self):
            self.deleted = True

        async def answer(self, text, **_):
            self.sent.append(text)

    state = State()
    bad = Msg("дорого")
    await items_panel.on_edit_value(bad, state, fixer)
    assert bad.deleted and bad.sent == [] and edits[-1][1].startswith("⚠️")
    good = Msg("299")
    await items_panel.on_edit_value(good, state, fixer)
    assert good.deleted and good.sent == []
    assert fixer.account.calls == [("update", "it-1", {"price": 299})]
    assert edits[-1][0] == 900 and "Цена изменена: 299 ₽" in edits[-1][1]


def test_blocked_item_has_no_autorelist_toggle_like_on_site():
    """Playerok у заблокированного лота отдаёт keepInSaleAvailable=true, но editable=false:
    сайт переключатель не показывает, запрос получает 403 — бот тоже не показывает."""
    l10n = make_fixer().l10n
    blocked = lot(1, status=ItemStatuses.BLOCKED, is_editable=False, keep_in_sale_available=True,
                  status_description="не та категория")
    text, markup = items_panel.build_item_card(l10n, blocked, "выкл")
    cbs = callbacks(markup)
    assert "it:k:it-1" not in cbs and "it:c:it-1" not in cbs and "it:$:it-1" not in cbs
    assert "Автовыставление" not in text
    _, markup = items_panel.build_item_card(l10n, lot(2, status=ItemStatuses.PENDING_MODERATION), "выкл")
    assert "it:k:it-2" in callbacks(markup)


def test_forbidden_error_is_explained():
    from playerokapi.common.exceptions import RequestPlayerokError
    exc = RequestPlayerokError.__new__(RequestPlayerokError)
    exc.error_code, exc.error_message = "FORBIDDEN", "У вас нет доступа на выполнение данной операции"
    assert "не разрешает" in items_panel._error_text(make_fixer(), exc)


async def test_keep_toggle_shows_new_state_even_if_playerok_answers_stale():
    """Сразу после сохранения Playerok может вернуть старые данные. Карточка и список «Товаров»
    должны показать новое состояние сразу — по нажатию, без перечитывания."""
    fixer = fixer_with_item(lot(1))
    fixer.account.get_item = lambda id=None, slug=None: lot(1, keep=False)  # всегда «старое»
    cached = lot(1, keep=False)
    items_panel.cache._items, items_panel.cache._loaded_at = [cached], items_panel.cache._clock()
    query = FakeQuery("it:k:it-1")
    await items_panel.cb_keep(query, fixer)
    text, markup = query.message.edits[-1]
    assert "Автовыставление: вкл" in text
    assert any(b.text.endswith("🟢") for row in markup.inline_keyboard for b in row)
    assert cached.keep_in_sale is True  # в списке раздела 🔁 появится сразу
    _, section_markup = items_panel.build_section_items(make_fixer().l10n, items_panel.cache.peek(), 0)
    assert section_markup.inline_keyboard[0][0].text.endswith("🔁")


def test_comment_comes_from_item_data_fields():
    from fixer.tg.handlers.items import comment_field
    from playerokapi.common.enums import GameCategoryDataFieldTypes
    field = SimpleNamespace(id="f-1", label="Комментарий", type=GameCategoryDataFieldTypes.ITEM_DATA,
                            value="Ссылка: https://drive.google.com/x")
    item = lot(1, comment=None, data_fields=[field])
    assert comment_field(item) == ("f-1", "Ссылка: https://drive.google.com/x")
    text, _ = items_panel.build_item_card(make_fixer().l10n, item, "выкл")
    assert "drive.google.com" in text and "Комментария нет" not in text


async def test_comment_saved_into_data_field_like_site():
    import time

    from playerokapi.common.enums import GameCategoryDataFieldTypes
    field = SimpleNamespace(id="f-1", label="Комментарий", type=GameCategoryDataFieldTypes.ITEM_DATA, value="old")
    fixer = fixer_with_item(lot(1, comment=None, data_fields=[field]))
    edits = []

    class Bot:
        async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
            edits.append(text)

    class State:
        data = {"item_id": "it-1", "since": time.time(), "panel": [1, 9]}

        async def get_data(self):
            return dict(self.data)

        async def get_state(self):
            return items_panel.ItemEdit.comment.state

        async def clear(self):
            pass

    class Msg:
        text, reply_to_message, bot = "Новая ссылка", None, Bot()
        chat, message_id = SimpleNamespace(id=1), 5

        async def delete(self):
            pass

    await items_panel.on_edit_value(Msg(), State(), fixer)
    assert fixer.account.calls == [("update", "it-1", {"data_fields": {"f-1": "Новая ссылка"}})]
    assert "Новая ссылка" in edits[-1] and "На модерации" in edits[-1]
