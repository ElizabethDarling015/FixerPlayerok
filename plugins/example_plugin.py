"""
Пример плагина для playerokapi.

Плагины автоматически подхватываются `PluginManager.load_plugins()` из папки `plugins/` —
достаточно положить туда `.py`-файл с метаданными и функцией `init(manager)`.
"""
import logging

logger = logging.getLogger("plugins.example_plugin")

NAME = "Пример плагина"
VERSION = "1.0.0"
DESCRIPTION = "Демонстрирует регистрацию хуков жизненного цикла, событий и авто-хуков методов Account."
CREDITS = "playerokapi"
UUID = "b7f9b6f0-3e2f-4c9b-8a1e-example00001"


def on_new_message(account, event=None, **kwargs):
    """Хук на событие NEW_MESSAGE (см. `common.enums.Hooks.NEW_MESSAGE`)."""
    if event and event.message and event.message.text:
        logger.info("[example_plugin] Новое сообщение в чате %s: %s", event.chat.id, event.message.text)


def on_new_deal(account, event=None, **kwargs):
    """Хук на событие NEW_DEAL."""
    if event:
        logger.info("[example_plugin] Новая сделка: %s", event.deal.id)


def before_send_message(account, method_name=None, args=None, kwargs=None, **_):
    """
    Авто-хук `PRE_send_message` — вызывается перед каждым вызовом `Account.send_message(...)`.

    Работает только если аккаунт был подключён через `manager.attach_to_account(account)`.
    """
    logger.info("[example_plugin] Отправляется сообщение: args=%s kwargs=%s", args, kwargs)


def init(manager) -> None:
    """Точка входа плагина — вызывается один раз при загрузке `PluginManager.load_plugins()`."""
    manager.bind("NEW_MESSAGE", on_new_message)
    manager.bind("NEW_DEAL", on_new_deal)
    manager.bind("PRE_send_message", before_send_message)
    logger.info("[example_plugin] Плагин %s v%s загружен", NAME, VERSION)
