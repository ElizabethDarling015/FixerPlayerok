"""Тесты билдеров TG-панели Fixer (меню, разделы) — чистые функции без сети."""
from types import SimpleNamespace

from fixer.settings import AutoDeliveryLot
from fixer.tg.handlers.autodelivery import build_lot_view, build_lots_list, build_stock_view
from fixer.tg.handlers.autoresponse import build_commands_list
from fixer.tg.handlers.common import PAGE_SIZE, paginate, pager_row
from fixer.tg.handlers.menu import MODULE_NAMES, build_main_menu, build_toggles_menu
from fixer.tg.handlers.notifications import NOTIFICATION_KEYS, build_notifications_menu
from fixer.tg.handlers.plugins_panel import build_plugins_menu

from fixer_helpers import make_fixer


def all_callback_data(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_main_menu_contains_status_and_sections():
    fixer = make_fixer()
    text, markup = build_main_menu(fixer)
    assert "seller" in text and "100" in text  # аккаунт и баланс
    callbacks = all_callback_data(markup)
    assert "Online" in text  # строка подключения
    # Тумблеры модулей и разделы автовыдачи/автоответчика/уведомлений — в «Настройках».
    assert not any(cb.startswith("mod:") for cb in callbacks)
    for section in ("chats", "bl", "pl", "st", "sys", "digest:now"):
        assert section in callbacks


def test_main_menu_button_order():
    """Ряды: «Статистика»+«Плагины», «Сводка сейчас»+«Настройки»."""
    _, markup = build_main_menu(make_fixer())
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert ["st", "pl"] in rows and ["digest:now", "sys"] in rows


def test_settings_menu_close_is_last_and_red():
    from fixer.tg.handlers.system import build_system_menu
    _, markup = build_system_menu(make_fixer())
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert ["sys:update", "px:menu"] in rows and ["sys:clear_confirm", "close"] in rows
    close = next(b for row in markup.inline_keyboard for b in row if b.callback_data == "close")
    assert close.text.startswith("❌")


def test_toggles_menu_contains_all_modules():
    fixer = make_fixer()
    text, markup = build_toggles_menu(fixer)
    callbacks = all_callback_data(markup)
    for name in MODULE_NAMES:
        assert f"mod:{name}" in callbacks
    assert "greeting" not in MODULE_NAMES and "gl:greet" not in callbacks
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
    fixer = make_fixer()
    for i in range(PAGE_SIZE + 3):
        fixer.autodelivery_config.lots[f"Лот {i:02d}"] = AutoDeliveryLot(stock_file=f"{i}.txt")
    fixer.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 1)

    _, markup = build_lots_list(fixer, page=0)
    callbacks = all_callback_data(markup)
    assert "ad:lot:0" in callbacks and f"ad:lot:{PAGE_SIZE}" not in callbacks
    assert "ad:p:1" in callbacks  # стрелка «вперёд»

    _, markup = build_lots_list(fixer, page=1)
    callbacks = all_callback_data(markup)
    assert f"ad:lot:{PAGE_SIZE}" in callbacks and "ad:lot:0" not in callbacks


def test_module_names_match_settings_fields():
    fixer = make_fixer()
    for name in MODULE_NAMES:
        assert hasattr(fixer.settings.modules, name)


def test_lots_list_and_view():
    fixer = make_fixer()
    fixer.autodelivery_config.lots["Лот А"] = AutoDeliveryLot(stock_file="a.txt", restore=True)
    fixer.autodelivery_manager = SimpleNamespace(get_stock_size=lambda name: 7)

    text, markup = build_lots_list(fixer)
    assert "Лот А" in text and "7" in text
    assert "ad:lot:0" in all_callback_data(markup)

    view = build_lot_view(fixer, 0)
    assert view is not None
    view_text, view_markup = view
    assert "a.txt" in view_text
    callbacks = all_callback_data(view_markup)
    assert "ad:stock:0" in callbacks and "ad:del:0" in callbacks
    assert "ad:view:0" in callbacks  # просмотр склада
    assert "ad:p:0" in callbacks and "menu" in callbacks  # «Назад» + «Главное меню»

    assert build_lot_view(fixer, 99) is None  # несуществующий индекс


