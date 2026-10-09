"""Общие фейки для тестов FixerPlayerok (используются в tests/test_fixer_*.py)."""
from __future__ import annotations

from types import SimpleNamespace

from playerokapi.plugins import PluginManager
from playerokapi.types import AccountBalance

from fixer.localization import L10n
from fixer.settings import AutoDeliveryConfig, AutoResponseConfig, BlacklistConfig, MainSettings


class FakeTgBot:
    """Фейковый aiogram-бот: записывает отправленные сообщения."""

    def __init__(self):
        self.sent: list[tuple[int, str]] = []
        self._message_id = 0

    async def send_message(self, chat_id, text, **kwargs):
        self._message_id += 1
        self.sent.append((chat_id, text))
        return SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=self._message_id)


class FakeFixerAccount:
    """Фейковый playerokapi.Account: записывает отправленные сообщения Playerok."""

    def __init__(self):
        self.id = "me-id"
        self.username = "seller"
        # Настоящий AccountBalance: у него есть format_balance(), который зовут меню, сводка и уведомления.
        self.profile = SimpleNamespace(
            balance=AccountBalance(id=None, value=100, frozen=0, available=100, withdrawable=100, pending_income=0),
            is_online=True, support_chat_id="support-chat", system_chat_id="system-chat",
        )
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


def make_fixer(settings: MainSettings | None = None) -> SimpleNamespace:
    """Минимальный объект «fixer» для модулей и уведомлений (без реального ядра)."""
    settings = settings or make_settings()
    fixer = SimpleNamespace(
        settings=settings,
        l10n=L10n(settings.language),
        account=FakeFixerAccount(),
        autoresponse_config=AutoResponseConfig(),
        autodelivery_config=AutoDeliveryConfig(),
        autodelivery_manager=None,
        blacklist_config=BlacklistConfig(),
        plugin_manager=PluginManager(plugins_dir="nonexistent_plugins_dir"),
        notifier=None,
        modules=[],
        uptime="00:00:01",
        playerok_connected=True,
    )
    fixer.is_blacklisted = lambda username, user_id=None: fixer.blacklist_config.contains(username, user_id)
    return fixer


def make_chat(chat_id="chat-1"):
    return SimpleNamespace(id=chat_id)


def make_chat_message(text, user_id="buyer-id", username="buyer"):
    return SimpleNamespace(
        text=text,
        user=SimpleNamespace(id=user_id, username=username),
    )
