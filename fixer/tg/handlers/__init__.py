"""Роутеры TG-панели Fixer (по роутеру на раздел)."""
from __future__ import annotations

from aiogram import Dispatcher

from . import (autodelivery, autoresponse, blacklist_panel, chats, deal_actions, last_deals, menu, notifications,
               plugins_panel, proxy, replies, stats, system, withdrawal)

def setup_routers(dispatcher: Dispatcher) -> None:
    """Подключает все роутеры панели. `replies` — последним (catch-all для reply-сообщений)."""
    # Сторож режима «живой диалог» — должен видеть ВСЕ callback-кнопки панели.
    chats.setup_chat_mode_guard(dispatcher)

    # Чаты — ДО menu: callback "chats" обязан обрабатывать раздел, а не заглушка.
    dispatcher.include_router(chats.router)
    dispatcher.include_router(menu.router)
    dispatcher.include_router(autodelivery.router)
    dispatcher.include_router(autoresponse.router)
    dispatcher.include_router(blacklist_panel.router)
    dispatcher.include_router(notifications.router)
    dispatcher.include_router(deal_actions.router)
    dispatcher.include_router(last_deals.router)
    dispatcher.include_router(withdrawal.router)
    dispatcher.include_router(stats.router)
    dispatcher.include_router(system.router)
    dispatcher.include_router(proxy.router)
    dispatcher.include_router(plugins_panel.router)
    dispatcher.include_router(replies.router)