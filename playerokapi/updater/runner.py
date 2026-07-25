"""
`Runner` — генератор событий аккаунта (аналог `FunPayAPI.updater.runner.Runner`).

Использует несколько параллельных источников событий:

1. WebSocket-подписки `chatUpdated` и `chatMarkedAsRead` (эндпоинт `wss://ws.playerok.com/graphql`,
   протокол `graphql-transport-ws`: `connection_init` → `connection_ack` → `subscribe`, входящие
   кадры `next`/`error`/`complete`, серверные `ping` получают ответ `pong`) — мгновенно дают
   `NewMessageEvent`, `ChatInitializedEvent` (при первом обнаружении чата) и `ItemPaidEvent`
   (по системному маркеру `{{ITEM_PAID}}` в тексте сообщения — аналогично `alleexxeeyy/PlayerokAPI`).
2. Периодический опрос раз в `requests_delay` секунд (фоновый поток) — обновляет профиль/баланс
   (`Account.get()`) и сравнивает список сделок (`Account.get_deals()`, с полной пагинацией) со
   снимком с предыдущего опроса, порождая `NewDealEvent`/`DealStatusChangedEvent` (плюс более
   конкретные события — `DealConfirmedEvent`, `DealRolledBackEvent`, `ItemSentEvent`, а также
   `DealHasProblemEvent`/`DealProblemResolvedEvent` — по изменению `ItemDeal.has_problem`). Тем же
   потоком, тем же интервалом, сравнивает список своих отзывов (`Account.get_my_reviews()`) со
   снимком с предыдущего опроса, порождая `NewReviewEvent`.
3. Опционально — таймер автоподнятия лотов (если передан `autoraise_manager`), раз в
   `autoraise_manager.raise_interval` секунд, порождающий `ItemRaisedEvent`/`InsufficientBalanceEvent`.

`ItemPaidEvent` дедуплицируется по `deal_id` между источниками (WS-маркер и поллинг) и — при наличии
SQLite-журнала выдач (`AutoDeliveryManager.ledger`) — между перезапусками процесса, так что одна
оплата порождает не более одного события (и одной авто-выдачи).

При наличии `plugin_manager` на каждое событие (и на старт/стоп) вызываются соответствующие хуки.
При наличии `autodelivery_manager` на `ItemPaidEvent` автоматически запускается выдача товара.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid

import websocket

from .. import parser
from ..common.enums import EventTypes, Hooks, ItemDealDirections
from ..graphql_queries import QUERIES
from . import events

logger = logging.getLogger("playerokapi.runner")

_WS_URL = "wss://ws.playerok.com/graphql"
_WS_ORIGIN = "https://playerok.com"
_WS_SUBPROTOCOL = "graphql-transport-ws"

# Максимальная длина текста сообщения в логах — чтобы длинные сообщения не раздували лог.
_LOG_TEXT_LIMIT = 200

# Максимум страниц за один цикл поллинга — защита от бесконечной пагинации при сбоящем курсоре.
_MAX_POLL_PAGES = 20

# Подписки WS по умолчанию: базовые чаты + seller-полезные item/chatCreated.
_DEFAULT_WS_SUBSCRIPTIONS = (
    "chatUpdated",
    "chatMarkedAsRead",
    "itemUpdated",
    "itemCreated",
    "chatCreated",
)


def _truncate_for_log(text: str | None, limit: int = _LOG_TEXT_LIMIT) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ⏎ ")
    if len(text) <= limit:
        return text
    return text[:limit] + f"… (+{len(text) - limit} симв.)"

# Соответствие "сырых" статусов сделки, после изменения на которые нужно породить более
# конкретное событие в дополнение к общему `DealStatusChangedEvent`.
_SPECIFIC_STATUS_EVENTS = {
    "CONFIRMED": events.DealConfirmedEvent,
    "CONFIRMED_AUTOMATICALLY": events.DealConfirmedAutomaticallyEvent,
    "ROLLED_BACK": events.DealRolledBackEvent,
    "SENT": events.ItemSentEvent,
}

# Соответствие типа события фиксированному хуку плагинной системы (см. `common.enums.Hooks`).
_EVENT_HOOK_MAP = {
    EventTypes.CHAT_INITIALIZED: Hooks.INIT_MESSAGE,
    EventTypes.NEW_MESSAGE: Hooks.NEW_MESSAGE,
    EventTypes.NEW_DEAL: Hooks.NEW_DEAL,
    EventTypes.DEAL_STATUS_CHANGED: Hooks.DEAL_STATUS_CHANGED,
    EventTypes.DEAL_CONFIRMED: Hooks.DEAL_CONFIRMED,
    EventTypes.DEAL_CONFIRMED_AUTOMATICALLY: Hooks.DEAL_CONFIRMED_AUTOMATICALLY,
    EventTypes.DEAL_ROLLED_BACK: Hooks.DEAL_ROLLED_BACK,
    EventTypes.DEAL_HAS_PROBLEM: Hooks.DEAL_HAS_PROBLEM,
    EventTypes.DEAL_PROBLEM_RESOLVED: Hooks.DEAL_PROBLEM_RESOLVED,
    EventTypes.NEW_REVIEW: Hooks.NEW_REVIEW,
    EventTypes.ITEM_PAID: Hooks.ITEM_PAID,
    EventTypes.ITEM_SENT: Hooks.ITEM_SENT,
    EventTypes.ITEM_RAISED: Hooks.ITEM_RAISED,
    EventTypes.INSUFFICIENT_BALANCE: Hooks.INSUFFICIENT_BALANCE,
}


class Runner:
    """
    Генератор событий аккаунта.

    :param account: Аккаунт, за которым нужно следить (должен быть после `Account(...).get()`).
    :param plugin_manager: Менеджер плагинов (`playerokapi.plugins.PluginManager`), опционально.
    :param autodelivery_manager: Менеджер авто-выдачи (`playerokapi.autodelivery.AutoDeliveryManager`), опционально.
    :param ws_subscriptions: Имена GraphQL-подписок для WS. По умолчанию —
        chatUpdated/chatMarkedAsRead + itemUpdated/itemCreated/chatCreated.
    """

    def __init__(self, account, plugin_manager=None, autodelivery_manager=None, autoraise_manager=None,
                 ws_subscriptions: tuple[str, ...] | list[str] | None = None):
        self.account = account
        self.plugin_manager = plugin_manager
        self.autodelivery_manager = autodelivery_manager
        self.autoraise_manager = autoraise_manager
        self.ws_subscriptions = tuple(ws_subscriptions) if ws_subscriptions is not None else _DEFAULT_WS_SUBSCRIPTIONS
        account._runner = self

        self._event_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._known_chats: dict[str, int] = {}
        self._known_last_message_ids: dict[str, str] = {}
        self._known_deals: dict[str, str | None] = {}
        self._known_deal_problems: dict[str, bool] = {}
        self._known_reviews: set[str] = set()
        # Отдельные флаги инициализации снимков: `not self._known_deals` не годится —
        # пустой первый снимок (нет сделок/отзывов) глотал бы первое настоящее событие.
        self._deals_initialized = False
        self._reviews_initialized = False
        # In-memory дедуп `ItemPaidEvent` по deal_id (плюс SQLite-журнал, если настроен).
        self._paid_deal_ids: set[str] = set()
        self._ws = None
        self._ignore_exceptions = True

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def listen(self, requests_delay: float = 5.0, ignore_exceptions: bool = True):
        """
        Запускает прослушивание событий аккаунта. Генератор работает до вызова `stop()`.

        :param requests_delay: Задержка между опросами профиля/баланса и списка сделок, в секундах.
        :param ignore_exceptions: Игнорировать ли исключения, возникающие в фоновых потоках
            (WS-подключение, опрос) — если `False`, они будут подняты повторно из самого
            генератора `listen()` и остановят `Runner`.
        :yields: Объекты `updater.events.BaseEvent` (и его подклассы) по мере появления.
        """
        self._ignore_exceptions = ignore_exceptions
        self._dispatch_hook(Hooks.PRE_START.value)
        self._stop_event.clear()
        self._warn_about_stuck_deliveries()
        self._seed_known_chats()

        poll_thread = threading.Thread(target=self._poll_loop, args=(requests_delay,), daemon=True)
        ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        poll_thread.start()
        ws_thread.start()
        if self.autoraise_manager is not None:
            autoraise_thread = threading.Thread(target=self._autoraise_loop, daemon=True)
            autoraise_thread.start()
        self._dispatch_hook(Hooks.POST_START.value)

        try:
            while not self._stop_event.is_set():
                try:
                    event = self._event_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if isinstance(event, BaseException):
                    # Исключение фонового потока (при ignore_exceptions=False) — перевыбрасываем
                    # в вызывающий код, вместо того чтобы молча уронить поток.
                    raise event
                self._handle_autodelivery(event)
                self._dispatch_event_hook(event)
                yield event
        finally:
            self.stop()

    def stop(self) -> None:
        """Останавливает `Runner` (фоновые потоки завершатся в течение нескольких секунд)."""
        if self._stop_event.is_set():
            return
        self._dispatch_hook(Hooks.PRE_STOP.value)
        self._stop_event.set()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
        self._dispatch_hook(Hooks.POST_STOP.value)

    # ------------------------------------------------------------------
    # Диспетчеризация хуков плагинов
    # ------------------------------------------------------------------

    def _dispatch_hook(self, hook_name: str, **kwargs) -> None:
        if not self.plugin_manager:
            return
        try:
            self.plugin_manager.dispatch(hook_name, account=self.account, runner=self, **kwargs)
        except Exception:
            if not self._ignore_exceptions:
                raise

    def _dispatch_event_hook(self, event: "events.BaseEvent") -> None:
        hook = _EVENT_HOOK_MAP.get(event.type)
        if hook:
            self._dispatch_hook(hook.value, event=event)

    # ------------------------------------------------------------------
    # Проброс ошибок фоновых потоков
    # ------------------------------------------------------------------

    def _report_thread_error(self, exc: Exception, source: str) -> bool:
        """
        Обрабатывает исключение фонового потока.

        :return: `True`, если поток должен завершиться (ignore_exceptions=False — исключение
            уже отправлено в `listen()` через очередь событий), `False` — если ошибку нужно
            проглотить и продолжить работу.
        """
        if not self._ignore_exceptions:
            self._event_queue.put(exc)
            return True
        logger.warning("Ошибка в фоновом потоке (%s): %s", source, exc, exc_info=True)
        return False

    # ------------------------------------------------------------------
    # Дедупликация ItemPaidEvent и авто-выдача
    # ------------------------------------------------------------------

    def _delivery_ledger(self):
        """SQLite-журнал выдач (`AutoDeliveryManager.ledger`), если настроен."""
        if self.autodelivery_manager is None:
            return None
        return getattr(self.autodelivery_manager, "ledger", None)

    def _emit_item_paid(self, chat, message, deal) -> None:
        """
        Эмитит `ItemPaidEvent` не более одного раза на сделку.

        Дедупликация: in-memory set по `deal_id` (WS-маркер и поллинг могут заметить одну и ту же
        оплату) плюс SQLite-журнал (защита от повторной выдачи после перезапуска процесса).
        """
        deal_id = deal.id if deal and deal.id else None
        if deal_id:
            if deal_id in self._paid_deal_ids:
                return
            self._paid_deal_ids.add(deal_id)
            ledger = self._delivery_ledger()
            if ledger is not None:
                item_name = deal.item.name if deal.item else None
                if not ledger.try_mark_seen_paid(deal_id, item_name):
                    logger.debug("Оплата сделки %s уже есть в журнале выдач — событие пропущено", deal_id)
                    return
        self._event_queue.put(events.ItemPaidEvent(self, chat, message, deal))

    def _seed_paid_deal(self, deal) -> None:
        """
        Регистрирует уже оплаченную сделку из первого снимка поллинга как `seen_paid` — без события
        и без выдачи (оплата произошла до запуска `Runner`, выдавать товар задним числом опасно).
        """
        self._paid_deal_ids.add(deal.id)
        ledger = self._delivery_ledger()
        if ledger is not None:
            item_name = deal.item.name if deal.item else None
            ledger.try_mark_seen_paid(deal.id, item_name)

    def _warn_about_stuck_deliveries(self) -> None:
        """Логирует сделки, у которых выдача прервалась посередине в прошлом запуске (`reserved`)."""
        ledger = self._delivery_ledger()
        if ledger is None:
            return
        try:
            stuck = ledger.deals_in_state("reserved")
        except Exception:
            logger.warning("Не удалось прочитать журнал выдач при старте", exc_info=True)
            return
        for deal_id, item_name in stuck:
            logger.error(
                "Выдача по сделке %s (лот %r) прервалась посередине в прошлом запуске: товар был "
                "забран со склада, но отправка покупателю не подтверждена. Авто-повтор не "
                "выполняется — проверьте сделку и склад вручную.", deal_id, item_name,
            )

    def _handle_autodelivery(self, event: "events.BaseEvent") -> None:
        """
        Обрабатывает авто-выдачу товара по `ItemPaidEvent`.

        Использует безопасную транзакционную пару `AutoDeliveryManager.reserve()`/`restore()`:
        товар считается по-настоящему выданным только после успешной отправки сообщения покупателю.
        Если `send_message` упал с ошибкой — товар возвращается обратно на склад лота (`restore()`
        в `finally`-ветке), а не теряется. Прогресс выдачи фиксируется в SQLite-журнале
        (`reserved` → `sent`/`restored`), что защищает от двойной выдачи после перезапуска.
        """
        if not self.autodelivery_manager or not isinstance(event, events.ItemPaidEvent):
            return
        deal = event.deal
        item_name = deal.item.name if deal and deal.item else None
        chat_id = event.chat.id if event.chat else (deal.chat.id if deal and deal.chat else None)
        if not item_name or not chat_id:
            return

        # Авто-выдача уместна только для продаж: direction=IN — это наша собственная покупка.
        if deal is not None and deal.direction is not None and deal.direction != ItemDealDirections.OUT:
            logger.debug("Авто-выдача по сделке %s пропущена — сделка не является продажей (direction=%s)",
                         deal.id, deal.direction)
            return

        deal_id = deal.id if deal else None
        ledger = self._delivery_ledger()
        if ledger is not None and deal_id:
            state = ledger.get_state(deal_id)
            if state in ("reserved", "sent"):
                logger.info("Авто-выдача по сделке %s пропущена — она уже в состоянии %r в журнале",
                            deal_id, state)
                return

        self._dispatch_hook(Hooks.PRE_DELIVERY.value, item_name=item_name, deal=deal)

        item_value = None
        try:
            item_value = self.autodelivery_manager.reserve(item_name)
        except Exception:
            if not self._ignore_exceptions:
                raise
            logger.warning("Не удалось забрать товар со склада лота %r", item_name, exc_info=True)

        delivered = False
        if item_value is not None:
            if ledger is not None and deal_id:
                ledger.mark_reserved(deal_id, item_name)
            try:
                delivery_text = self.autodelivery_manager.format_delivery_text(item_value)
                self.account.send_message(chat_id, delivery_text)
                delivered = True
                if ledger is not None and deal_id:
                    ledger.mark_sent(deal_id)
                logger.info("Товар по лоту %r выдан покупателю в чат %s (сделка %s)",
                            item_name, chat_id, deal_id or "?")
            except Exception:
                # Значение товара в лог не пишем — это секрет (ключ/данные аккаунта).
                logger.warning("Не удалось отправить выданный товар покупателю в чат %s (лот %r) — "
                               "товар возвращён на склад", chat_id, item_name, exc_info=True)
                if not self._ignore_exceptions:
                    raise
            finally:
                if not delivered:
                    try:
                        self.autodelivery_manager.restore(item_name, item_value)
                        if ledger is not None and deal_id:
                            ledger.mark_restored(deal_id)
                    except Exception:
                        logger.error("Не удалось вернуть товар на склад лота %r после сбоя отправки",
                                     item_name, exc_info=True)

        self._dispatch_hook(Hooks.POST_DELIVERY.value, item_name=item_name, deal=deal, delivered=delivered)

    # ------------------------------------------------------------------
    # Периодический опрос (профиль/баланс + сделки + отзывы)
    # ------------------------------------------------------------------

    def _poll_loop(self, delay: float) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:
                if self._report_thread_error(exc, "поллинг"):
                    return
            self._stop_event.wait(delay)

    def _poll_once(self) -> None:
        try:
            self.account.get()
        except Exception as exc:
            # Ошибка обновления профиля не должна блокировать опрос сделок/отзывов.
            if not self._ignore_exceptions:
                raise
            logger.warning("Не удалось обновить профиль аккаунта при поллинге: %s", exc)
        self._poll_deals()
        self._poll_reviews()

    def _collect_all_pages(self, fetch_page, extract_items) -> list | None:
        """
        Собирает элементы со всех страниц курсорной пагинации (максимум `_MAX_POLL_PAGES` страниц,
        с защитой от неподвижного курсора).

        :param fetch_page: `fetch_page(after_cursor) -> список-страница | None`.
        :param extract_items: `extract_items(page) -> list` — извлекает элементы из страницы.
        :return: Все собранные элементы, либо `None`, если запрос упал (снимок трогать нельзя).
        """
        items: list = []
        cursor: str | None = None
        for _ in range(_MAX_POLL_PAGES):
            try:
                page = fetch_page(cursor)
            except Exception:
                if not self._ignore_exceptions:
                    raise
                logger.warning("Ошибка запроса при поллинге", exc_info=True)
                return None
            if page is None:
                break
            items.extend(extract_items(page) or [])
            page_info = getattr(page, "page_info", None)
            if not page_info or not page_info.has_next_page:
                break
            next_cursor = page_info.end_cursor
            if not next_cursor or next_cursor == cursor:
                logger.warning("Курсор пагинации не продвинулся — опрос страницы прерван")
                break
            cursor = next_cursor
        return items

    def _poll_deals(self) -> None:
        is_first_poll = not self._deals_initialized
        deals = self._collect_all_pages(
            lambda cursor: self.account.get_deals(count=50, after_cursor=cursor),
            lambda page: page.deals,
        )
        if deals is None:
            return

        for deal in deals:
            if not deal or not deal.id:
                continue
            new_raw = deal.raw_status.name if deal.raw_status else None
            new_has_problem = bool(deal.has_problem)

            if deal.id not in self._known_deals:
                self._known_deals[deal.id] = new_raw
                self._known_deal_problems[deal.id] = new_has_problem
                if is_first_poll:
                    # Снимок при старте: уже оплаченные сделки регистрируются в журнале как
                    # seen_paid без события — их оплата случилась до запуска Runner.
                    if new_raw == "PAID":
                        self._seed_paid_deal(deal)
                else:
                    self._event_queue.put(events.NewDealEvent(self, deal))
                    if new_raw == "PAID":
                        self._emit_item_paid(deal.chat, None, deal)
                continue

            old_raw = self._known_deals.get(deal.id)
            if old_raw != new_raw:
                self._known_deals[deal.id] = new_raw
                self._event_queue.put(events.DealStatusChangedEvent(self, deal, old_raw, new_raw))
                specific_cls = _SPECIFIC_STATUS_EVENTS.get(new_raw)
                if specific_cls:
                    self._event_queue.put(specific_cls(self, deal, old_raw, new_raw))
                # Переход уже известной сделки в PAID — тоже оплата (раньше замечались только
                # новые сделки, и оплата после PENDING терялась).
                if new_raw == "PAID":
                    self._emit_item_paid(deal.chat, None, deal)

            old_has_problem = self._known_deal_problems.get(deal.id, new_has_problem)
            if old_has_problem != new_has_problem:
                self._known_deal_problems[deal.id] = new_has_problem
                if new_has_problem:
                    self._event_queue.put(events.DealHasProblemEvent(self, deal))
                else:
                    self._event_queue.put(events.DealProblemResolvedEvent(self, deal))

        self._deals_initialized = True

    def _poll_reviews(self) -> None:
        """Сравнивает список своих отзывов со снимком с предыдущего опроса, порождая `NewReviewEvent`."""
        is_first_poll = not self._reviews_initialized
        reviews = self._collect_all_pages(
            lambda cursor: self.account.get_my_reviews(count=50, after_cursor=cursor),
            lambda page: page.reviews,
        )
        if reviews is None:
            return

        for review in reviews:
            if not review or not review.id or review.id in self._known_reviews:
                continue
            self._known_reviews.add(review.id)
            if not is_first_poll:
                self._event_queue.put(events.NewReviewEvent(self, review))

        self._reviews_initialized = True

    # ------------------------------------------------------------------
    # Автоподнятие лотов (по таймеру `autoraise_manager.raise_interval`)
    # ------------------------------------------------------------------

    def _autoraise_loop(self) -> None:
        manager = self.autoraise_manager
        # Не поднимаем лоты сразу при старте — ждём первый полный интервал, чтобы не мешать
        # только что вручную поднятым лотам и не спамить запросами сразу после запуска.
        if self._stop_event.wait(manager.raise_interval):
            return
        while not self._stop_event.is_set():
            try:
                self._run_autoraise_cycle()
            except Exception as exc:
                if self._report_thread_error(exc, "автоподнятие"):
                    return
            self._stop_event.wait(manager.raise_interval)

    def _run_autoraise_cycle(self) -> None:
        results = self.autoraise_manager.raise_all(self.account)
        for result in results:
            if result.raised:
                self._event_queue.put(events.ItemRaisedEvent(self, result))
            elif result.skipped_reason == "insufficient_balance":
                self._event_queue.put(events.InsufficientBalanceEvent(self, result))

    # ------------------------------------------------------------------
    # WebSocket (чаты, сообщения в реальном времени)
    # ------------------------------------------------------------------

    def _seed_known_chats(self) -> None:
        """Заполняет снимок текущих чатов до старта, чтобы не породить `ChatInitializedEvent` на них."""
        chats = self._collect_all_pages(
            lambda cursor: self.account.get_chats(count=50, after_cursor=cursor),
            lambda page: page.chats,
        )
        for chat in chats or []:
            if not chat or not chat.id:
                continue
            self._known_chats[chat.id] = chat.unread_messages_counter or 0
            if chat.last_message and chat.last_message.id:
                self._known_last_message_ids[chat.id] = chat.last_message.id

    def _ws_loop(self) -> None:
        reconnect_delay = 1.0
        while not self._stop_event.is_set():
            connected_at = time.monotonic()
            try:
                self._ws_connect_and_listen()
            except Exception as exc:
                if self._report_thread_error(exc, "WebSocket"):
                    return
            if self._stop_event.is_set():
                return
            # Экспоненциальный backoff переподключения; после стабильного соединения — сброс.
            if time.monotonic() - connected_at > 30:
                reconnect_delay = 1.0
            logger.debug("WS-переподключение через %.0f с", reconnect_delay)
            self._stop_event.wait(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60.0)

    def _ws_connect_and_listen(self) -> None:
        headers = [
            f"Cookie: {self.account._cookie_header()}",
            f"User-Agent: {self.account.user_agent}",
        ]
        ws = websocket.create_connection(
            _WS_URL,
            header=headers,
            origin=_WS_ORIGIN,
            subprotocols=[_WS_SUBPROTOCOL],
            timeout=10,
        )
        self._ws = ws
        try:
            # Рукопожатие graphql-transport-ws (payload снят с реального трафика playerok.com).
            timezone_offset = time.timezone // 60  # минуты, как отдаёт JS Date.getTimezoneOffset()
            ws.send(json.dumps({
                "type": "connection_init",
                "payload": {"x-gql-op": "ws-subscription", "x-gql-path": "/",
                            "x-timezone-offset": timezone_offset},
            }))
            if not self._ws_wait_for_ack(ws):
                raise ConnectionError("Сервер Playerok не подтвердил WS-соединение (нет connection_ack)")
            self._ws_subscribe(ws)
            logger.info("WS-подключение к %s установлено, подписки оформлены", _WS_URL)
            ws.settimeout(30)
            while not self._stop_event.is_set():
                try:
                    raw = ws.recv()
                except Exception:
                    break
                if not raw:
                    continue
                self._handle_ws_message(ws, raw)
        finally:
            try:
                ws.close()
            except Exception:
                pass
            if self._ws is ws:
                self._ws = None

    def _ws_wait_for_ack(self, ws) -> bool:
        """Ждёт кадр `connection_ack` после `connection_init` (отвечая на серверные `ping`)."""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                raw = ws.recv()
            except Exception:
                return False
            if not raw:
                continue
            try:
                message = json.loads(raw)
            except Exception:
                continue
            message_type = message.get("type")
            if message_type == "connection_ack":
                return True
            if message_type == "ping":
                ws.send(json.dumps({"type": "pong"}))
        return False

    def _ws_subscribe(self, ws) -> None:
        """Оформляет WS-подписки из `self.ws_subscriptions`."""
        for operation_name in self.ws_subscriptions:
            if operation_name not in QUERIES:
                logger.warning("WS-подписка %r отсутствует в QUERIES — пропуск", operation_name)
                continue
            variables = self._ws_subscription_variables(operation_name)
            ws.send(json.dumps({
                "id": str(uuid.uuid4()),
                "type": "subscribe",
                "payload": {
                    "variables": variables,
                    "extensions": {},
                    "operationName": operation_name,
                    "query": QUERIES[operation_name],
                },
            }))

    def _ws_subscription_variables(self, operation_name: str) -> dict:
        user_id = self.account.id
        if operation_name in ("chatUpdated", "chatMarkedAsRead"):
            return {"filter": {"userId": user_id}, "showForbiddenImage": True}
        if operation_name == "chatCreated":
            return {"filter": {"userId": user_id}}
        if operation_name in ("itemUpdated", "itemCreated"):
            return {"filter": {"userId": user_id}, "showForbiddenImage": True}
        if operation_name == "userUpdated":
            return {"userId": user_id}
        if operation_name == "chatMessageCreated":
            return {"filter": {"userId": user_id}, "showForbiddenImage": True}
        return {}

    def _handle_ws_message(self, ws, raw: str) -> None:
        try:
            message = json.loads(raw)
        except Exception:
            return
        message_type = message.get("type")
        if message_type == "ping":
            try:
                ws.send(json.dumps({"type": "pong"}))
            except Exception:
                pass
            return
        if message_type == "error":
            logger.warning("WS-подписка вернула ошибку: %s", message.get("payload"))
            return
        if message_type == "complete":
            logger.debug("WS-подписка %s завершена сервером", message.get("id"))
            return
        if message_type != "next":
            return
        payload = (message.get("payload") or {}).get("data") or {}
        if payload.get("chatUpdated"):
            self._handle_chat_updated(payload["chatUpdated"])
            return
        if payload.get("chatMarkedAsRead"):
            self._handle_chat_marked_as_read(payload["chatMarkedAsRead"])
            return
        if payload.get("chatCreated"):
            self._handle_chat_created(payload["chatCreated"])
            return
        if payload.get("itemUpdated"):
            self._event_queue.put(events.ItemUpdatedEvent(self, self.account._resolve_items(payload["itemUpdated"])))
            return
        if payload.get("itemCreated"):
            self._event_queue.put(events.ItemCreatedEvent(self, self.account._resolve_items(payload["itemCreated"])))
            return

    def _handle_chat_created(self, raw_chat: dict) -> None:
        chat_obj = parser.chat(raw_chat)
        if not chat_obj or not chat_obj.id:
            return
        self.account._note_chat(chat_obj)
        self._known_chats[chat_obj.id] = chat_obj.unread_messages_counter or 0
        self._event_queue.put(events.ChatCreatedEvent(self, chat_obj))
        # Также как инициализация нового чата — совместимость с существующими модулями.
        self._event_queue.put(events.ChatInitializedEvent(self, chat_obj))

    def _handle_chat_marked_as_read(self, raw_chat: dict) -> None:
        """Обновляет счётчик непрочитанных в снимке чатов (без порождения событий)."""
        chat_obj = parser.chat(raw_chat)
        if not chat_obj or not chat_obj.id:
            return
        self.account._note_chat(chat_obj)
        self._known_chats[chat_obj.id] = chat_obj.unread_messages_counter or 0

    def _handle_chat_updated(self, raw_chat: dict) -> None:
        chat_obj = parser.chat(raw_chat)
        if not chat_obj or not chat_obj.id:
            return
        self.account._note_chat(chat_obj)  # держим Account.mark_chat_as_read_if_needed() в курсе актуального счётчика
        is_new_chat = chat_obj.id not in self._known_chats
        self._known_chats[chat_obj.id] = chat_obj.unread_messages_counter or 0

        if is_new_chat:
            self._event_queue.put(events.ChatInitializedEvent(self, chat_obj))
            # Не выходим: last_message нового чата — как правило, и есть первое сообщение
            # (включая маркер оплаты), терять его нельзя.

        message = chat_obj.last_message
        if not message or not message.id:
            return
        # Детекция новых сообщений по смене id последнего сообщения (а не по росту счётчика
        # непрочитанных — он не растёт, например, для собственных исходящих сообщений).
        if self._known_last_message_ids.get(chat_obj.id) == message.id:
            return
        self._known_last_message_ids[chat_obj.id] = message.id

        author = message.user.username if message.user else None
        author_id = message.user.id if message.user else "?"
        logger.info("Новое сообщение в чате %s — от %r (id=%s): %s", chat_obj.id, author, author_id,
                    _truncate_for_log(message.text) or "<без текста>")
        self._event_queue.put(events.NewMessageEvent(self, chat_obj, message))
        if message.text and "{{ITEM_PAID}}" in message.text:
            self._emit_item_paid(chat_obj, message, message.deal)
