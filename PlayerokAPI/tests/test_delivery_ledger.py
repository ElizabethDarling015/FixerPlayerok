"""Тесты SQLite-журнала авто-выдачи (`delivery_ledger.DeliveryLedger`)."""
from playerokapi.delivery_ledger import DeliveryLedger


def test_try_mark_seen_paid_dedup(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "ledger.sqlite3"))
    assert ledger.try_mark_seen_paid("deal-1", "Лот") is True
    # Повторная отметка той же сделки — дубль.
    assert ledger.try_mark_seen_paid("deal-1", "Лот") is False
    assert ledger.get_state("deal-1") == "seen_paid"


def test_state_transitions(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "ledger.sqlite3"))
    ledger.try_mark_seen_paid("deal-1", "Лот")
    ledger.mark_reserved("deal-1", "Лот")
    assert ledger.get_state("deal-1") == "reserved"
    ledger.mark_sent("deal-1")
    assert ledger.get_state("deal-1") == "sent"

    ledger.mark_reserved("deal-2", "Лот 2")
    ledger.mark_restored("deal-2")
    assert ledger.get_state("deal-2") == "restored"


def test_seen_paid_after_terminal_state_is_still_dedup(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "ledger.sqlite3"))
    ledger.mark_sent("deal-1")
    # Сделка уже в журнале (в любом состоянии) — событие оплаты не должно эмититься повторно.
    assert ledger.try_mark_seen_paid("deal-1") is False
    assert ledger.get_state("deal-1") == "sent"


def test_deals_in_state(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "ledger.sqlite3"))
    ledger.mark_reserved("deal-1", "Лот 1")
    ledger.mark_reserved("deal-2", "Лот 2")
    ledger.mark_sent("deal-2")

    stuck = ledger.deals_in_state("reserved")
    assert stuck == [("deal-1", "Лот 1")]


def test_persistence_across_restart(tmp_path):
    path = str(tmp_path / "ledger.sqlite3")
    first = DeliveryLedger(path)
    first.try_mark_seen_paid("deal-1", "Лот")
    first.mark_reserved("deal-1", "Лот")
    first.close()

    # "Перезапуск процесса": новый объект над тем же файлом видит прежнее состояние.
    second = DeliveryLedger(path)
    assert second.get_state("deal-1") == "reserved"
    assert second.deals_in_state("reserved") == [("deal-1", "Лот")]
    assert second.try_mark_seen_paid("deal-1") is False
