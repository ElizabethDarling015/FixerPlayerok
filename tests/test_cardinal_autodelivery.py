"""
Тесты улучшений авто-выдачи Cardinal: выбор лота из списка Playerok, тест выдачи
без покупки и автоснятие лота с публикации при пустом складе.
"""
from types import SimpleNamespace

import pytest

from playerokapi.autodelivery import AutoDeliveryManager
from playerokapi.common.enums import ItemDealDirections, ItemStatuses
from playerokapi.updater.events import ItemPaidEvent

from cardinal.core import Cardinal
from cardinal.settings import AutoDeliveryLot
from cardinal.tg.handlers.autodelivery import (
    build_lot_view,
    build_lots_list,
    build_pick_list,
    create_lot,
    fetch_my_item_names,
    simulate_delivery,
)

from cardinal_helpers import make_cardinal, make_settings


def all_callback_data(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def make_manager(tmp_path, lines=("SECRET-1", "SECRET-2"), ledger_path=None, **kwargs):
    stock = tmp_path / "stock.txt"
    stock.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    manager = AutoDeliveryManager(config={"Лот": str(stock)}, ledger_path=ledger_path, **kwargs)
    return manager, stock


# ----------------------------------------------------------------------
# Привязка лота выбором из списка с площадки
# ----------------------------------------------------------------------

def make_items_page(names, has_next_page=False, end_cursor=None):
    return SimpleNamespace(
        items=[SimpleNamespace(id=f"id-{name}", name=name) for name in names],
        page_info=SimpleNamespace(has_next_page=has_next_page, end_cursor=end_cursor),
    )


async def test_fetch_my_item_names_paginates_and_dedupes():
    cardinal = make_cardinal()
    calls = []

    def get_my_items(status=None, count=20, after_cursor=None):
        calls.append((status, after_cursor))
        if after_cursor is None:
            return make_items_page(["Лот А", "Лот Б"], has_next_page=True, end_cursor="cur-1")
        return make_items_page(["Лот Б", "Лот В"])

    cardinal.account.get_my_items = get_my_items
    names = await fetch_my_item_names(cardinal)

    assert names == ["Лот А", "Лот Б", "Лот В"]  # повтор со второй страницы отброшен
    assert calls == [(ItemStatuses.APPROVED, None), (ItemStatuses.APPROVED, "cur-1")]


async def test_fetch_my_item_names_stops_on_stuck_cursor():
    cardinal = make_cardinal()
    cardinal.account.get_my_items = lambda **kwargs: make_items_page(
        ["Лот А"], has_next_page=True, end_cursor=None)
    assert await fetch_my_item_names(cardinal) == ["Лот А"]


def test_pick_list_marks_configured_lots():
    cardinal = make_cardinal()
    cardinal.autodelivery_config.lots["Лот Б"] = AutoDeliveryLot(stock_file="b.txt")

    text, markup = build_pick_list(cardinal, ["Лот А", "Лот Б"])
    assert "Playerok" in text
    buttons = [button for row in markup.inline_keyboard for button in row]
    assert [b.callback_data for b in buttons][:2] == ["ad:pickadd:0", "ad:pickadd:1"]
    assert buttons[0].text == "Лот А" and buttons[1].text.startswith("✅")


def test_pick_list_paginates():
    cardinal = make_cardinal()
    names = [f"Лот {i:02d}" for i in range(13)]
    _, markup = build_pick_list(cardinal, names, page=1)
    callbacks = all_callback_data(markup)
    assert "ad:pickadd:10" in callbacks and "ad:pickadd:0" not in callbacks
    assert "ad:pickp:0" in callbacks


def test_pick_list_empty_message():
    cardinal = make_cardinal()
    text, markup = build_pick_list(cardinal, [])
    assert text == cardinal.l10n("ad_pick_empty")
    assert not any(cb.startswith("ad:pickadd") for cb in all_callback_data(markup))


def test_create_lot_writes_exact_name_and_stock_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cardinal = make_cardinal()
    saved = []
    cardinal.apply_autodelivery_config = lambda: None
    monkeypatch.setattr("cardinal.tg.handlers.autodelivery.save_autodelivery_config",
                        lambda config: saved.append(config))

    stock_file = create_lot(cardinal, "Лот «А» / 100 шт.")

    lot = cardinal.autodelivery_config.lots["Лот «А» / 100 шт."]  # имя сохранено дословно
    assert lot.stock_file == stock_file
    assert (tmp_path / stock_file).is_file()  # склад создан пустым файлом
    assert lot.delivery_text is None and lot.disable_deactivate is False
    assert saved == [cardinal.autodelivery_config]


def test_lots_list_has_pick_button_and_global_deactivate_toggle():
    cardinal = make_cardinal()
    _, markup = build_lots_list(cardinal)
    callbacks = all_callback_data(markup)
    assert "ad:pick" in callbacks and "ad:autodeact" in callbacks


def test_lot_view_has_test_and_per_lot_text_buttons():
    cardinal = make_cardinal()
    cardinal.autodelivery_config.lots["Лот"] = AutoDeliveryLot(stock_file="s.txt",
                                                               delivery_text="Свой: {item}")
    cardinal.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 2)
    text, markup = build_lot_view(cardinal, 0)
    callbacks = all_callback_data(markup)
    assert "ad:test:0" in callbacks and "ad:ltext:0" in callbacks and "ad:nodeact:0" in callbacks
    assert "🟢" in text  # свой текст выдачи задан


