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
from playerokapi.common.enums import ItemDealDirections, ItemStatuses
from playerokapi.common.exceptions import RequestSendingError
from playerokapi.plugins import PluginManager
from playerokapi.updater.events import ItemPaidEvent, ItemRaisedEvent, SessionExpiredEvent
from playerokapi.updater.runner import Runner

from .localization import L10n
from .stats_store import ACTION_DELIVERY, ACTION_RAISE, StatsStore
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

    # add_stock (пополнение склада из TG-панели) — публичный метод AutoDeliveryManager.


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

        #: Счётчики «что бот сделал сам» (выдачи, поднятия, автоответы) — раздел «Статистика».
        self.stats = StatsStore()

        self.modules: list[BaseModule] = []
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.notifier: Notifier | None = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self.event_queue: asyncio.Queue | None = None
        self._stop_event: asyncio.Event | None = None
        self._tasks: list[asyncio.Task] = []
        self._runner_thread: threading.Thread | None = None

        #: Выставляется `request_restart()`: после остановки main.py перезапустит процесс.
        self.restart_requested = False

        # Состояние вахтёра опроса (heartbeat): предупреждение уже отправлено и не сброшено.
        self._poll_stall_warned = False
        # `time.monotonic()` старта вахтёра — точка отсчёта, пока не было ни одного успешного опроса.
        self._poll_watch_started_at: float | None = None

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
        """
        Синхронизирует склады и пер-лотовые тексты выдачи `AutoDeliveryManager`
        с текущим `autodelivery_config`.
        """
        if self.autodelivery_manager is not None:
            self.autodelivery_manager.stock_paths = {
                name: lot.stock_file for name, lot in self.autodelivery_config.lots.items()
            }
            self.autodelivery_manager.delivery_texts = {
                name: lot.delivery_text for name, lot in self.autodelivery_config.lots.items()
                if lot.delivery_text
            }

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

        # --- Аккаунт Playerok ---
        self.account = Account(
            cookies=self.settings.playerok.cookies,
            user_agent=self.settings.playerok.user_agent,
            proxy=self.settings.playerok.proxy,
            requests_timeout=int(self.settings.playerok.requests_timeout),
        )
        logger.info("Авторизуемся на Playerok…")
        # Сетевые сбои (медленный прокси, curl 28) на старте не должны убивать бота —
        # особенно после рестарта из TG-панели, когда поднять его вручную некому.
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
            delivery_texts={name: lot.delivery_text
                            for name, lot in self.autodelivery_config.lots.items() if lot.delivery_text},
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

        # --- Модули ---
        from .modules import build_modules
        self.modules = build_modules(self)

        # --- Runner ---
        self.runner = Runner(
            self.account,
            plugin_manager=self.plugin_manager,
            autodelivery_manager=self.autodelivery_manager,
            autoraise_manager=self.autoraise_manager,
        )

        # --- Telegram ---
        if self.settings.telegram.token:
            from .tg.bot import setup_telegram
            self.bot, self.dispatcher, self.notifier = setup_telegram(self)
            self.spawn(self._tg_polling())
        else:
            logger.warning("Токен Telegram-бота не задан — панель управления и уведомления недоступны.")

        for module in self.modules:
            await module.on_start()

        self._runner_thread = threading.Thread(target=self._runner_thread_loop, daemon=True,
                                               name="cardinal-runner")
        self._runner_thread.start()
        self.spawn(self._consume_events())
        self.spawn(self._poll_watchdog())

        logger.success("PlayerokCardinal запущен. Модули: {}", ", ".join(
            name for name in type(self.settings.modules).model_fields
            if getattr(self.settings.modules, name)
        ) or "—")
        if self.notifier is not None:
            with contextlib.suppress(Exception):
                await self.notifier.notify_started()

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
        self.stats.close()
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
        except Exception as exc:  # noqa: BLE001 — пробрасываем любой сбой в основной цикл
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
            if isinstance(event, SessionExpiredEvent):
                # Смерть сессии — критичное служебное событие: отдельное уведомление
                # с инструкцией по замене токена (модулям оно не нужно).
                if self.notifier is not None:
                    with contextlib.suppress(Exception):
                        await self.notifier.notify_session_expired(event.cause)
                continue
            try:
                self._record_bot_action(event)
            except Exception:
                logger.exception("Не удалось записать статистику по событию {}", type(event).__name__)
            for module in self.modules:
                try:
                    await module.on_event(event)
                except Exception:
                    logger.exception("Ошибка модуля {} при обработке события {}",
                                     module.name, type(event).__name__)
            try:
                # После модулей: autorestore успевает пересоздать лот, и снимаем мы уже копию.
                await self.maybe_deactivate_empty_lot(event)
            except Exception:
                logger.exception("Ошибка автодеактивации лота по событию {}", type(event).__name__)
            if self.notifier is not None:
                try:
                    await self.notifier.on_event(event)
                except Exception:
                    logger.exception("Ошибка при отправке уведомления о событии {}", type(event).__name__)

    def _record_bot_action(self, event) -> None:
        """
        Учитывает автоматическое действие бота в `StatsStore`.

        Поднятие лота — по `ItemRaisedEvent`; выдача товара — по `ItemPaidEvent`, у которого
        журнал выдач подтверждает отправку («sent») — тот же приём, что в `Notifier` (авто-выдача
        выполняется Runner'ом до того, как событие дошло сюда). Автоответы и приветствия
        записывают сами модули (константы `ACTION_AUTORESPONSE`/`ACTION_GREETING`).
        """
        if isinstance(event, ItemRaisedEvent):
            self.stats.record(ACTION_RAISE)
        elif isinstance(event, ItemPaidEvent):
            deal = event.deal
            manager = self.autodelivery_manager
            if (deal is not None and manager is not None and manager.ledger is not None
                    and manager.ledger.get_state(deal.id) == "sent"):
                self.stats.record(ACTION_DELIVERY)

    # ------------------------------------------------------------------
    # Автодеактивация лота при пустом складе
    # ------------------------------------------------------------------

    def find_published_item_ids(self, item_name: str, max_pages: int = 10) -> list[str]:
        """
        Ищет ID своих активных (`APPROVED`) лотов с точным названием `item_name`.

        Синхронный метод (сеть) — из async-кода вызывать через `asyncio.to_thread`.

        :param item_name: Точное название лота, как на Playerok.
        :param max_pages: Ограничение на число страниц пагинации (страховка от бесконечного цикла).
        :return: Список ID найденных лотов (пустой, если таких лотов нет).
        """
        found: list[str] = []
        after_cursor: str | None = None
        for _ in range(max_pages):
            page = self.account.get_my_items(status=ItemStatuses.APPROVED, count=50,
                                             after_cursor=after_cursor)
            if not page or not page.items:
                break
            found.extend(item.id for item in page.items
                         if item and item.id and item.name == item_name)
            page_info = getattr(page, "page_info", None)
            if not page_info or not page_info.has_next_page:
                break
            next_cursor = page_info.end_cursor
            if not next_cursor or next_cursor == after_cursor:
                # Пустой/неподвижный курсор — защита от зацикливания (как в remove_all_items).
                break
            after_cursor = next_cursor
        return found

    def deactivate_lot(self, item_name: str) -> int:
        """
        Снимает лот с публикации: удаляет (`remove_item`) все свои активные лоты с этим названием.

        Отдельной мутации «снять с публикации» на Playerok нет — единственный способ убрать лот
        из выдачи это `removeItem`. Лот можно вернуть, пополнив склад и создав лот заново
        (в т.ч. модулем autorestore).

        Синхронный метод (сеть) — из async-кода вызывать через `asyncio.to_thread`.

        :param item_name: Точное название лота.
        :return: Сколько лотов реально снято с публикации.
        """
        return sum(1 for item_id in self.find_published_item_ids(item_name)
                   if self.account.remove_item(item_id))

    async def maybe_deactivate_empty_lot(self, event) -> None:
        """
        Снимает лот с публикации, если после продажи его склад авто-выдачи опустел.

        Работает только при включённой настройке `[autodelivery] deactivate_on_empty` и только
        для лотов, у которых не выставлен персональный флаг `disable_deactivate`. Ошибки
        деактивации не должны мешать обработке события — они логируются и уходят админу
        в Telegram.
        """
        if not isinstance(event, ItemPaidEvent) or not self.settings.autodelivery.deactivate_on_empty:
            return
        deal = event.deal
        item_name = deal.item.name if deal is not None and deal.item is not None else None
        if not item_name:
            return
        if deal.direction is not None and deal.direction is not ItemDealDirections.OUT:
            return  # чужая покупка (direction=IN) — не наш лот
        lot = self.autodelivery_config.lots.get(item_name)
        manager = self.autodelivery_manager
        if lot is None or lot.disable_deactivate or manager is None:
            return
        if manager.get_stock_size(item_name) > 0:
            return

        try:
            removed = await asyncio.to_thread(self.deactivate_lot, item_name)
        except Exception as exc:  # noqa: BLE001 — деактивация не должна ронять обработку события
            logger.exception("Не удалось снять с публикации лот {!r} с пустым складом", item_name)
            if self.notifier is not None:
                with contextlib.suppress(Exception):
                    await self.notifier.notify_deactivate_failed(item_name, str(exc))
            return

        if not removed:
            logger.info("Автодеактивация: активных лотов с названием {!r} не найдено", item_name)
            return
        logger.success("Склад лота {!r} опустел — лот снят с публикации (шт.: {})", item_name, removed)
        if self.notifier is not None:
            with contextlib.suppress(Exception):
                await self.notifier.notify_lot_deactivated(item_name)

    def check_poll_health(self, now: float) -> str | None:
        """
        Чистая проверка вахтёра опроса (без сна и уведомлений — удобно тестировать).

        Сравнивает `now` (time.monotonic) с `runner.last_success_at` (либо со стартом вахтёра,
        пока успешных опросов ещё не было) и порогом `[playerok] poll_warn_minutes`.

        :return: `"stalled"` — пора предупредить (взводится флаг, повторно не вернётся до
            восстановления); `"recovered"` — опрос ожил после предупреждения (флаг сброшен);
            `None` — делать ничего не нужно (в т.ч. при `poll_warn_minutes = 0`).
        """
        warn_minutes = self.settings.playerok.poll_warn_minutes
        if warn_minutes <= 0 or self.runner is None:
            return None
        last = self.runner.last_success_at
        if last is None:
            last = self._poll_watch_started_at if self._poll_watch_started_at is not None else now
        stalled = (now - last) >= warn_minutes * 60
        if stalled and not self._poll_stall_warned:
            self._poll_stall_warned = True
            return "stalled"
        if not stalled and self._poll_stall_warned:
            self._poll_stall_warned = False
            return "recovered"
        return None

    async def _poll_watchdog(self) -> None:
        """Вахтёр опроса Playerok: раз в 60 с проверяет `runner.last_success_at` (heartbeat)."""
        self._poll_watch_started_at = time.monotonic()
        while True:
            await asyncio.sleep(60)
            action = self.check_poll_health(time.monotonic())
            if action is None or self.notifier is None:
                continue
            try:
                if action == "stalled":
                    await self.notifier.notify_poll_stalled(self.settings.playerok.poll_warn_minutes)
                else:
                    await self.notifier.notify_poll_recovered()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Не удалось отправить уведомление вахтёра опроса")

    async def _tg_polling(self) -> None:
        """Long-polling aiogram (отменяется при остановке Cardinal)."""
        try:
            await self.dispatcher.start_polling(self.bot, handle_signals=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Polling Telegram-бота упал")
