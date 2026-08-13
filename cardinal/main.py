"""Точка входа PlayerokCardinal: настройка логов, первичная настройка, запуск ядра."""
from __future__ import annotations

import asyncio
import os
import sys

from loguru import logger

from .logging_setup import setup_logging
from .settings import MAIN_CONFIG, ConfigError, load_main_settings


def main(argv: list[str] | None = None) -> int:
    """Запускает Cardinal. Возвращает код выхода процесса."""
    setup_logging()

    # Парсим аргументы командной строки
    args = argv if argv is not None else sys.argv[1:]
    offline_mode_flag = "--offline" in args or "-o" in args

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

    cardinal = Cardinal(settings)
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