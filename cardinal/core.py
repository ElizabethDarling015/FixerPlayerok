"""
Ядро PlayerokCardinal — класс `Cardinal`.

Связывает синхронную библиотеку `playerokapi` (curl_cffi + потоки) с asyncio-миром aiogram:

- `Runner.listen()` крутится в фоновом потоке и пересылает события в `asyncio.Queue`
  через `loop.call_soon_threadsafe` (см. `_runner_thread_loop`);
- потребитель очереди (`_consume_events`) раздаёт события модулям и уведомлениям;
- все вызовы синхронного `Account` из асинхронного кода — через `asyncio.to_thread`.
"""
from __future__ import annotations

import asyncio
import contextlib
import signal
import threading
import time
from typing import TYPE_CHECKING

from loguru import logger

from playerokapi.account import Account
from playerokapi.autodelivery import AutoDeliveryManager
from playerokapi.autoraise import AutoRaiseManager
from playerokapi.common.exceptions import RequestSendingError
from playerokapi.plugins import PluginManager
from playerokapi.updater.runner import Runner

from .localization import L10n
from .settings import (
    AUTODELIVERY_CONFIG,
    AUTORESPONSE_CONFIG,
    BLACKLIST_CONFIG,
    MainSettings,
    load_autodelivery_config,
    load_autoresponse_config,
    load_blacklist_config,
)

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher

    from .modules.base import BaseModule
    from .tg.notifications import Notifier


class _ToggleableAutoDelivery(AutoDeliveryManager):
    """Авто-выдача, уважающая переключатель модуля: при выключенном модуле склад «пуст»."""

    def __init__(self, cardinal: "Cardinal", **kwargs):
        super().__init__(**kwargs)
        self._cardinal = cardinal

    def reserve(self, item_name: str) -> str | None:
        if not self._cardinal.settings.modules.autodelivery:
            logger.info("Авто-выдача выключена — лот {!r} не выдаётся автоматически", item_name)
            return None
        return super().reserve(item_name)


class _ToggleableAutoRaise(AutoRaiseManager):
    """Автоподнятие, уважающее переключатель модуля: при выключенном модуле цикл пропускается."""

    def __init__(self, cardinal: "Cardinal", **kwargs):
        super().__init__(**kwargs)
        self._cardinal = cardinal

    def raise_all(self, account):
        if not self._cardinal.settings.modules.autoraise:
            return []
        return super().raise_all(account)


