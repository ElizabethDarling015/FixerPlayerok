"""
Контрактные тесты плагинной системы (`playerokapi.plugins.PluginManager`).

Фиксируют текущее публичное поведение bind/unbind_all/dispatch и обёртки методов
`Account` авто-хуками `PRE_<метод>`/`POST_<метод>`, чтобы рефакторинг не сломал
контракт незаметно. Сами `plugins.py` эти тесты не меняют — только описывают.
"""
import pytest

from playerokapi.common.enums import Hooks
from playerokapi.plugins import PluginManager


class FakeAccount:
    """Минимальный фейк `Account`: пара публичных методов, без сети."""

    def __init__(self):
        self.call_log = []

    def send_message(self, chat_id, text, *, silent=False):
        self.call_log.append(("send_message", chat_id, text, silent))
        return f"sent:{text}"

    def failing_method(self):
        raise ValueError("метод упал")


# ----------------------------------------------------------------------
# bind / dispatch
# ----------------------------------------------------------------------

def test_bind_accepts_hooks_enum_and_raw_string():
    """bind принимает и значение enum Hooks, и голую строку — оба зовутся одним dispatch."""
    manager = PluginManager()
    calls = []
    manager.bind(Hooks.NEW_MESSAGE, lambda **kwargs: calls.append("enum"))
    manager.bind("NEW_MESSAGE", lambda **kwargs: calls.append("string"))

    # dispatch тоже принимает и enum, и строку — оба резолвятся в одно имя хука.
    manager.dispatch(Hooks.NEW_MESSAGE, account="a")
    manager.dispatch("NEW_MESSAGE", account="a")

    assert calls == ["enum", "string", "enum", "string"]


def test_dispatch_passes_kwargs_to_handler():
    """dispatch передаёт хендлеру все свои kwargs как есть (плюс account)."""
    manager = PluginManager()
    manager.account = "acc"
    received = []
    manager.bind("MY_HOOK", lambda **kwargs: received.append(kwargs))

    manager.dispatch("MY_HOOK", event="событие", number=42)

    assert received == [{"account": "acc", "event": "событие", "number": 42}]


def test_dispatch_unknown_hook_is_noop():
    """dispatch по хуку без хендлеров — тихий no-op, без ошибок."""
    manager = PluginManager()
    manager.dispatch("NO_SUCH_HOOK", account="a")  # не должно упасть


# ----------------------------------------------------------------------
# unbind_all
# ----------------------------------------------------------------------

def test_unbind_all_removes_only_own_handlers():
    """unbind_all снимает хендлеры только указанного плагина — чужие остаются."""
    manager = PluginManager()
    calls = []
    manager.bind("MY_HOOK", lambda **kwargs: calls.append("мой"), plugin_uuid="uuid-мой")
    manager.bind("MY_HOOK", lambda **kwargs: calls.append("чужой"), plugin_uuid="uuid-чужой")
    manager.bind("OTHER_HOOK", lambda **kwargs: calls.append("мой-другой-хук"), plugin_uuid="uuid-мой")

    manager.unbind_all("uuid-мой")

    manager.dispatch("MY_HOOK", account="a")
    manager.dispatch("OTHER_HOOK", account="a")
    assert calls == ["чужой"]  # хендлеры "uuid-мой" сняты со всех хуков


# ----------------------------------------------------------------------
# Обёртка методов Account: PRE_/POST_-хуки
# ----------------------------------------------------------------------

def test_wrapped_method_pre_and_post_hooks_order_and_payload():
    """PRE_-хук получает method_name/args/kwargs до вызова, POST_ — плюс result после; порядок PRE → метод → POST."""
    manager = PluginManager()
    account = FakeAccount()
    order = []
    pre_payloads, post_payloads = [], []

    def pre_handler(**kwargs):
        order.append("pre")
        # На момент PRE_-хука сам метод ещё не вызывался.
        assert account.call_log == []
        pre_payloads.append(kwargs)

    def post_handler(**kwargs):
        order.append("post")
        post_payloads.append(kwargs)

    manager.bind("PRE_send_message", pre_handler)
    manager.bind("POST_send_message", post_handler)
    manager.attach_to_account(account)

    result = manager.account.send_message("chat-1", "привет", silent=True)
    order.append("returned")

    assert result == "sent:привет"  # обёртка возвращает результат метода как есть
    assert order == ["pre", "post", "returned"]
    assert account.call_log == [("send_message", "chat-1", "привет", True)]

    assert pre_payloads == [{
        "account": account,
        "method_name": "send_message",
        "args": ("chat-1", "привет"),
        "kwargs": {"silent": True},
    }]
    assert post_payloads == [{
        "account": account,
        "method_name": "send_message",
        "args": ("chat-1", "привет"),
        "kwargs": {"silent": True},
        "result": "sent:привет",
    }]


def test_pre_hook_exception_is_swallowed_method_still_called():
    """Исключение в хендлере хука dispatch глотает (логирует) — метод и POST_-хук всё равно выполняются."""
    manager = PluginManager()
    account = FakeAccount()
    calls = []

    def failing_pre(**kwargs):
        calls.append("pre")
        raise RuntimeError("хендлер упал")

    manager.bind("PRE_send_message", failing_pre)
    manager.bind("POST_send_message", lambda **kwargs: calls.append("post"))
    manager.attach_to_account(account)

    result = manager.account.send_message("chat-1", "текст")

    assert result == "sent:текст"
    assert calls == ["pre", "post"]
    assert len(account.call_log) == 1


def test_exception_in_wrapped_method_propagates_and_skips_post_hook():
    """Исключение в самом обёрнутом методе пробрасывается наружу, POST_-хук НЕ вызывается."""
    manager = PluginManager()
    account = FakeAccount()
    calls = []
    manager.bind("PRE_failing_method", lambda **kwargs: calls.append("pre"))
    manager.bind("POST_failing_method", lambda **kwargs: calls.append("post"))
    manager.attach_to_account(account)

    with pytest.raises(ValueError, match="метод упал"):
        manager.account.failing_method()

    assert calls == ["pre"]  # PRE_ успел, POST_ после падения метода не зовётся
