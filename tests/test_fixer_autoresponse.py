"""Тесты модуля автоответчика Fixer (`fixer.modules.autoresponse`)."""
from fixer.modules.autoresponse import AutoResponseModule
from playerokapi.updater.events import NewMessageEvent

from fixer_helpers import make_fixer, make_chat, make_chat_message


def make_module(commands: dict[str, str]) -> tuple[AutoResponseModule, object]:
    fixer = make_fixer()
    fixer.autoresponse_config.commands = commands
    return AutoResponseModule(fixer), fixer


async def test_replies_to_known_command():
    module, fixer = make_module({"!цена": "Цена — 100 руб."})
    event = NewMessageEvent(None, make_chat("chat-1"), make_chat_message("!цена"))
    await module.on_event(event)
    assert fixer.account.sent_messages == [("chat-1", "Цена — 100 руб.")]


async def test_command_matching_is_case_insensitive_and_prefix():
    module, fixer = make_module({"!Цена": "100"})
    event = NewMessageEvent(None, make_chat(), make_chat_message("!цена на аккаунт?"))
    await module.on_event(event)
    assert len(fixer.account.sent_messages) == 1


async def test_ignores_unknown_text_and_own_messages():
    module, fixer = make_module({"!цена": "100"})
    await module.on_event(NewMessageEvent(None, make_chat(), make_chat_message("привет")))
    # Своё сообщение (user.id == account.id) не должно вызывать ответ.
    own = make_chat_message("!цена", user_id=fixer.account.id)
    await module.on_event(NewMessageEvent(None, make_chat(), own))
    assert fixer.account.sent_messages == []


async def test_disabled_module_does_nothing():
    module, fixer = make_module({"!цена": "100"})
    fixer.settings.modules.autoresponse = False
    await module.on_event(NewMessageEvent(None, make_chat(), make_chat_message("!цена")))
    assert fixer.account.sent_messages == []


async def test_variables_substitution():
    module, fixer = make_module({"!привет": "Привет, $username! Чат: $chat_id"})
    event = NewMessageEvent(None, make_chat("c-7"), make_chat_message("!привет", username="buyer99"))
    await module.on_event(event)
    chat_id, text = fixer.account.sent_messages[0]
    assert text == "Привет, buyer99! Чат: c-7"


async def test_builtin_commands_list():
    module, fixer = make_module({"!цена": "100", "!помощь": "..."})
    await module.on_event(NewMessageEvent(None, make_chat(), make_chat_message("!команды")))
    _, text = fixer.account.sent_messages[0]
    assert "!цена" in text and "!помощь" in text


def test_format_response_date_time():
    module, _ = make_module({})
    text = module.format_response("Сегодня $date, время $time", username="u", chat_id="c")
    assert "$date" not in text and "$time" not in text
