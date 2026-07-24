"""
Логирование Cardinal: loguru (цветная консоль + файл с ротацией) с перехватом stdlib-логов.

Библиотека `playerokapi` пишет через стандартный `logging` — `InterceptHandler` пересылает
её записи в loguru, чтобы весь вывод был в одном формате и в одном файле.
"""
from __future__ import annotations

import inspect
import logging
import os
import sys

from loguru import logger

#: Файл лога по умолчанию (используется также разделом «Логи» в TG-панели).
LOG_FILE = os.path.join("storage", "logs", "cardinal.log")


class InterceptHandler(logging.Handler):
    """Пересылает записи stdlib `logging` в loguru (с корректными level/exc_info/глубиной стека)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Ищем кадр стека, из которого реально пришёл лог (пропуская сам модуль logging).
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(console_level: str = "INFO", log_file: str = LOG_FILE) -> None:
    """
    Настраивает loguru: цветная консоль + файл с ротацией 10 МБ и хранением 14 дней.

    Все stdlib-логгеры (включая `playerokapi.*` и `aiogram`) перенаправляются в loguru.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=console_level,
        format="<green>{time:HH:mm:ss}</green> <level>{level: <8}</level> <cyan>{name}</cyan> — {message}",
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention=14,
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} {level: <8} {name}:{line} — {message}",
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    # aiogram довольно многословен на INFO — приглушаем до WARNING.
    logging.getLogger("aiogram").setLevel(logging.WARNING)