# ----------------------------------------------------------------------
# Тест выдачи без покупки
# ----------------------------------------------------------------------

def test_simulate_delivery_returns_item_to_stock(tmp_path):
    manager, stock = make_manager(tmp_path, ledger_path=str(tmp_path / "ledger.sqlite3"))
    manager.delivery_text_template = "Ваш товар: {item}"

    result = simulate_delivery(manager, "Лот")

    assert result == ("Ваш товар: SECRET-1", 1)  # остаток, каким он был бы после выдачи
    # Товар вернулся на склад в том же порядке — покупателям ничего не «съедено».
    assert stock.read_text(encoding="utf-8") == "SECRET-1\nSECRET-2\n"
    assert manager.get_stock_size("Лот") == 2
    # Журнал выдач не засорён: ни одной записи о сделке.
    assert manager.ledger.deals_in_state("reserved") == []
    assert manager.ledger.deals_in_state("sent") == []


def test_simulate_delivery_uses_lot_template(tmp_path):
    manager, _ = make_manager(tmp_path, delivery_texts={"Лот": "Личный: {item}"})
    text, _ = simulate_delivery(manager, "Лот")
    assert text == "Личный: SECRET-1"


def test_simulate_delivery_on_empty_stock(tmp_path):
    manager, _ = make_manager(tmp_path, lines=())
    assert simulate_delivery(manager, "Лот") is None


def test_simulate_delivery_returns_item_even_on_format_error(tmp_path):
    manager, stock = make_manager(tmp_path)
    manager.delivery_text_template = "{неизвестный_плейсхолдер}"
    with pytest.raises(KeyError):
        simulate_delivery(manager, "Лот")
    assert stock.read_text(encoding="utf-8") == "SECRET-1\nSECRET-2\n"


# ----------------------------------------------------------------------
# Автодеактивация лота при пустом складе
# ----------------------------------------------------------------------

class FakeNotifier:
    def __init__(self):
        self.deactivated: list[str] = []
        self.failed: list[tuple[str, str]] = []

    async def notify_lot_deactivated(self, item_name):
        self.deactivated.append(item_name)

    async def notify_deactivate_failed(self, item_name, error_text):
        self.failed.append((item_name, error_text))


