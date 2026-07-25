"""Тесты модуля автовосстановления лотов Cardinal (`cardinal.modules.autorestore`)."""
from types import SimpleNamespace

import pytest

from cardinal.modules.autorestore import AutoRestoreModule, RestoreError, RestoreResult
from cardinal.settings import AutoDeliveryLot
from playerokapi.common.enums import (
    GameCategoryDataFieldTypes,
    ItemDealDirections,
    ItemStatuses,
    PriorityTypes,
)
from playerokapi.updater.events import ItemPaidEvent

from cardinal_helpers import make_cardinal, make_chat


class FakeNotifier:
    def __init__(self):
        self.stock_empty: list[str] = []
        self.restored: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str]] = []
        self.premium_fallback: list[tuple[str, str, str]] = []

    async def notify_stock_empty(self, item_name):
        self.stock_empty.append(item_name)

    async def notify_restore_ok(self, item_name, new_item_id):
        self.restored.append((item_name, new_item_id))

    async def notify_restore_failed(self, item_name, error):
        self.failed.append((item_name, error))

    async def notify_restore_premium_fallback(self, item_name, new_item_id, reason):
        self.premium_fallback.append((item_name, new_item_id, reason))


def make_sold_item(item_id="item-1", name="Лот", priority=PriorityTypes.DEFAULT):
    return SimpleNamespace(
        id=item_id,
        name=name,
        price=100,
        description="описание",
        comment=None,
        status=ItemStatuses.SOLD,
        priority=priority,
        game=SimpleNamespace(id="game-1"),
        category=SimpleNamespace(id="cat-1"),
        obtaining_type=SimpleNamespace(id="obt-1"),
        data_fields=[
            SimpleNamespace(id="f1", value="логин", type=GameCategoryDataFieldTypes.ITEM_DATA),
            SimpleNamespace(id="f2", value=None, type=GameCategoryDataFieldTypes.ITEM_DATA),
            SimpleNamespace(id="f3", value="почта", type=GameCategoryDataFieldTypes.OBTAINING_DATA),
        ],
    )


def setup_module_env(sold_item, lot: AutoDeliveryLot, *, balance_available=10_000,
                     statuses=None, publish_premium_error=None):
    cardinal = make_cardinal()
    cardinal.settings.modules.autorestore = True
    cardinal.autodelivery_config.lots[sold_item.name] = lot
    cardinal.notifier = FakeNotifier()

    account = cardinal.account
    account.calls = []
    account.get_item = lambda id=None, slug=None: sold_item
    account.create_item = lambda **kwargs: (account.calls.append(("create", kwargs)),
                                            SimpleNamespace(id="new-item", price=100))[1]
    account.get_balance = lambda: SimpleNamespace(value=balance_available, available=balance_available)
    if statuses is None:
        statuses = [
            SimpleNamespace(id="ps-default", type=PriorityTypes.DEFAULT, price=0),
            SimpleNamespace(id="ps-premium", type=PriorityTypes.PREMIUM, price=50),
        ]
    account.get_item_priority_statuses = lambda item_id, price: statuses

    def publish_item(item_id, priority_status_id=None, provider_id="LOCAL"):
        account.calls.append(("publish", item_id, priority_status_id))
        if publish_premium_error and priority_status_id == "ps-premium":
            raise publish_premium_error
        return SimpleNamespace(id="published-item")

    account.publish_item = publish_item
    return AutoRestoreModule(cardinal), cardinal


def make_paid_event(item, direction=ItemDealDirections.OUT):
    deal = SimpleNamespace(id="deal-1", direction=direction,
                           item=SimpleNamespace(id=item.id, name=item.name),
                           user=SimpleNamespace(username="buyer"))
    return ItemPaidEvent(None, make_chat(), None, deal)


async def test_restores_sold_item_with_default_priority():
    item = make_sold_item(priority=PriorityTypes.DEFAULT)
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))

    await module.on_event(make_paid_event(item))

    create_call = next(c for c in cardinal.account.calls if c[0] == "create")
    kwargs = create_call[1]
    assert kwargs["game_id"] == "game-1" and kwargs["category_id"] == "cat-1"
    assert kwargs["name"] == "Лот" and kwargs["price"] == 100
    assert kwargs["data_fields"] == {"f1": "логин"}
    publish_call = next(c for c in cardinal.account.calls if c[0] == "publish")
    assert publish_call[1] == "new-item" and publish_call[2] == "ps-default"
    assert cardinal.notifier.restored == [("Лот", "published-item")]
    assert cardinal.notifier.premium_fallback == []


