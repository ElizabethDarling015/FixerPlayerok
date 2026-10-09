"""Тесты чёрного списка покупателей: конфиг, игнор в модулях, уведомление, панель."""
from types import SimpleNamespace

from fixer.modules.autoresponse import AutoResponseModule
from fixer.settings import BlacklistConfig, load_blacklist_config, save_blacklist_config
from fixer.tg.handlers.blacklist_panel import build_blacklist_menu
from fixer.tg.notifications import Notifier
from playerokapi.updater.events import ItemPaidEvent, NewMessageEvent

from fixer_helpers import FakeTgBot, make_fixer, make_chat, make_chat_message


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
    fixer = make_fixer()
    fixer.autoresponse_config.commands["!тест"] = "ответ"
    fixer.blacklist_config.usernames.append("cheater")
    module = AutoResponseModule(fixer)

    event = NewMessageEvent(None, make_chat(), make_chat_message("!тест", username="Cheater"))
    await module.on_event(event)
    assert fixer.account.sent_messages == []

    # Обычному покупателю модуль отвечает как раньше.
    event = NewMessageEvent(None, make_chat(), make_chat_message("!тест", username="honest"))
    await module.on_event(event)
    assert len(fixer.account.sent_messages) == 1


async def test_greeting_ignores_blacklisted(tmp_path):
    from fixer.modules.greeting import GreetingModule

    fixer = make_fixer()
    fixer.settings.modules.greeting = True
    fixer.blacklist_config.usernames.append("cheater")
    module = GreetingModule(fixer, db_path=str(tmp_path / "greeting.sqlite3"))

    await module.on_event(NewMessageEvent(None, make_chat("c1"), make_chat_message("привет", username="cheater")))
    assert fixer.account.sent_messages == []
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
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert any("чёрного списка" in text.lower() for text in texts)


async def test_blacklist_warning_toggle_off():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    fixer.settings.notifications.blacklist = False
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("cheater")))
    texts = [text for _, text in bot.sent]
    assert not any("чёрного списка" in text.lower() for text in texts)


async def test_no_warning_for_regular_buyer():
    fixer = make_fixer()
    fixer.blacklist_config.usernames.append("cheater")
    bot = FakeTgBot()
    notifier = Notifier(fixer, bot, SimpleNamespace(all_ids={1}))

    await notifier.on_event(ItemPaidEvent(None, make_chat(), None, make_deal("honest")))
    texts = [text for _, text in bot.sent]
    assert not any("чёрного списка" in text.lower() for text in texts)


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
