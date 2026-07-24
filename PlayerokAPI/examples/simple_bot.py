"""
Минимальный пример бота на playerokapi: отвечает на новые сообщения в чатах и логирует новые сделки.

Перед запуском вставьте cookies своего аккаунта Playerok в переменную `COOKIES` ниже.
"""
import logging

from playerokapi.account import Account
from playerokapi.common.enums import EventTypes
from playerokapi.updater.runner import Runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simple_bot")

COOKIES = "token=...; __ddg5_=..."  # cookies авторизованного аккаунта Playerok


def main() -> None:
    account = Account(cookies=COOKIES).get()
    logger.info("Авторизован как %s (баланс: %s)", account.username, account.profile.balance.value)

    runner = Runner(account)
    for event in runner.listen(requests_delay=5.0):
        if event.type is EventTypes.CHAT_INITIALIZED:
            logger.info("Обнаружен чат: %s", event.chat.id)

        elif event.type is EventTypes.NEW_MESSAGE:
            message = event.message
            if message.user and message.user.id == account.id:
                continue  # не отвечаем на собственные сообщения
            if message.text:
                logger.info("Новое сообщение от %s: %s", message.user.username if message.user else "?", message.text)
                account.send_message(event.chat.id, "Спасибо за сообщение! Скоро отвечу лично.")

        elif event.type is EventTypes.NEW_DEAL:
            logger.info("Новая сделка: %s (лот: %s)", event.deal.id, event.deal.item.name if event.deal.item else "?")

        elif event.type is EventTypes.DEAL_STATUS_CHANGED:
            logger.info("Статус сделки %s изменился: %s -> %s", event.deal.id, event.previous_status, event.new_status)


if __name__ == "__main__":
    main()
