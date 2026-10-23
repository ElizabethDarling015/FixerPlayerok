"""Шаблоны автоответчика: быстрые ответы продавца `!!команда` в чате (старый модуль удалён)."""
from fixer_helpers import make_fixer


def make_fixer_with(commands: dict[str, str]):
    fixer = make_fixer()
    fixer.autoresponse_config.commands = commands
    return fixer


def test_quick_command_matches_case_insensitive_prefix():
    from fixer.tg.handlers.chats import _match_quick_command
    fixer = make_fixer_with({"!Цена": "100 руб.", "!помощь": "..."})
    assert _match_quick_command(fixer, "!!цена") == ("!Цена", "100 руб.")
    assert _match_quick_command(fixer, "  !!ЦЕНА на аккаунт") == ("!Цена", "100 руб.")
    assert _match_quick_command(fixer, "!цена") is None       # одинарный «!» — обычный текст
    assert _match_quick_command(fixer, "!!неизвестная") is None


def test_quick_command_variables_substitution():
    from fixer.tg.handlers.chats import _format_quick_response
    text = _format_quick_response("Привет, $username! Чат: $chat_id, $date $time", username="buyer99", chat_id="c-7")
    assert text.startswith("Привет, buyer99! Чат: c-7, ")
    assert "$date" not in text and "$time" not in text


def test_old_autoresponse_module_and_toggle_are_gone():
    from fixer.modules import build_modules
    from fixer.settings import ModulesSettings
    assert "autoresponse" not in ModulesSettings.model_fields
    # Старый ключ в main.toml не ломает загрузку.
    assert ModulesSettings.model_validate({"autoresponse": True, "autorestore": False}).online is True
    assert all(m.name != "autoresponse" for m in build_modules(make_fixer()))
