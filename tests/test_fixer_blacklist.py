"""Тесты чёрного списка покупателей: конфиг, уведомление, панель."""
from types import SimpleNamespace

from fixer.settings import BlacklistConfig, load_blacklist_config, save_blacklist_config
from fixer.tg.handlers.blacklist_panel import build_blacklist_menu
from fixer.tg.notifications import Notifier
from playerokapi.updater.events import ItemPaidEvent

from fixer_helpers import FakeTgBot, make_fixer, make_chat


# ----------------------------------------------------------------------
# Конфиг
# ----------------------------------------------------------------------

def test_config_cleans_and_dedupes():
    config = BlacklistConfig(usernames=["  Cheater ", "cheater", "", "other"])
    assert config.usernames == ["Cheater", "other"]


def test_contains_case_insensitive():
    config = BlacklistConfig(usernames=["Cheater"])
    assert config.contains("cheater")
    assert config.contains(" CHEATER ")
    assert not config.contains("honest")
    assert not config.contains(None)


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "blacklist.toml")
    save_blacklist_config(BlacklistConfig(usernames=["cheater", "спамер"]), path)
    loaded = load_blacklist_config(path)
    assert loaded.usernames == ["cheater", "спамер"]


def test_load_missing_file_is_empty(tmp_path):
    assert load_blacklist_config(str(tmp_path / "nope.toml")).usernames == []


# ----------------------------------------------------------------------
# Игнор в модулях
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Уведомление о сделке с ЧС-покупателем
# ----------------------------------------------------------------------

def make_deal(buyer="cheater"):
    return SimpleNamespace(
        id="deal-1",
        item=SimpleNamespace(name="Лот"),
        user=SimpleNamespace(username=buyer),
        raw_status=SimpleNamespace(name="PAID"),
    )


async def test_blacklist_deal_warning():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert any("🚫" in text for text in texts)


async def test_blacklist_warning_toggle_off():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    fixer.settings.notifications.blacklist = False
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert not any("🚫" in text for text in texts)


async def test_no_warning_for_regular_buyer():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("honest")))
    texts = [text for _, text in bot.sent]
    assert not any("🚫" in text for text in texts)


# ----------------------------------------------------------------------
# Панель
# ----------------------------------------------------------------------

def test_build_blacklist_menu():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.extend(["zeta", "Alpha"])
    text, markup = build_blacklist_menu(fixer)
    assert "zeta" in text and "Alpha" in text
    buttons = [button for row in markup.inline_keyboard for button in row]
    # Кнопки удаления отсортированы без учёта регистра + «добавить» + «назад».
    assert buttons[0].text.endswith("Alpha")
    assert buttons[1].text.endswith("zeta")
    assert any(button.callback_data == "bl:add" for button in buttons)


def test_build_blacklist_menu_empty():
    fixer = make_fixer()
    text, markup = build_blacklist_menu(fixer)
    assert fixer.l10n("bl_empty") in text
