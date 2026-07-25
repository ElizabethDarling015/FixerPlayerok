"""Тесты билдеров TG-панели Cardinal (меню, разделы) — чистые функции без сети."""
from types import SimpleNamespace

from cardinal.settings import AutoDeliveryLot
from cardinal.tg.handlers.autodelivery import build_lot_view, build_lots_list, build_stock_view
from cardinal.tg.handlers.autoresponse import build_commands_list
from cardinal.tg.handlers.common import PAGE_SIZE, paginate, pager_row
from cardinal.tg.handlers.menu import MODULE_NAMES, build_main_menu, build_toggles_menu
from cardinal.tg.handlers.notifications import NOTIFICATION_KEYS, build_notifications_menu
from cardinal.tg.handlers.plugins_panel import build_plugins_menu

from cardinal_helpers import make_cardinal


def all_callback_data(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_main_menu_contains_status_and_sections():
    cardinal = make_cardinal()
    text, markup = build_main_menu(cardinal)
    assert "seller" in text and "100" in text  # аккаунт и баланс
    callbacks = all_callback_data(markup)
    # Тумблеры модулей переехали в подменю «Глобальные переключатели».
    assert not any(cb.startswith("mod:") for cb in callbacks)
    for section in ("gl", "ad", "ar", "bl", "nt", "pl", "st", "sys"):
        assert section in callbacks


def test_toggles_menu_contains_all_modules_and_greeting():
    cardinal = make_cardinal()
    text, markup = build_toggles_menu(cardinal)
    callbacks = all_callback_data(markup)
    for name in MODULE_NAMES:
        assert f"mod:{name}" in callbacks
    assert "gl:greet" in callbacks
    assert "menu" in callbacks  # кнопка «Главное меню»


def test_paginate_clamps_and_slices():
    items = list(range(25))
    page_items, page, total_pages, start = paginate(items, 0)
    assert page_items == list(range(10)) and total_pages == 3 and start == 0
    page_items, page, total_pages, start = paginate(items, 2)
    assert page_items == [20, 21, 22, 23, 24] and start == 20
    # Выход за границы зажимается.
    page_items, page, _, _ = paginate(items, 99)
    assert page == 2 and page_items[-1] == 24
    page_items, page, total_pages, _ = paginate([], 5)
    assert page_items == [] and page == 0 and total_pages == 1


def test_pager_row_only_when_needed():
    assert pager_row("x:p", 0, 1) == []
    row = pager_row("x:p", 1, 3)
    assert [b.callback_data for b in row] == ["x:p:0", "noop", "x:p:2"]
    assert row[1].text == "2/3"


def test_lots_list_paginates():
    cardinal = make_cardinal()
    for i in range(PAGE_SIZE + 3):
        cardinal.autodelivery_config.lots[f"Лот {i:02d}"] = AutoDeliveryLot(stock_file=f"{i}.txt")
    cardinal.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 1)

    _, markup = build_lots_list(cardinal, page=0)
    callbacks = all_callback_data(markup)
    assert "ad:lot:0" in callbacks and f"ad:lot:{PAGE_SIZE}" not in callbacks
    assert "ad:p:1" in callbacks  # стрелка «вперёд»

    _, markup = build_lots_list(cardinal, page=1)
    callbacks = all_callback_data(markup)
    assert f"ad:lot:{PAGE_SIZE}" in callbacks and "ad:lot:0" not in callbacks


def test_module_names_match_settings_fields():
    cardinal = make_cardinal()
    for name in MODULE_NAMES:
        assert hasattr(cardinal.settings.modules, name)


