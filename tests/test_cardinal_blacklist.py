"""Тесты чёрного списка покупателей: конфиг, игнор в модулях, уведомление, панель."""
from types import SimpleNamespace

from cardinal.modules.autoresponse import AutoResponseModule
from cardinal.settings import BlacklistConfig, load_blacklist_config, save_blacklist_config
from cardinal.tg.handlers.blacklist_panel import build_blacklist_menu
from cardinal.tg.notifications import Notifier
from playerokapi.updater.events import ItemPaidEvent, NewMessageEvent

from cardinal_helpers import FakeTgBot, make_cardinal, make_chat, make_chat_message


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

async def test_autoresponse_ignores_blacklisted():
    cardinal = make_cardinal()
    cardinal.autoresponse_config.commands["!тест"] = "ответ"
    cardinal.blacklist_config.usernames.append("cheater")
    module = AutoResponseModule(cardinal)

    event = NewMessageEvent(None, make_chat(), make_chat_message("!тест", username="Cheater"))
    await module.on_event(event)
    assert cardinal.account.sent_messages == []

    # Обычному покупателю модуль отвечает как раньше.
    event = NewMessageEvent(None, make_chat(), make_chat_message("!тест", username="honest"))
    await module.on_event(event)
    assert len(cardinal.account.sent_messages) == 1


async def test_greeting_ignores_blacklisted(tmp_path):
    from cardinal.modules.greeting import GreetingModule

    cardinal = make_cardinal()
    cardinal.settings.modules.greeting = True
    cardinal.blacklist_config.usernames.append("cheater")
    module = GreetingModule(cardinal, db_path=str(tmp_path / "greeting.sqlite3"))

    await module.on_event(NewMessageEvent(None, make_chat("c1"), make_chat_message("привет", username="cheater")))
    assert cardinal.account.sent_messages == []
    # Чат не помечен — если покупателя уберут из ЧС, приветствие ещё сработает.
    assert not module.is_greeted("c1")


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
    cardinal = make_cardinal()
    cardinal.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(cardinal, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert any("чёрного списка" in text.lower() for text in texts)


async def test_blacklist_warning_toggle_off():
    cardinal = make_cardinal()
    cardinal.blacklist_config.usernames.append("cheater")
    cardinal.settings.notifications.blacklist = False
    bot = FakeTgBot()
    notifier = Notifier(cardinal, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert not any("чёрного списка" in text.lower() for text in texts)


async def test_no_warning_for_regular_buyer():
    cardinal = make_cardinal()
    cardinal.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(cardinal, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("honest")))
    texts = [text for _, text in bot.sent]
    assert not any("чёрного списка" in text.lower() for text in texts)


# ----------------------------------------------------------------------
# Панель
# ----------------------------------------------------------------------

def test_build_blacklist_menu():
    cardinal = make_cardinal()
    cardinal.blacklist_config.usernames.extend(["zeta", "Alpha"])
    text, markup = build_blacklist_menu(cardinal)
    assert "zeta" in text and "Alpha" in text
    buttons = [button for row in markup.inline_keyboard for button in row]
    # Кнопки удаления отсортированы без учёта регистра + «добавить» + «назад».
    assert buttons[0].text.endswith("Alpha")
    assert buttons[1].text.endswith("zeta")
    assert any(button.callback_data == "bl:add" for button in buttons)


def test_build_blacklist_menu_empty():
    cardinal = make_cardinal()
    text, markup = build_blacklist_menu(cardinal)
    assert cardinal.l10n("bl_empty") in text
