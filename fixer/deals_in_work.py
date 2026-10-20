"""«⏳ Сделки в работе»: продажи, которые ещё требуют вашего внимания.

В раздел попадают:

* оплаченные сделки (`PAID`), по которым вы ещё не нажали «Подтвердить выдачу»;
* сделки с открытым спором (`hasProblem`), пока они не завершены и не возвращены —
  в том числе спор, открытый уже после подтверждения выдачи.

Сделка уходит из раздела, когда выдача подтверждена (и спора нет), спор закрыт после
подтверждения, сделка завершена, возвращена или отменена.

Порядок — порядок появления в разделе: новая оплата и новый спор (по сделке, которой в разделе
не было) встают в конец списка; сделка, которая уже была в разделе и получила спор, остаётся
на своём месте. Порядок хранится в `storage/deals_in_work.json`, чтобы не путаться после
перезапуска.

Число в кнопке главного меню держится в памяти:

* при подключении к Playerok бот один раз собирает такие сделки (тот же список, что
  «Мои продажи» на сайте);
* дальше число меняется по событиям Runner (оплата, подтверждение, спор, возврат…) и по
  нажатию «Подтвердить выдачу» в боте;
* раз в 10 минут бот тихо сверяется с Playerok — на случай потерянного события.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from contextlib import suppress

from loguru import logger

from playerokapi.common.enums import EventTypes, ItemDealDirections

from .settings import STORAGE_DIR

ORDER_FILE = os.path.join(STORAGE_DIR, "deals_in_work.json")
#: Сверка с Playerok, секунд.
RESYNC_INTERVAL = 600
#: Сделок на страницу и предел страниц при сверке (как у опроса сделок в Runner).
PAGE_SIZE = 50
MAX_PAGES = 20

#: Сделка закончена — в разделе ей не место, даже со спором.
FINAL_STATUSES = frozenset({"CONFIRMED", "CONFIRMED_AUTOMATICALLY", "ROLLED_BACK"})

#: События, в которых есть сделка и которые могут поменять раздел.
_DEAL_EVENTS = frozenset({
    EventTypes.NEW_DEAL, EventTypes.ITEM_PAID, EventTypes.ITEM_SENT,
    EventTypes.DEAL_STATUS_CHANGED, EventTypes.DEAL_CONFIRMED,
    EventTypes.DEAL_CONFIRMED_AUTOMATICALLY, EventTypes.DEAL_ROLLED_BACK,
    EventTypes.DEAL_HAS_PROBLEM, EventTypes.DEAL_PROBLEM_RESOLVED,
})


def raw_status(deal) -> str | None:
    return getattr(getattr(deal, "raw_status", None), "name", None)


def is_in_work(raw: str | None, has_problem: bool) -> bool:
    """Нужна ли сделке ваша реакция: не подтверждена выдача или открыт спор."""
    if raw in FINAL_STATUSES:
        return False
    return raw == "PAID" or bool(has_problem)


def _is_sale(deal) -> bool:
    direction = getattr(deal, "direction", None)
    return direction is None or direction == ItemDealDirections.OUT


class DealsInWork:
    """Список «сделок в работе» в памяти (id → последняя известная сделка) в порядке появления."""

    def __init__(self, order_file: str | None = ORDER_FILE):
        self._order_file = order_file
        self._deals: dict[str, object] = {}
        #: Состояние сделки, которое мы знаем лучше Playerok (сразу после нажатия он ещё
        #: несколько секунд отдаёт старый статус): id → raw-статус.
        self._local_status: dict[str, str] = {}
        self._lock = threading.Lock()
        self.synced = False
        self._saved_order = self._load_order()

    # ------------------------------------------------------------------
    # Чтение
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self._deals)

    def deals(self) -> list:
        with self._lock:
            return list(self._deals.values())

    def get(self, deal_id: str):
        return self._deals.get(deal_id)

    def is_sent(self, deal_id: str) -> bool:
        """Выдача по сделке уже подтверждена (сделка в разделе только из-за спора)."""
        deal = self._deals.get(deal_id)
        raw = self._local_status.get(deal_id) or raw_status(deal)
        return raw is not None and raw != "PAID"

    def has_problem(self, deal_id: str) -> bool:
        return bool(getattr(self._deals.get(deal_id), "has_problem", False))

    # ------------------------------------------------------------------
    # Изменения
    # ------------------------------------------------------------------

    def observe(self, deal, *, paid_hint: bool = False) -> None:
        """Учитывает свежие данные сделки: добавляет в конец, обновляет или убирает."""
        deal_id = getattr(deal, "id", None)
        if not deal_id or not _is_sale(deal):
            return
        raw = raw_status(deal)
        if raw is None and paid_hint:
            raw = "PAID"
        if raw is None:
            return
        local = self._local_status.get(deal_id)
        if local is not None:
            if raw == "PAID":
                raw = local  # Playerok ещё не видит наше подтверждение
            else:
                self._local_status.pop(deal_id, None)
        problem = bool(getattr(deal, "has_problem", False))
        with self._lock:
            if is_in_work(raw, problem):
                if deal_id not in self._deals:
                    logger.info("[в работе] + сделка {} ({}{})", deal_id, raw, ", спор" if problem else "")
                self._deals[deal_id] = deal
            elif self._deals.pop(deal_id, None) is not None:
                logger.info("[в работе] − сделка {} ({})", deal_id, raw)
            else:
                return
        self._save_order()

    def mark_sent(self, deal_id: str) -> None:
        """Вы подтвердили выдачу из бота: сделка уходит, если по ней нет спора."""
        self._local_status[deal_id] = "SENT"
        with self._lock:
            deal = self._deals.get(deal_id)
            if deal is None:
                return
            if getattr(deal, "has_problem", False):
                return
            self._deals.pop(deal_id, None)
        logger.info("[в работе] − сделка {} (выдача подтверждена в боте)", deal_id)
        self._save_order()

    def on_event(self, event) -> None:
        """Событие Runner → обновление раздела (быстро, без запросов к Playerok)."""
        event_type = getattr(event, "type", None)
        if event_type not in _DEAL_EVENTS:
            return
        deal = getattr(event, "deal", None)
        if deal is None:
            return
        self.observe(deal, paid_hint=event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID))

    def replace_all(self, fresh: list) -> None:
        """Итог сверки: `fresh` — все продажи с Playerok (сначала новые, как отдаёт сайт)."""
        candidates: dict[str, object] = {}
        for deal in reversed(fresh):  # старые — раньше, новые — в конец
            deal_id = getattr(deal, "id", None)
            if not deal_id or not _is_sale(deal):
                continue
            raw = raw_status(deal)
            local = self._local_status.get(deal_id)
            if local is not None:
                if raw == "PAID":
                    raw = local
                else:
                    self._local_status.pop(deal_id, None)
            if is_in_work(raw, bool(getattr(deal, "has_problem", False))):
                candidates[deal_id] = deal
        with self._lock:
            if self.synced:
                known = list(self._deals)
            else:
                # Первая сверка: порядок с прошлого запуска, остальное — следом.
                known = [deal_id for deal_id in self._saved_order if deal_id in candidates]
            ordered: dict[str, object] = {}
            for deal_id in known:
                if deal_id in candidates:
                    ordered[deal_id] = candidates[deal_id]
            for deal_id, deal in candidates.items():
                ordered.setdefault(deal_id, deal)
            changed = list(ordered) != list(self._deals)
            self._deals = ordered
            self.synced = True
        if changed:
            logger.info("[в работе] сверка с Playerok: {} сделок", len(ordered))
        self._save_order()

    # ------------------------------------------------------------------
    # Сверка с Playerok
    # ------------------------------------------------------------------

    def fetch_sales(self, account) -> list | None:
        """Все свои продажи (до `MAX_PAGES` страниц), `None` — если запрос не прошёл."""
        sales: list = []
        cursor = None
        for _ in range(MAX_PAGES):
            page = account.get_deals(count=PAGE_SIZE, after_cursor=cursor,
                                     direction=ItemDealDirections.OUT)
            if page is None:
                break
            sales.extend(deal for deal in (page.deals or []) if deal)
            info = getattr(page, "page_info", None)
            next_cursor = getattr(info, "end_cursor", None)
            if not getattr(info, "has_next_page", False) or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return sales

    async def resync(self, fixer) -> bool:
        account = getattr(fixer, "account", None)
        if account is None or not getattr(fixer, "playerok_connected", False):
            return False
        try:
            sales = await asyncio.to_thread(self.fetch_sales, account)
        except Exception as exc:
            logger.warning("[в работе] Сверка с Playerok не удалась: {}", exc)
            return False
        if sales is None:
            return False
        self.replace_all(sales)
        return True

    async def run(self, fixer) -> None:
        """Фоновая задача: сверка сразу после подключения и затем раз в `RESYNC_INTERVAL`."""
        while True:
            await self.resync(fixer)
            await asyncio.sleep(RESYNC_INTERVAL)

    # ------------------------------------------------------------------
    # Порядок между перезапусками
    # ------------------------------------------------------------------

    def _load_order(self) -> list[str]:
        if not self._order_file:
            return []
        with suppress(Exception):
            if os.path.isfile(self._order_file):
                with open(self._order_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return [str(x) for x in data]
        return []

    def _save_order(self) -> None:
        if not self._order_file:
            return
        with self._lock:
            order = list(self._deals)
        with suppress(Exception):
            os.makedirs(os.path.dirname(self._order_file) or ".", exist_ok=True)
            with open(self._order_file, "w", encoding="utf-8") as f:
                json.dump(order, f)