def test_lots_list_and_view():
    cardinal = make_cardinal()
    cardinal.autodelivery_config.lots["Лот А"] = AutoDeliveryLot(stock_file="a.txt", restore=True)
    cardinal.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 7)

    text, markup = build_lots_list(cardinal)
    assert "Лот А" in text and "7" in text
    assert "ad:lot:0" in all_callback_data(markup)

    view = build_lot_view(cardinal, 0)
    assert view is not None
    view_text, view_markup = view
    assert "a.txt" in view_text
    callbacks = all_callback_data(view_markup)
    assert "ad:stock:0" in callbacks and "ad:del:0" in callbacks
    assert "ad:view:0" in callbacks  # просмотр склада
    assert "ad:p:0" in callbacks and "menu" in callbacks  # «Назад» + «Главное меню»

    assert build_lot_view(cardinal, 99) is None  # несуществующий индекс


def test_stock_view_shows_items(tmp_path):
    cardinal = make_cardinal()
    stock_file = tmp_path / "stock.txt"
    stock_file.write_text("key-1\nkey-2\nkey-3\n", encoding="utf-8")
    cardinal.autodelivery_config.lots["Лот А"] = AutoDeliveryLot(stock_file=str(stock_file))

    view = build_stock_view(cardinal, 0)
    assert view is not None
    text, markup = view
    assert "key-1" in text and "key-3" in text
    assert "ad:lot:0" in all_callback_data(markup)  # назад в карточку лота

    assert build_stock_view(cardinal, 99) is None


def test_commands_list():
    cardinal = make_cardinal()
    cardinal.autoresponse_config.commands["!цена"] = "100"
    text, markup = build_commands_list(cardinal)
    assert "!цена" in text
    assert "ar:v:0" in all_callback_data(markup)


def test_notifications_menu_covers_all_toggles():
    cardinal = make_cardinal()
    text, markup = build_notifications_menu(cardinal)
    callbacks = all_callback_data(markup)
    for key in NOTIFICATION_KEYS:
        assert f"nt:t:{key}" in callbacks
    # У каждого тумблера есть строка в локали.
    for key in NOTIFICATION_KEYS:
        assert cardinal.l10n(f"nt_{key}") != f"nt_{key}"


def test_plugins_menu_empty():
    cardinal = make_cardinal()
    text, markup = build_plugins_menu(cardinal)
    assert "pl:install" in all_callback_data(markup)


def test_plugins_menu_has_toggle_and_delete_buttons():
    from playerokapi.plugins import PluginInfo

    cardinal = make_cardinal()
    cardinal.plugin_manager.plugins["uuid-1"] = PluginInfo(
        uuid="uuid-1", name="Мой плагин", version="1.0", description=None,
        credits=None, path="plugins/my.py", module=None,
    )
    text, markup = build_plugins_menu(cardinal)
    callbacks = all_callback_data(markup)
    assert "pl:t:0" in callbacks and "pl:d:0" in callbacks


def test_system_menu_has_all_buttons():
    from cardinal.tg.handlers.system import build_system_menu

    cardinal = make_cardinal()
    text, markup = build_system_menu(cardinal)
    callbacks = all_callback_data(markup)
    for callback in ("sys:logs", "sys:backup", "sys:update", "sys:reload", "sys:restart", "sys:off"):
        assert callback in callbacks


def test_stats_view_totals():
    import datetime

    from cardinal.tg.handlers.stats import build_stats_view

    cardinal = make_cardinal()
    assert build_stats_view(cardinal) is None  # без модуля сводки

    today = datetime.date.today().isoformat()
    old_day = (datetime.date.today() - datetime.timedelta(days=20)).isoformat()

    def get_last_days(days):
        rows = [(today, 2, 300.0)]
        if days >= 30:
            rows.append((old_day, 1, 100.0))
        return rows

    cardinal.modules = [SimpleNamespace(name="digest", get_last_days=get_last_days)]
    view = build_stats_view(cardinal)
    assert view is not None
    text, markup = view
    assert today in text
    assert "2" in text and "300.00" in text  # неделя
    assert "400.00" in text  # месяц: 300 + 100
    assert "menu" in all_callback_data(markup)


def test_locales_have_same_keys():
    from cardinal.locales import en, ru
    assert set(ru.STRINGS) == set(en.STRINGS)
