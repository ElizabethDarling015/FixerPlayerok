"""Сборка Telegram-бота Cardinal: Bot + Dispatcher + авторизация + роутеры + уведомления."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from .auth import AuthMiddleware, TgAdmins
from .notifications import Notifier


def setup_telegram(cardinal):
    """
    Создаёт и настраивает Telegram-часть Cardinal.

    :return: Кортеж `(bot, dispatcher, notifier)`.
    """
    bot = Bot(token=cardinal.settings.telegram.token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()

    admins = TgAdmins(cardinal.settings.telegram.admin_ids)
    if not admins.all_ids:
        logger.warning("Администраторы Telegram не настроены. Отправьте боту код привязки: {}",
                       admins.secret_code)
    else:
        logger.info("Администраторы Telegram: {}", ", ".join(map(str, sorted(admins.all_ids))))

    auth = AuthMiddleware(cardinal, admins)
    dispatcher.message.outer_middleware(auth)
    dispatcher.callback_query.outer_middleware(auth)

    notifier = Notifier(cardinal, bot, admins)

    # Через workflow_data aiogram внедряет эти объекты в хендлеры по имени параметра.
    dispatcher["cardinal"] = cardinal
    dispatcher["admins"] = admins
    dispatcher["notifier"] = notifier

    from .handlers import setup_routers
    setup_routers(dispatcher)

    return bot, dispatcher, notifier
