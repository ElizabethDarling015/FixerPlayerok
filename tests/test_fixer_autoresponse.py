"""Тесты модуля автоответчика Fixer (`fixer.modules.autoresponse`)."""
from fixer.modules.autoresponse import AutoResponseModule
from playerokapi.updater.events import NewMessageEvent

from fixer_helpers import make_fixer, make_chat, make_chat_message


def make_module(commands: dict[str, str]) -> tuple[AutoResponseModule, object]:
    fixer = make_fixer()
    fixer.autoresponse_config.commands = commands
    return AutoResponseModule(fixer), fixer


async def test_buyer_commands_get_no_automatic_reply():
    """Автоответчик больше не отвечает покупателям сам: это библиотека шаблонов продавца."""
    module, fixer = make_module({"!цена": "Цена — 100 руб."})
    for text in ("!цена", "!Цена на аккаунт?", "!команды", "привет"):
        await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message(text)))
    assert fixer.account.sent_messages == []


def test_quick_command_matches_case_insensitive_prefix():
    from fixer.tg.handlers.chats import _match_quick_command
    _, fixer = make_module({"!Цена": "100 руб.", "!помощь": "..."})
    assert _match_quick_command(fixer, "!!цена") == ("!Цена", "100 руб.")
    assert _match_quick_command(fixer, "  !!ЦЕНА на аккаунт") == ("!Цена", "100 руб.")
    assert _match_quick_command(fixer, "!цена") is None       # одинарный «!» — обычный текст
    assert _match_quick_command(fixer, "!!неизвестная") is None


def test_quick_command_variables_substitution():
    from fixer.tg.handlers.chats import _format_quick_response
    text = _format_quick_response("Привет, $username! Чат: $chat_id, $date $time", username="buyer99", chat_id="c-7")
    assert text.startswith("Привет, buyer99! Чат: c-7, ")
    assert "$date" not in text and "$time" not in text


def test_builtin_commands_list_reply():
    module, fixer = make_module({"!цена": "100", "!помощь": "..."})
    text = module.build_reply("!команды", username="u", chat_id="c")
    assert "!цена" in text and "!помощь" in text


def test_format_response_date_time():
    module, _ = make_module({})
    text = module.format_response("Сегодня $date, время $time", username="u", chat_id="c")
    assert "$date" not in text and "$time" not in text
