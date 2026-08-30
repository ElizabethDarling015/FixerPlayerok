"""Роутеры TG-панели Cardinal (по роутеру на раздел)."""
from __future__ import annotations

from aiogram import Dispatcher

from . import autodelivery, autoresponse, blacklist_panel, chats, menu, notifications, plugins_panel, replies, stats, system

def setup_routers(dispatcher: Dispatcher) -> None:
    """Подключает все роутеры панели. `replies` — последним (catch-all для reply-сообщений)."""
    # Сторож режима «живой диалог» — должен видеть ВСЕ callback-кнопки панели.
    chats.setup_chat_mode_guard(dispatcher)

    dispatcher.include_router(menu.router)
    dispatcher.include_router(autodelivery.router)
    dispatcher.include_router(autoresponse.router)
    dispatcher.include_router(blacklist_panel.router)
    dispatcher.include_router(notifications.router)
    dispatcher.include_router(stats.router)
    dispatcher.include_router(system.router)
    dispatcher.include_router(plugins_panel.router)
    chats.setup_chat_mode_guard(dispatcher)
    dispatcher.include_router(replies.router)