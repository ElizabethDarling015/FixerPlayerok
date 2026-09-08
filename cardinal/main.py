"""Точка входа PlayerokCardinal: настройка логов, первичная настройка, запуск ядра."""
from __future__ import annotations

import asyncio
import os
import re
import sys

from loguru import logger

from .logging_setup import setup_logging
from .settings import MAIN_CONFIG, ConfigError, load_main_settings

#: --add-proxy=<url> — добавляет прокси в ту же БД, что и Telegram-меню Настройки ->
#: Прокси, но БЕЗ запуска бота вообще. Ровно для сценария "нет VPN, нет прокси, панель
#: без прокси не поднять" — нужно куда-то положить первый прокси ДО того, как впервые
#: запустить бота с --proxyN. Схема URL (socks5/socks5h/socks4/http/https) определяет
#: протокол автоматически; без схемы (host:port[:user:pass]) считается HTTP.
_ADD_PROXY_RE = re.compile(r"^--add-proxy=(.+)$")


def _handle_add_proxy_flag(args: list[str]) -> int | None:
    """
    Возвращает код возврата процесса, если среди аргументов был --add-proxy=...
    (в этом случае main() должен сразу завершиться, бота не запуская), иначе None —
    значит флага не было, продолжаем обычный запуск.
    """
    for arg in args:
        m = _ADD_PROXY_RE.match(arg)
        if not m:
            continue
        url = m.group(1)
        from . import proxy_store
        from .proxy_tools import parse_proxy_text
        parsed = parse_proxy_text(url)
        if not parsed:
            logger.error(
                "--add-proxy: не удалось разобрать {!r}. Поддерживаемые форматы:\n"
                "  socks5://user:pass@host:port\n"
                "  http://host:port\n"
                "  host:port  (без схемы считается HTTP)\n"
                "  host:port:user:pass",
                url,
            )
            return 1
        proxy = proxy_store.add_or_update_proxy(
            parsed["type"], parsed["host"], parsed["port"], parsed["username"], parsed["password"],
        )
        ordinal = next(
            (i for i, p in enumerate(proxy_store.list_proxies(), start=1) if p["id"] == proxy["id"]),
            None,
        )
        logger.success(
            "Прокси сохранён: {} {}:{} -> используйте --proxy{} для Telegram-сессии "
            "при следующем запуске. Активировать для Playerok можно будет отдельно "
            "через Telegram-меню Настройки -> Прокси, когда панель поднимется.",
            parsed["type"].upper(), parsed["host"], parsed["port"], ordinal,
        )
        return 0
    return None


#: --proxy1, --proxy2, ... — разовый выбор N-го сохранённого прокси (по порядку
#: добавления через Telegram-меню Настройки -> Прокси) для Telegram-сессии бота
#: на ЭТОТ запуск. Playerok этот флаг не видит — Account/Runner продолжают
#: подключаться как настроено отдельно (обычно напрямую, домашним IP); см.
#: cardinal/proxy_store.py, почему это разделено намеренно.
_PROXY_FLAG_RE = re.compile(r"^--proxy(\d+)$")


def _parse_cli_proxy_flag(args: list[str]) -> str | None:
    """
    Возвращает URL прокси для Telegram-сессии, если среди аргументов есть --proxyN,
    иначе None. Бросает SystemExit с понятным сообщением, если номер не сохранён в
    БД — по договорённости флаг обязан падать явно, а не тихо стартовать без прокси
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
        logger.info(
            "Флаг --proxy{}: Telegram-сессия разово пойдёт через {}:{} (только на этот "
            "процесс; Playerok этот флаг не затрагивает)", n, proxy["host"], proxy["port"],
        )
        return build_proxy_url(proxy)
    return None


def main(argv: list[str] | None = None) -> int:
    """Запускает Cardinal. Возвращает код выхода процесса."""
    setup_logging()

    # Парсим аргументы командной строки
    args = argv if argv is not None else sys.argv[1:]

    # --add-proxy=... — самостоятельная команда, бота не запускает, конфиг не нужен.
    add_proxy_result = _handle_add_proxy_flag(args)
    if add_proxy_result is not None:
        return add_proxy_result

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