class Cardinal:
    """Собирает и запускает все части бота: Account, Runner, модули, Telegram."""

    def __init__(self, settings: MainSettings):
        self.settings = settings
        self.l10n = L10n(settings.language)
        self.started_at = time.time()

        self.account: Account | None = None
        self.runner: Runner | None = None
        self.plugin_manager = PluginManager()
        self.autodelivery_manager: AutoDeliveryManager | None = None
        self.autoraise_manager: AutoRaiseManager | None = None

        self.autoresponse_config = load_autoresponse_config(AUTORESPONSE_CONFIG)
        self.autodelivery_config = load_autodelivery_config(AUTODELIVERY_CONFIG)
        self.blacklist_config = load_blacklist_config(BLACKLIST_CONFIG)

        self.modules: list[BaseModule] = []
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.notifier: Notifier | None = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self.event_queue: asyncio.Queue | None = None
        self._stop_event: asyncio.Event | None = None
        self._tasks: list[asyncio.Task] = []
        self._runner_thread: threading.Thread | None = None

        # Флаг состояния подключения к Playerok API
        self._playerok_connected: bool = False
        self._playerok_connecting: bool = False
        self._plugins_loaded: bool = False
        self._consume_task: asyncio.Task | None = None

        #: Выставляется `request_restart()`: после остановки main.py перезапустит процесс.
        self.restart_requested = False

    # ------------------------------------------------------------------
    # Вспомогательное
    # ------------------------------------------------------------------

    @property
    def uptime(self) -> str:
        """Аптайм в виде `1д 02:03:04`."""
        seconds = int(time.time() - self.started_at)
        days, rest = divmod(seconds, 86400)
        hours, rest = divmod(rest, 3600)
        minutes, secs = divmod(rest, 60)
        prefix = f"{days}д " if days else ""
        return f"{prefix}{hours:02d}:{minutes:02d}:{secs:02d}"

    @property
    def playerok_connected(self) -> bool:
        """Подключен ли бот к Playerok API в данный момент."""
        return self._playerok_connected

    def spawn(self, coro) -> asyncio.Task:
        """Запускает фоновую asyncio-задачу под управлением Cardinal (отменится при остановке)."""
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.append(task)
        return task

    def request_shutdown(self) -> None:
        """Просит Cardinal остановиться (безопасно вызывать из хендлеров aiogram)."""
        if self._stop_event is not None:
            self._stop_event.set()

    def request_restart(self) -> None:
        """Просит Cardinal перезапуститься: мягкая остановка, затем main.py перезапустит процесс."""
        self.restart_requested = True
        self.request_shutdown()

    def reload_configs(self) -> str:
        """
        Перечитывает `autoresponse.toml`, `autodelivery.toml` и `blacklist.toml` без перезапуска.

        :return: Короткая сводка для ответа в TG (сколько команд, лотов и ников загружено).
        """
        self.autoresponse_config = load_autoresponse_config(AUTORESPONSE_CONFIG)
        self.autodelivery_config = load_autodelivery_config(AUTODELIVERY_CONFIG)
        self.blacklist_config = load_blacklist_config(BLACKLIST_CONFIG)
        self.apply_autodelivery_config()
        return (f"команд автоответчика: {len(self.autoresponse_config.commands)}, "
                f"лотов авто-выдачи: {len(self.autodelivery_config.lots)}, "
                f"в чёрном списке: {len(self.blacklist_config.usernames)}")

    def is_blacklisted(self, username: str | None) -> bool:
        """Проверяет, находится ли покупатель в чёрном списке (без учёта регистра)."""
        return self.blacklist_config.contains(username)

    def apply_autodelivery_config(self) -> None:
        """Синхронизирует склады `AutoDeliveryManager` с текущим `autodelivery_config`."""
        if self.autodelivery_manager is not None:
            self.autodelivery_manager.stock_paths = {
                name: lot.stock_file for name, lot in self.autodelivery_config.lots.items()
            }

    # ------------------------------------------------------------------
    # Управление подключением к Playerok API
    # ------------------------------------------------------------------

    async def connect_playerok(self) -> dict:
        """Подключается к Playerok API вручную (кнопка в TG-панели)."""
        if self._playerok_connected:
            return {"ok": True,
                    "message": "Уже подключен к Playerok",
                    "username": self.account.username if self.account else None}

        if self._playerok_connecting:
            return {"ok": False, "message": "Подключение уже выполняется", "username": None}

        self._playerok_connecting = True
        try:
            if self.account is None:
                self.account = Account(
                    cookies=self.settings.playerok.cookies,
                    user_agent=self.settings.playerok.user_agent,
                    proxy=self.settings.playerok.proxy,
                    requests_timeout=int(self.settings.playerok.requests_timeout),
                )

            logger.info("Авторизуемся на Playerok (ручное подключение)…")
            auth_attempts = 3
            for attempt in range(1, auth_attempts + 1):
                try:
                    await asyncio.to_thread(self.account.get)
                    break
                except RequestSendingError as exc:
                    if attempt == auth_attempts:
                        raise
                    logger.warning("Сеть недоступна (попытка {}/{}): {} — повтор через 10 с",
                                   attempt, auth_attempts, exc)
                    await asyncio.sleep(10)

            balance = (self.account.profile.balance.value
                       if self.account.profile and self.account.profile.balance else "?")
            logger.success("Авторизованы как {} (баланс: {})", self.account.username, balance)

            if self.autodelivery_manager is None:
                self.autodelivery_manager = _ToggleableAutoDelivery(
                    self,
                    config={name: lot.stock_file for name, lot in self.autodelivery_config.lots.items()},
                    delivery_text_template=self.settings.autodelivery.delivery_text,
                    ledger_path=self.settings.autodelivery.ledger_file,
                )
            if self.autoraise_manager is None:
                self.autoraise_manager = _ToggleableAutoRaise(
                    self,
                    raise_interval=self.settings.autoraise.interval,
                    min_balance_reserve=self.settings.autoraise.min_balance_reserve,
                )

            self.plugin_manager.attach_to_account(self.account)
            if not self._plugins_loaded:
                self.plugin_manager.load_plugins()
                self._plugins_loaded = True

            self.runner = Runner(
                self.account,
                plugin_manager=self.plugin_manager,
                autodelivery_manager=self.autodelivery_manager,
                autoraise_manager=self.autoraise_manager,
            )

            self._runner_thread = threading.Thread(target=self._runner_thread_loop, daemon=True,
                                                   name="cardinal-runner")
            self._runner_thread.start()
            self._consume_task = self.spawn(self._consume_events())

            self._playerok_connected = True
            logger.success("Playerok API подключён")

            # Уведомляем админов об успешном подключении
            if self.notifier is not None:
                try:
                    await self.notifier.notify_playerok_connected(self.account.username, balance)
                except Exception as exc:
                    logger.warning("Не удалось отправить уведомление о подключении: {}", exc)

            return {"ok": True, "message": f"Подключён как {self.account.username}",
                    "username": self.account.username}

        except Exception as exc:
            logger.error("Ошибка подключения к Playerok: {}", exc)
            return {"ok": False, "message": str(exc), "username": None}
        finally:
            self._playerok_connecting = False

    async def disconnect_playerok(self) -> dict:
        """Отключается от Playerok API вручную (кнопка в TG-панели)."""
        if not self._playerok_connected:
            return {"ok": True, "message": "Уже отключен от Playerok"}

        try:
            if self.runner is not None:
                with contextlib.suppress(Exception):
                    self.runner.stop()
            if self._runner_thread is not None:
                await asyncio.to_thread(self._runner_thread.join, 5.0)
                self._runner_thread = None
            if self._consume_task is not None:
                self._consume_task.cancel()
                self._consume_task = None

            self.runner = None
            self.account = None
            self._playerok_connected = False
            logger.info("Playerok API отключён")

            # Уведомляем админов об отключении
            if self.notifier is not None:
                try:
                    await self.notifier.notify_playerok_disconnected()
                except Exception as exc:
                    logger.warning("Не удалось отправить уведомление об отключении: {}", exc)

            return {"ok": True, "message": "Отключено от Playerok"}

        except Exception as exc:
            logger.error("Ошибка отключения от Playerok: {}", exc)
            return {"ok": False, "message": str(exc)}

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Запускает Cardinal и работает до `request_shutdown()` (или сигнала SIGTERM/SIGINT)."""
        self.loop = asyncio.get_running_loop()
        self.event_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                self.loop.add_signal_handler(sig, self.request_shutdown)

        # --- Проверяем offline_mode ---
        offline_mode = self.settings.playerok.offline_mode

        if not offline_mode:
            # --- Аккаунт Playerok ---
            self.account = Account(
                cookies=self.settings.playerok.cookies,
                user_agent=self.settings.playerok.user_agent,
                proxy=self.settings.playerok.proxy,
                requests_timeout=int(self.settings.playerok.requests_timeout),
            )
            logger.info("Авторизуемся на Playerok…")
            auth_attempts = 5
            for attempt in range(1, auth_attempts + 1):
                try:
                    await asyncio.to_thread(self.account.get)
                    break
                except RequestSendingError as exc:
                    if attempt == auth_attempts:
                        raise
                    logger.warning("Сеть недоступна (попытка {}/{}): {} — повтор через 15 с",
                                   attempt, auth_attempts, exc)
                    await asyncio.sleep(15)
            balance = self.account.profile.balance.value if self.account.profile and self.account.profile.balance else "?"
            logger.success("Авторизованы как {} (баланс: {})", self.account.username, balance)

            # --- Менеджеры библиотеки ---
            self.autodelivery_manager = _ToggleableAutoDelivery(
                self,
                config={name: lot.stock_file for name, lot in self.autodelivery_config.lots.items()},
                delivery_text_template=self.settings.autodelivery.delivery_text,
                ledger_path=self.settings.autodelivery.ledger_file,
            )
            self.autoraise_manager = _ToggleableAutoRaise(
                self,
                raise_interval=self.settings.autoraise.interval,
                min_balance_reserve=self.settings.autoraise.min_balance_reserve,
            )

            # --- Плагины ---
            self.plugin_manager.attach_to_account(self.account)
            self.plugin_manager.load_plugins()
            self._plugins_loaded = True

            # --- Runner ---
            self.runner = Runner(
                self.account,
                plugin_manager=self.plugin_manager,
                autodelivery_manager=self.autodelivery_manager,
                autoraise_manager=self.autoraise_manager,
            )

            self._playerok_connected = True
        else:
            logger.warning("🔧 OFFLINE MODE: Playerok API отключён. Работает только Telegram-панель.")
            logger.info("Для подключения к Playerok используйте кнопку в меню /menu → Система → Подключить Playerok")

        # --- Модули ---
        from .modules import build_modules
        self.modules = build_modules(self)

        # --- Telegram ---
        if self.settings.telegram.token:
            from .tg.bot import setup_telegram
            self.bot, self.dispatcher, self.notifier = setup_telegram(self)
            self.spawn(self._tg_polling())
        else:
            logger.warning("Токен Telegram-бота не задан — панель управления и уведомления недоступны.")

        for module in self.modules:
            await module.on_start()

        # Запускаем Runner только если не в offline_mode
        if not offline_mode and self.runner is not None:
            self._runner_thread = threading.Thread(
                target=self._runner_thread_loop,
                daemon=True,
                name="cardinal-runner"
            )
            self._runner_thread.start()
            self.spawn(self._consume_events())

        logger.success("PlayerokCardinal запущен. Модули: {}", ", ".join(
            name for name in type(self.settings.modules).model_fields
            if getattr(self.settings.modules, name)
        ) or "—")

        if offline_mode:
            logger.info("Статус: OFFLINE MODE — только Telegram-панель")
            # Стандартное стартовое уведомление (с кнопкой «В главное меню»)
            if self.notifier is not None:
                try:
                    logger.info("Отправляем стартовое уведомление (offline)...")
                    await self.notifier.notify_started(missed_deals=[])
                    logger.success("Стартовое уведомление успешно отправлено")
                except Exception as exc:
                    logger.exception("ОШИБКА при отправке стартового уведомления: {}", exc)
        else:
            # --- Собираем пропущенные сделки (за время простоя) ---
            missed_deals = []
            try:
                from datetime import datetime, timedelta, timezone
                # Получаем последние 50 сделок
                deals = await asyncio.to_thread(self.account.get_deals, count=50)
                if deals:
                    # Порог: сделки за последние 24 часа
                    threshold = datetime.now(timezone.utc) - timedelta(hours=24)
                    for deal in deals:
                        if deal is None or deal.raw_status is None:
                            continue
                        if deal.raw_status.name in ("PAID", "CONFIRMED"):
                            created = getattr(deal, "created_at", None)
                            if created and created >= threshold:
                                missed_deals.append(deal)
                if missed_deals:
                    logger.info("Найдено {} сделок за время простоя", len(missed_deals))
            except Exception as exc:
                logger.warning("Не удалось проверить пропущенные сделки при старте: {}", exc)

            if self.notifier is not None:
                try:
                    logger.info("Отправляем стартовое уведомление...")
                    await self.notifier.notify_started(missed_deals=missed_deals)
                    logger.success("Стартовое уведомление успешно отправлено")
                except Exception as exc:
                    logger.exception("ОШИБКА при отправке стартового уведомления: {}", exc)

        await self._stop_event.wait()
        await self._shutdown()

    async def _shutdown(self) -> None:
        logger.info("Останавливаем PlayerokCardinal…")
        for module in self.modules:
            with contextlib.suppress(Exception):
                await module.on_stop()
        if self.runner is not None:
            with contextlib.suppress(Exception):
                self.runner.stop()
        if self._runner_thread is not None:
            await asyncio.to_thread(self._runner_thread.join, 5.0)
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self.bot is not None:
            with contextlib.suppress(Exception):
                await self.bot.session.close()
        logger.info("PlayerokCardinal остановлен.")

    # ------------------------------------------------------------------
    # Фоновые циклы
    # ------------------------------------------------------------------

    def _runner_thread_loop(self) -> None:
        """Крутится в фоновом потоке: события Runner пересылаются в asyncio-очередь."""
        try:
            for event in self.runner.listen(requests_delay=self.settings.playerok.requests_delay,
                                            ignore_exceptions=True):
                self.loop.call_soon_threadsafe(self.event_queue.put_nowait, event)
        except Exception as exc:
            logger.exception("Поток Runner упал")
            self.loop.call_soon_threadsafe(self.event_queue.put_nowait, exc)

    async def _consume_events(self) -> None:
        """Раздаёт события из очереди модулям и уведомлениям (ошибка одного не роняет остальных)."""
        while True:
            event = await self.event_queue.get()
            if isinstance(event, BaseException):
                if self.notifier is not None:
                    with contextlib.suppress(Exception):
                        await self.notifier.notify_error(f"{type(event).__name__}: {event}")
                continue
            for module in self.modules:
                try:
                    await module.on_event(event)
                except Exception:
                    logger.exception("Ошибка модуля {} при обработке события {}",
                                     module.name, type(event).__name__)
            if self.notifier is not None:
                try:
                    await self.notifier.on_event(event)
                except Exception:
                    logger.exception("Ошибка при отправке уведомления о событии {}", type(event).__name__)

    async def _tg_polling(self) -> None:
        """Long-polling aiogram (отменяется при остановке Cardinal)."""
        try:
            await self.dispatcher.start_polling(self.bot, handle_signals=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Polling Telegram-бота упал")