def test_stock_view_shows_items(tmp_path):
    fixer = make_fixer()
    stock_file = tmp_path / "stock.txt"
    stock_file.write_text("key-1\nkey-2\nkey-3\n", encoding="utf-8")
    fixer.autodelivery_config.lots["Лот А"] = AutoDeliveryLot(stock_file=str(stock_file))

    view = build_stock_view(fixer, 0)
    assert view is not None
    text, markup = view
    assert "key-1" in text and "key-3" in text
    assert "ad:lot:0" in all_callback_data(markup)  # назад в карточку лота

    assert build_stock_view(fixer, 99) is None


def test_commands_list():
    fixer = make_fixer()
    fixer.autoresponse_config.commands["!цена"] = "100"
    text, markup = build_commands_list(fixer)
    assert "!цена" in text
    assert "ar:v:0" in all_callback_data(markup)


def test_notifications_menu_covers_all_toggles():
    fixer = make_fixer()
    text, markup = build_notifications_menu(fixer)
    callbacks = all_callback_data(markup)
    for key in NOTIFICATION_KEYS:
        assert f"nt:t:{key}" in callbacks
    # У каждого тумблера есть строка в локали.
    for key in NOTIFICATION_KEYS:
        assert fixer.l10n(f"nt_{key}") != f"nt_{key}"


def test_plugins_menu_empty():
    fixer = make_fixer()
    text, markup = build_plugins_menu(fixer)
    assert "pl:install" in all_callback_data(markup)


def test_plugins_menu_has_toggle_and_delete_buttons():
    from playerokapi.plugins import PluginInfo

    fixer = make_fixer()
    fixer.plugin_manager.plugins["uuid-1"] = PluginInfo(
        uuid="uuid-1", name="Мой плагин", version="1.0", description=None,
        credits=None, path="plugins/my.py", module=None,
    )
    text, markup = build_plugins_menu(fixer)
    callbacks = all_callback_data(markup)
    # В списке — меню плагина и быстрый тумблер; удаление — внутри меню плагина.
    assert "pl:menu:0" in callbacks and "pl:t:0" in callbacks
    from fixer.tg.handlers.plugins_panel import build_plugin_menu
    _, plugin_markup = build_plugin_menu(fixer, 0)
    assert "pl:d:0" in all_callback_data(plugin_markup)


def test_system_menu_has_all_buttons():
    from fixer.tg.handlers.system import build_system_menu

    fixer = make_fixer()
    fixer.playerok_connected = False
    text, markup = build_system_menu(fixer)
    callbacks = all_callback_data(markup)
    for callback in ("sys:logs", "sys:backup", "sys:update", "sys:connect_playerok",
                     "sys:tests", "sys:clear_confirm", "px:menu", "close"):
        assert callback in callbacks
    # «Перезапустить» заменена кнопкой «Обновить с GitHub», «Выключить» убрана.
    assert "sys:restart" not in callbacks and "sys:off" not in callbacks


def test_locales_have_same_keys():
    from fixer.locales import en, ru
    assert set(ru.STRINGS) == set(en.STRINGS)


def test_locales_have_same_placeholders():
    """Подстановки {…} в ru и en совпадают — иначе в одном из языков уведомление
    придёт сырым шаблоном (как было с сообщениями поддержки)."""
    import string
    from fixer.locales import en, ru

    def placeholders(text):
        return {field for _, field, _, _ in string.Formatter().parse(text) if field}

    for key in ru.STRINGS:
        assert placeholders(ru.STRINGS[key]) == placeholders(en.STRINGS[key]), key
