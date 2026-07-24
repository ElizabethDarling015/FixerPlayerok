"""Тесты AutoRaiseManager: item_ids=[], balance.available, ошибка баланса, проверка результата."""
from types import SimpleNamespace

from playerokapi.autoraise import AutoRaiseManager
from playerokapi.common.enums import PriorityTypes, TransactionProviderIds


class FakeRaiseAccount:
    def __init__(self, items=None, available=100, value=500):
        self._items = items if items is not None else [
            SimpleNamespace(id="item-1", name="Лот 1", price=100),
        ]
        self._balance = SimpleNamespace(available=available, value=value)
        self.raise_calls = []
        self.statuses = [SimpleNamespace(id="ps-premium", type=PriorityTypes.PREMIUM, price=50)]
        self.raise_result = SimpleNamespace(id="item-1", name="Лот 1", priority="PREMIUM")

    def get_my_items(self, status=None, count=50, after_cursor=None):
        return SimpleNamespace(
            items=self._items,
            page_info=SimpleNamespace(has_next_page=False, end_cursor=None),
        )

    def get_balance(self):
        return self._balance

    def get_item_priority_statuses(self, item_id, price):
        return self.statuses

    def increase_item_priority_status(self, item_id, priority_status_id, provider_id="LOCAL"):
        self.raise_calls.append((item_id, priority_status_id, provider_id))
        return self.raise_result


def test_empty_item_ids_means_raise_nothing():
    account = FakeRaiseAccount()
    manager = AutoRaiseManager(item_ids=[])
    results = manager.raise_all(account)
    assert results == []
    assert account.raise_calls == []


def test_none_item_ids_means_all_items():
    account = FakeRaiseAccount()
    manager = AutoRaiseManager(item_ids=None)
    results = manager.raise_all(account)
    assert len(results) == 1
    assert results[0].raised is True
    assert account.raise_calls == [("item-1", "ps-premium", "LOCAL")]


def test_uses_available_balance_not_value():
    # value=500 (много), но available=30 < цены 50 — поднимать нельзя.
    account = FakeRaiseAccount(available=30, value=500)
    manager = AutoRaiseManager()
    results = manager.raise_all(account)

    assert len(results) == 1
    assert results[0].raised is False
    assert results[0].skipped_reason == "insufficient_balance"
    assert results[0].available == 30
    assert account.raise_calls == []


def test_balance_error_skips_whole_cycle():
    account = FakeRaiseAccount()

    def failing_balance():
        raise RuntimeError("network down")

    account.get_balance = failing_balance
    manager = AutoRaiseManager()
    results = manager.raise_all(account)

    # Ошибка запроса баланса — не «нет денег»: цикл пропущен без ложных событий.
    assert results == []
    assert account.raise_calls == []


def test_unconfirmed_mutation_is_not_counted_as_raised():
    account = FakeRaiseAccount()
    account.raise_result = None  # сервер не вернул обновлённый лот
    manager = AutoRaiseManager()
    results = manager.raise_all(account)

    assert len(results) == 1
    assert results[0].raised is False
    assert results[0].skipped_reason == "raise_error"


def test_provider_id_normalized_from_enum():
    manager = AutoRaiseManager(provider_id=TransactionProviderIds.LOCAL)
    assert manager.provider_id == "LOCAL"

    account = FakeRaiseAccount()
    manager.raise_all(account)
    assert account.raise_calls == [("item-1", "ps-premium", "LOCAL")]


def test_min_balance_reserve_respected():
    account = FakeRaiseAccount(available=60)
    manager = AutoRaiseManager(min_balance_reserve=20)  # 60 - 20 = 40 < 50
    results = manager.raise_all(account)
    assert results[0].skipped_reason == "insufficient_balance"
