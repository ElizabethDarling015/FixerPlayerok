"""Регрессия: PluginManager.dispatch не должен падать при account в kwargs (так его зовёт Runner)."""
from playerokapi.plugins import PluginManager


def test_dispatch_with_account_kwarg_calls_handler_once():
    manager = PluginManager()
    manager.account = "manager-account"
    calls = []
    manager.bind("MY_HOOK", lambda **kwargs: calls.append(kwargs))

    # Runner всегда передаёт account= сам — раньше это давало TypeError, который молча глотался.
    manager.dispatch("MY_HOOK", account="runner-account", runner="runner")

    assert len(calls) == 1
    assert calls[0]["account"] == "runner-account"
    assert calls[0]["runner"] == "runner"


def test_dispatch_without_account_uses_manager_account():
    manager = PluginManager()
    manager.account = "manager-account"
    calls = []
    manager.bind("MY_HOOK", lambda **kwargs: calls.append(kwargs))

    manager.dispatch("MY_HOOK")

    assert len(calls) == 1
    assert calls[0]["account"] == "manager-account"


def test_dispatch_handler_error_does_not_break_other_handlers():
    manager = PluginManager()
    calls = []

    def failing_handler(**kwargs):
        raise RuntimeError("boom")

    manager.bind("MY_HOOK", failing_handler)
    manager.bind("MY_HOOK", lambda **kwargs: calls.append(kwargs))

    manager.dispatch("MY_HOOK", account="a")

    assert len(calls) == 1


def test_unload_plugin_removes_handlers_and_registry():
    from playerokapi.plugins import PluginInfo

    manager = PluginManager()
    manager.plugins["uuid-1"] = PluginInfo(uuid="uuid-1", name="Мой плагин", version="1.0",
                                           description=None, credits=None, path="plugins/my.py",
                                           module=None)
    calls = []
    manager.bind("MY_HOOK", lambda **kwargs: calls.append(kwargs), plugin_uuid="uuid-1")

    removed = manager.unload_plugin("uuid-1")

    assert removed is not None and removed.name == "Мой плагин"
    assert "uuid-1" not in manager.plugins
    manager.dispatch("MY_HOOK", account="a")
    assert calls == []  # хендлеры выгруженного плагина больше не вызываются

    assert manager.unload_plugin("uuid-1") is None  # повторная выгрузка безопасна
