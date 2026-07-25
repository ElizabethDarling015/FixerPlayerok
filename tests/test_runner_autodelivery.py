"""Тесты авто-выдачи через Runner: одна выдача на сделку, restore при сбое, direction, рестарт."""
import logging
from types import SimpleNamespace

import pytest

from conftest import FakeAccount, drain_events, make_deal

from playerokapi.autodelivery import AutoDeliveryManager
from playerokapi.common.enums import ItemDealDirections
from playerokapi.updater import events
from playerokapi.updater.runner import Runner


@pytest.fixture
def env(tmp_path):
    stock = tmp_path / "stock.txt"
    stock.write_text("SECRET-1\nSECRET-2\n", encoding="utf-8")
    manager = AutoDeliveryManager(
        config={"Лот": str(stock)},
        ledger_path=str(tmp_path / "ledger.sqlite3"),
    )
    account = FakeAccount()
    runner = Runner(account, autodelivery_manager=manager)
    return SimpleNamespace(stock=stock, manager=manager, account=account, runner=runner,
                           tmp_path=tmp_path)


def paid_event(runner, deal):
    return events.ItemPaidEvent(runner, deal.chat, None, deal)


def test_ws_and_poll_duplicate_leads_to_single_delivery(env):
    deal = make_deal(direction=ItemDealDirections.OUT)

    # Оплату замечают оба источника: WS-маркер и поллинг.
    env.runner._emit_item_paid(deal.chat, None, deal)
    env.runner._emit_item_paid(deal.chat, None, deal)
    emitted = [e for e in drain_events(env.runner) if isinstance(e, events.ItemPaidEvent)]
    assert len(emitted) == 1

    env.runner._handle_autodelivery(emitted[0])
    assert env.account.sent_messages == [("chat-1", env.manager.format_delivery_text("SECRET-1"))]
    assert env.stock.read_text(encoding="utf-8") == "SECRET-2\n"
    assert env.manager.ledger.get_state(deal.id) == "sent"

    # Даже если событие каким-то образом дошло второй раз — журнал не даст выдать повторно.
    env.runner._handle_autodelivery(paid_event(env.runner, deal))
    assert len(env.account.sent_messages) == 1


def test_send_failure_restores_stock_and_marks_ledger(env):
    deal = make_deal(direction=ItemDealDirections.OUT)

    def failing_send(chat_id, text=None, **kwargs):
        raise RuntimeError("network down")

    env.account.send_message = failing_send
    env.runner._handle_autodelivery(paid_event(env.runner, deal))

    # Товар вернулся на склад (в начало файла), журнал зафиксировал restored.
    assert env.stock.read_text(encoding="utf-8") == "SECRET-1\nSECRET-2\n"
    assert env.manager.ledger.get_state(deal.id) == "restored"


def test_incoming_deal_is_not_delivered(env):
    deal = make_deal(direction=ItemDealDirections.IN)
    env.runner._handle_autodelivery(paid_event(env.runner, deal))

    assert env.account.sent_messages == []
    assert env.stock.read_text(encoding="utf-8") == "SECRET-1\nSECRET-2\n"


def test_restart_does_not_redeliver_seen_deal(env, tmp_path):
    deal = make_deal(direction=ItemDealDirections.OUT)
    emitted_event = None
    env.runner._emit_item_paid(deal.chat, None, deal)
    emitted_event = drain_events(env.runner)[0]
    env.runner._handle_autodelivery(emitted_event)
    assert len(env.account.sent_messages) == 1

    # "Перезапуск процесса": новые Runner/менеджер над тем же файлом журнала.
    manager2 = AutoDeliveryManager(
        config={"Лот": str(env.stock)},
        ledger_path=str(tmp_path / "ledger.sqlite3"),
    )
    account2 = FakeAccount()
    runner2 = Runner(account2, autodelivery_manager=manager2)

    # Та же оплата замечена снова (например, поллинг видит PAID-переход при старте).
    runner2._emit_item_paid(deal.chat, None, deal)
    assert drain_events(runner2) == []
    assert account2.sent_messages == []


def test_stuck_reserved_deal_logged_on_start(env, tmp_path, caplog):
    env.manager.ledger.mark_reserved("deal-stuck", "Лот")

    with caplog.at_level(logging.ERROR, logger="playerokapi.runner"):
        env.runner._warn_about_stuck_deliveries()

    assert "deal-stuck" in caplog.text
    # Авто-повтора выдачи нет.
    assert env.account.sent_messages == []


def test_delivery_log_does_not_leak_secret(env, caplog):
    deal = make_deal(direction=ItemDealDirections.OUT)
    with caplog.at_level(logging.DEBUG):
        env.runner._handle_autodelivery(paid_event(env.runner, deal))
    assert "SECRET-1" not in caplog.text
