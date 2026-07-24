"""Общие фейки для тестов PlayerokCardinal (используются в tests/test_cardinal_*.py)."""
from __future__ import annotations

from types import SimpleNamespace

from playerokapi.plugins import PluginManager

from cardinal.localization import L10n
from cardinal.settings import AutoDeliveryConfig, AutoResponseConfig, BlacklistConfig, MainSettings


class FakeTgBot:
    """Фейковый aiogram-бот: записывает отправленные сообщения."""

    def __init__(self):
        self.sent: list[tuple[int, str]] = []
        self._message_id = 0

    async def send_message(self, chat_id, text, **kwargs):
        self._message_id += 1
        self.sent.append((chat_id, text))
        return SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=self._message_id)


class FakeCardinalAccount:
    """Фейковый playerokapi.Account: записывает отправленные сообщения Playerok."""

    def __init__(self):
        self.id = "me-id"
        self.username = "seller"
        self.profile = SimpleNamespace(balance=SimpleNamespace(value=100, available=100), is_online=True)
        self.sent_messages: list[tuple[str, str]] = []

    def send_message(self, chat_id, text=None, **kwargs):
        self.sent_messages.append((chat_id, text))
        return SimpleNamespace(id="msg-id", text=text)

    def get(self):
        return self


def make_settings(**overrides) -> MainSettings:
    data = {"playerok": {"cookies": "token=abc; __ddg5_=x"}}
    data.update(overrides)
    return MainSettings.model_validate(data)


def make_cardinal(settings: MainSettings | None = None) -> SimpleNamespace:
    """Минимальный объект «cardinal» для модулей и уведомлений (без реального ядра)."""
    settings = settings or make_settings()
    cardinal = SimpleNamespace(
        settings=settings,
        l10n=L10n(settings.language),
        account=FakeCardinalAccount(),
        autoresponse_config=AutoResponseConfig(),
        autodelivery_config=AutoDeliveryConfig(),
        autodelivery_manager=None,
        blacklist_config=BlacklistConfig(),
        plugin_manager=PluginManager(plugins_dir="nonexistent_plugins_dir"),
        notifier=None,
        modules=[],
        uptime="00:00:01",
    )
    cardinal.is_blacklisted = lambda username: cardinal.blacklist_config.contains(username)
    return cardinal


def make_chat(chat_id="chat-1"):
    return SimpleNamespace(id=chat_id)


def make_chat_message(text, user_id="buyer-id", username="buyer"):
    return SimpleNamespace(
        text=text,
        user=SimpleNamespace(id=user_id, username=username),
    )
