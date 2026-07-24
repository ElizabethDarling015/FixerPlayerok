"""
Пример бота с авто-поднятием лотов по таймеру.

Перед запуском вставьте cookies своего аккаунта в переменную `COOKIES` ниже.
Настройте `RAISE_INTERVAL` (таймер) и при желании `MIN_BALANCE_RESERVE` — сумму,
которую не нужно тратить на поднятие (например, отложенную на вывод).
"""
import logging

from playerokapi.account import Account
from playerokapi.autoraise import AutoRaiseManager
from playerokapi.common.enums import EventTypes
from playerokapi.updater.runner import Runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("autoraise_bot")

COOKIES = "token=...; __ddg5_=..."  # cookies авторизованного аккаунта Playerok

# Как часто пытаться поднимать лоты (в секундах). 4 часа — стартовое значение, подберите под свою категорию.
RAISE_INTERVAL = 4 * 60 * 60

# Сколько денег на балансе никогда не трогать (например, отложено на вывод).
MIN_BALANCE_RESERVE = 0


def main() -> None:
    account = Account(cookies=COOKIES).get()
    logger.info("Авторизован как %s (баланс: %s)", account.username, account.profile.balance.value)

    autoraise_manager = AutoRaiseManager(raise_interval=RAISE_INTERVAL, min_balance_reserve=MIN_BALANCE_RESERVE)
    runner = Runner(account, autoraise_manager=autoraise_manager)

    for event in runner.listen():
        if event.type is EventTypes.ITEM_RAISED:
            result = event.result
            logger.info("Лот %r поднят, потрачено %s", result.item_name, result.spent)

        elif event.type is EventTypes.INSUFFICIENT_BALANCE:
            result = event.result
            price = result.priority_status.price if result.priority_status else "?"
            logger.warning(
                "Не хватило баланса, чтобы поднять лот %r: нужно %s, доступно %s. "
                "Пополните баланс — при следующем цикле (через %.0f сек) попробуем снова.",
                result.item_name, price, result.available, RAISE_INTERVAL,
            )
            # Здесь удобно вызвать свой плагин с уведомлением в Telegram/Discord, см. plugins/example_plugin.py


if __name__ == "__main__":
    main()
