"""
Пример бота с авто-выдачей уникального товара из файла-склада при оплате лота.

Перед запуском:
1. Вставьте cookies своего аккаунта в переменную `COOKIES` ниже.
2. Настройте `examples/autodelivery.json` — сопоставление `{"название лота": "путь/к/складу.txt"}`.
3. Заполните файлы-склады (например `examples/stock/example_lot.txt`) — одна позиция товара на строку.
"""
import logging
import os

from playerokapi.account import Account
from playerokapi.autodelivery import AutoDeliveryManager
from playerokapi.common.enums import EventTypes
from playerokapi.updater.runner import Runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("autodelivery_bot")

COOKIES = "token=...; __ddg5_=..."  # cookies авторизованного аккаунта Playerok
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "autodelivery.json")


def main() -> None:
    account = Account(cookies=COOKIES).get()
    logger.info("Авторизован как %s", account.username)

    autodelivery_manager = AutoDeliveryManager(config=CONFIG_PATH)
    runner = Runner(account, autodelivery_manager=autodelivery_manager)

    for event in runner.listen(requests_delay=5.0):
        if event.type is EventTypes.ITEM_PAID:
            item_name = event.deal.item.name if event.deal and event.deal.item else "?"
            # Runner сам выполняет безопасную выдачу через reserve()/restore() и фиксирует
            # прогресс в SQLite-журнале — вызывать deliver() вручную не нужно.
            logger.info("Лот %r оплачен — Runner выполнит авто-выдачу", item_name)
        elif event.type is EventTypes.NEW_MESSAGE and event.message.text:
            logger.info("Сообщение в чате %s: %s", event.chat.id, event.message.text)


if __name__ == "__main__":
    main()
