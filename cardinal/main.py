"""Точка входа PlayerokCardinal: настройка логов, первичная настройка, запуск ядра."""
from __future__ import annotations

import asyncio
import os
import re
import sys

from loguru import logger

from .logging_setup import setup_logging
from .settings import MAIN_CONFIG, ConfigError, load_main_settings

#: --proxy1, --proxy2, ... — разовый выбор N-го сохранённого прокси (по порядку
#: добавления через Telegram-меню Настройки -> Прокси) для ЭТОГО запуска.
_PROXY_FLAG_RE = re.compile(r"^--proxy(\d+)$")


def _parse_cli_proxy_flag(args: list[str]) -> str | None:
    """
    Возвращает URL прокси, если среди аргументов есть --proxyN, иначе None.
    Бросает SystemExit с понятным сообщением, если номер не сохранён в БД —
    по договорённости флаг обязан падать явно, а не тихо стартовать без прокси
    или напрямую, если человек ошибся в номере.
    """
    for arg in args:
        m = _PROXY_FLAG_RE.match(arg)
        if not m:
            continue
        n = int(m.group(1))
        from . import proxy_store
        from .proxy_tools import build_proxy_url
        proxy = proxy_store.get_by_ordinal(n)
        if proxy is None:
            total = len(proxy_store.list_proxies())
            logger.error(
                "Флаг --proxy{}: прокси с таким номером не сохранён (всего сохранено: {}). "
                "Добавьте прокси через Telegram-меню Настройки -> Прокси или укажите "
                "существующий номер.", n, total,
            )
            raise SystemExit(1)
        logger.info("Флаг --proxy{}: разово запускаюсь через {}:{} (только на этот процесс)",
                    n, proxy["host"], proxy["port"])
        return build_proxy_url(proxy)
    return None


def main(argv: list[str] | None = None) -> int:
    """Запускает Cardinal. Возвращает код выхода процесса."""
    setup_logging()

    # Парсим аргументы командной строки
    args = argv if argv is not None else sys.argv[1:]
    offline_mode_flag = "--offline" in args or "-o" in args
    try:
        cli_proxy = _parse_cli_proxy_flag(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    if not os.path.isfile(MAIN_CONFIG):
        # Первый запуск — интерактивный мастер (создаёт конфиги и папки).
        from .first_setup import run_first_setup
        try:
            settings = run_first_setup()
        except (KeyboardInterrupt, EOFError):
            logger.info("Первичная настройка прервана — выходим.")
            return 1
    else:
        try:
            settings = load_main_settings(MAIN_CONFIG)
        except ConfigError as exc:
            logger.error("{}", exc)
            return 1

    # Применяем флаг --offline из командной строки
    if offline_mode_flag:
        settings.playerok.offline_mode = True
        logger.info("Флаг --offline: принудительный оффлайн-режим")

    from .core import Cardinal

    cardinal = Cardinal(settings, cli_proxy=cli_proxy)
    try:
        asyncio.run(cardinal.run())
    except KeyboardInterrupt:
        logger.info("Остановлено по Ctrl+C.")
    except Exception:
        logger.exception("Cardinal завершился с ошибкой")
        return 1

    if cardinal.restart_requested:
        logger.info("Перезапускаю Cardinal…")
        os.execv(sys.executable, [sys.executable, "-m", "cardinal"])
    return 0


if __name__ == "__main__":
    sys.exit(main())