def make_core(tmp_path, stock_lines=(), deactivate_on_empty=True, lot=None, remove_error=None):
    settings = make_settings(autodelivery={"deactivate_on_empty": deactivate_on_empty})
    cardinal = Cardinal(settings)
    manager, _ = make_manager(tmp_path, lines=stock_lines)
    cardinal.autodelivery_manager = manager
    cardinal.autodelivery_config.lots = {"Лот": lot or AutoDeliveryLot(stock_file="s.txt")}
    cardinal.notifier = FakeNotifier()

    removed: list[str] = []

    def remove_item(item_id):
        if remove_error is not None:
            raise remove_error
        removed.append(item_id)
        return True

    cardinal.account = SimpleNamespace(
        get_my_items=lambda status=None, count=20, after_cursor=None: make_items_page(
            ["Лот", "Другой лот"]),
        remove_item=remove_item,
    )
    cardinal.removed = removed
    return cardinal


def paid_event(item_name="Лот", direction=ItemDealDirections.OUT):
    deal = SimpleNamespace(id="deal-1", direction=direction,
                           item=SimpleNamespace(id="id-1", name=item_name),
                           user=SimpleNamespace(username="buyer"))
    return ItemPaidEvent(None, SimpleNamespace(id="chat-1"), None, deal)


async def test_deactivates_lot_when_stock_is_empty(tmp_path):
    cardinal = make_core(tmp_path, stock_lines=())
    await cardinal.maybe_deactivate_empty_lot(paid_event())
    # Снят только лот с совпадающим названием.
    assert cardinal.removed == ["id-Лот"]
    assert cardinal.notifier.deactivated == ["Лот"]


async def test_does_not_deactivate_when_stock_left(tmp_path):
    cardinal = make_core(tmp_path, stock_lines=("SECRET-1",))
    await cardinal.maybe_deactivate_empty_lot(paid_event())
    assert cardinal.removed == [] and cardinal.notifier.deactivated == []


async def test_does_not_deactivate_when_setting_off(tmp_path):
    cardinal = make_core(tmp_path, deactivate_on_empty=False)
    await cardinal.maybe_deactivate_empty_lot(paid_event())
    assert cardinal.removed == []


async def test_does_not_deactivate_when_lot_flag_disables_it(tmp_path):
    cardinal = make_core(tmp_path, lot=AutoDeliveryLot(stock_file="s.txt", disable_deactivate=True))
    await cardinal.maybe_deactivate_empty_lot(paid_event())
    assert cardinal.removed == []


async def test_does_not_deactivate_unknown_lot_or_own_purchase(tmp_path):
    cardinal = make_core(tmp_path)
    await cardinal.maybe_deactivate_empty_lot(paid_event(item_name="Чужой лот"))
    await cardinal.maybe_deactivate_empty_lot(paid_event(direction=ItemDealDirections.IN))
    assert cardinal.removed == []


async def test_deactivation_error_is_reported_and_swallowed(tmp_path):
    cardinal = make_core(tmp_path, remove_error=RuntimeError("сеть недоступна"))
    await cardinal.maybe_deactivate_empty_lot(paid_event())  # не должно бросить наружу
    assert cardinal.removed == []
    assert cardinal.notifier.failed == [("Лот", "сеть недоступна")]
    assert cardinal.notifier.deactivated == []


def test_find_published_item_ids_follows_pagination(tmp_path):
    cardinal = make_core(tmp_path)
    pages = {
        None: make_items_page(["Лот", "Другой"], has_next_page=True, end_cursor="cur-1"),
        "cur-1": make_items_page(["Лот"]),
    }
    cardinal.account.get_my_items = lambda status=None, count=20, after_cursor=None: pages[after_cursor]
    assert cardinal.find_published_item_ids("Лот") == ["id-Лот", "id-Лот"]


async def test_apply_autodelivery_config_syncs_per_lot_texts(tmp_path):
    cardinal = make_core(tmp_path)
    cardinal.autodelivery_config.lots = {
        "Лот": AutoDeliveryLot(stock_file="s.txt", delivery_text="Личный: {item}"),
        "Второй": AutoDeliveryLot(stock_file="s2.txt"),
    }
    cardinal.apply_autodelivery_config()
    assert cardinal.autodelivery_manager.delivery_texts == {"Лот": "Личный: {item}"}
    assert set(cardinal.autodelivery_manager.stock_paths) == {"Лот", "Второй"}
