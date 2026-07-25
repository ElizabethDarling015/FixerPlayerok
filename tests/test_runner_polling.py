"""Тесты поллинга Runner: флаги инициализации, переход в PAID, дедуп, пагинация."""
from types import SimpleNamespace

from conftest import FakeAccount, drain_events, make_deal, make_page

from playerokapi.updater import events
from playerokapi.updater.runner import Runner


def make_runner(account=None):
    return Runner(account or FakeAccount())


def set_deal_pages(account, pages_by_cursor):
    """Настраивает account.get_deals на курсорную пагинацию по словарю {cursor: page}."""
    account.get_deals = lambda count=50, after_cursor=None: pages_by_cursor.get(after_cursor)


def test_empty_first_snapshot_does_not_swallow_first_event():
    account = FakeAccount()
    runner = make_runner(account)

    # Первый опрос — пустой снимок (сделок нет вообще).
    set_deal_pages(account, {None: make_page([])})
    runner._poll_deals()
    assert drain_events(runner) == []

    # Второй опрос — появилась первая сделка: событие НЕ должно быть проглочено.
    deal = make_deal(status="PENDING")
    set_deal_pages(account, {None: make_page([deal])})
    runner._poll_deals()
    emitted = drain_events(runner)
    assert any(isinstance(e, events.NewDealEvent) for e in emitted)


def test_first_snapshot_with_deals_emits_nothing():
    account = FakeAccount()
    runner = make_runner(account)
    set_deal_pages(account, {None: make_page([make_deal(status="SENT")])})
    runner._poll_deals()
    assert drain_events(runner) == []


def test_transition_to_paid_emits_item_paid():
    account = FakeAccount()
    runner = make_runner(account)

    deal = make_deal(status="PENDING")
    set_deal_pages(account, {None: make_page([deal])})
    runner._poll_deals()
    drain_events(runner)

    deal_paid = make_deal(status="PAID")
    set_deal_pages(account, {None: make_page([deal_paid])})
    runner._poll_deals()
    emitted = drain_events(runner)
    assert any(isinstance(e, events.DealStatusChangedEvent) for e in emitted)
    assert any(isinstance(e, events.ItemPaidEvent) for e in emitted)


def test_first_poll_paid_deal_is_seeded_without_event():
    account = FakeAccount()
    runner = make_runner(account)
    deal = make_deal(status="PAID")
    set_deal_pages(account, {None: make_page([deal])})
    runner._poll_deals()

    assert drain_events(runner) == []
    # Сделка зарегистрирована как оплаченная — повторная оплата не эмитится.
    assert deal.id in runner._paid_deal_ids
    runner._emit_item_paid(deal.chat, None, deal)
    assert drain_events(runner) == []


def test_item_paid_dedup_between_ws_and_poll():
    runner = make_runner()
    deal = make_deal(status="PAID")

    # WS-маркер и поллинг замечают одну и ту же оплату.
    runner._emit_item_paid(deal.chat, None, deal)
    runner._emit_item_paid(deal.chat, None, deal)

    emitted = drain_events(runner)
    assert len([e for e in emitted if isinstance(e, events.ItemPaidEvent)]) == 1


def test_poll_deals_pagination_collects_all_pages():
    account = FakeAccount()
    runner = make_runner(account)

    deal_a = make_deal(deal_id="deal-a", status="SENT")
    deal_b = make_deal(deal_id="deal-b", status="SENT")
    set_deal_pages(account, {
        None: make_page([deal_a], has_next_page=True, end_cursor="cursor-1"),
        "cursor-1": make_page([deal_b]),
    })
    runner._poll_deals()

    assert set(runner._known_deals) == {"deal-a", "deal-b"}


def test_pagination_stops_on_stagnant_cursor():
    account = FakeAccount()
    runner = make_runner(account)

    deal = make_deal(deal_id="deal-a", status="SENT")
    # Сервер "завис": has_next_page=True, но курсор не двигается.
    set_deal_pages(account, {None: make_page([deal], has_next_page=True, end_cursor=None)})
    runner._poll_deals()  # не должен зациклиться

    assert set(runner._known_deals) == {"deal-a"}


def test_poll_reviews_empty_first_snapshot():
    account = FakeAccount()
    runner = make_runner(account)

    account.get_my_reviews = lambda count=50, after_cursor=None: make_page([], field="reviews")
    runner._poll_reviews()
    assert drain_events(runner) == []

    review = SimpleNamespace(id="review-1")
    account.get_my_reviews = lambda count=50, after_cursor=None: make_page([review], field="reviews")
    runner._poll_reviews()
    emitted = drain_events(runner)
    assert any(isinstance(e, events.NewReviewEvent) for e in emitted)


def test_poll_error_keeps_snapshot_uninitialized():
    account = FakeAccount()
    runner = make_runner(account)

    def failing(count=50, after_cursor=None):
        raise RuntimeError("network down")

    account.get_deals = failing
    runner._poll_deals()  # ignore_exceptions=True по умолчанию
    assert runner._deals_initialized is False
    assert drain_events(runner) == []