async def test_restores_with_same_premium_priority():
    item = make_sold_item(priority=PriorityTypes.PREMIUM)
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))

    await module.on_event(make_paid_event(item))

    publish_calls = [c for c in cardinal.account.calls if c[0] == "publish"]
    assert publish_calls == [("publish", "new-item", "ps-premium")]
    assert cardinal.notifier.restored == [("Лот", "published-item")]
    assert cardinal.notifier.premium_fallback == []


async def test_premium_falls_back_when_balance_low():
    item = make_sold_item(priority=PriorityTypes.PREMIUM)
    module, cardinal = setup_module_env(
        item, AutoDeliveryLot(stock_file="s.txt", restore=True), balance_available=10,
    )

    await module.on_event(make_paid_event(item))

    publish_calls = [c for c in cardinal.account.calls if c[0] == "publish"]
    assert publish_calls == [("publish", "new-item", "ps-default")]
    assert cardinal.notifier.restored == []
    assert len(cardinal.notifier.premium_fallback) == 1
    name, item_id, reason = cardinal.notifier.premium_fallback[0]
    assert name == "Лот" and item_id == "published-item"
    assert "баланса" in reason


async def test_premium_falls_back_when_publish_raises():
    item = make_sold_item(priority=PriorityTypes.PREMIUM)
    module, cardinal = setup_module_env(
        item, AutoDeliveryLot(stock_file="s.txt", restore=True),
        publish_premium_error=RuntimeError("insufficient funds"),
    )

    await module.on_event(make_paid_event(item))

    publish_calls = [c for c in cardinal.account.calls if c[0] == "publish"]
    assert publish_calls == [
        ("publish", "new-item", "ps-premium"),
        ("publish", "new-item", "ps-default"),
    ]
    assert len(cardinal.notifier.premium_fallback) == 1
    assert "insufficient funds" in cardinal.notifier.premium_fallback[0][2]


async def test_premium_falls_back_when_premium_status_missing():
    item = make_sold_item(priority=PriorityTypes.PREMIUM)
    module, cardinal = setup_module_env(
        item, AutoDeliveryLot(stock_file="s.txt", restore=True),
        statuses=[SimpleNamespace(id="ps-default", type=PriorityTypes.DEFAULT, price=0)],
    )

    await module.on_event(make_paid_event(item))

    publish_calls = [c for c in cardinal.account.calls if c[0] == "publish"]
    assert publish_calls == [("publish", "new-item", "ps-default")]
    assert "премиум" in cardinal.notifier.premium_fallback[0][2].lower()


async def test_no_priority_defaults_to_free():
    item = make_sold_item(priority=None)
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))
    result = module.restore_item(item.id)
    assert isinstance(result, RestoreResult)
    assert result.used_priority is PriorityTypes.DEFAULT
    assert result.fallback_from_premium is False


async def test_no_restore_without_flag():
    item = make_sold_item()
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=False))
    await module.on_event(make_paid_event(item))
    assert cardinal.account.calls == []


async def test_no_restore_for_incoming_deal():
    item = make_sold_item()
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))
    await module.on_event(make_paid_event(item, direction=ItemDealDirections.IN))
    assert cardinal.account.calls == []


async def test_empty_stock_with_deactivation_skips_restore():
    item = make_sold_item()
    module, cardinal = setup_module_env(
        item, AutoDeliveryLot(stock_file="s.txt", restore=True, deactivate_when_empty=True))
    cardinal.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 0)

    await module.on_event(make_paid_event(item))

    assert cardinal.account.calls == []
    assert cardinal.notifier.stock_empty == ["Лот"]


async def test_restore_failure_notifies():
    item = make_sold_item()
    item.status = ItemStatuses.APPROVED  # не продан — восстановление должно упасть
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))

    await module.on_event(make_paid_event(item))

    assert cardinal.notifier.restored == []
    assert len(cardinal.notifier.failed) == 1
    assert "SOLD" in cardinal.notifier.failed[0][1]


def test_restore_item_requires_game_and_category():
    item = make_sold_item()
    item.game = None
    module, cardinal = setup_module_env(item, AutoDeliveryLot(stock_file="s.txt", restore=True))
    with pytest.raises(RestoreError, match="игре/категории"):
        module.restore_item(item.id)
