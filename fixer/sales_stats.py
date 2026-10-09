"""Статистика продаж — прямо из истории транзакций Playerok.

Раньше продажи считались ботом самостоятельно: каждое замеченное событие «оплачено» —
+1 в локальную базу. Поэтому статистика теряла всё, что произошло, пока бот был выключен,
пропускала сделки, которые сайт сам успевал перевести в «отправлено», и считала возвраты
как продажи.

Теперь источник — транзакции продажи (`operation = SELL`) на Playerok, те же, что видны
в кошельке на сайте. По каждой есть:

* дата создания;
* `value` — сколько получает продавец, `fee` — комиссия Playerok (вместе — цена лота);
* статус: ``PENDING``/``PROCESSING`` — деньги заморожены, ``CONFIRMED`` — зачислены,
  ``ROLLED_BACK`` — возврат покупателю.
"""
from __future__ import annotations

import datetime
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

#: Сколько транзакций запрашивать за раз и сколько страниц максимум (защита от зацикливания).
PAGE_SIZE = 24
MAX_PAGES = 30
#: Сколько секунд держать загруженную историю (повторное нажатие — без запросов).
CACHE_TTL = 300


@dataclass
class Sale:
    day: datetime.date
    gross: float
    """Цена лота (то, что заплатил покупатель)."""
    net: float
    """Сколько получает продавец после комиссии."""
    refunded: bool
    frozen: bool
    """Деньги ещё заморожены (не зачислены на баланс)."""


@dataclass
class DayTotals:
    count: int = 0
    gross: float = 0.0
    net: float = 0.0
    refunds: int = 0


def seller_tz(settings) -> datetime.tzinfo | None:
    """Часовой пояс продавца из `[digest] timezone` (иначе — пояс сервера)."""
    name = getattr(getattr(settings, "digest", None), "timezone", None)
    return ZoneInfo(name) if name else None


def _parse_dt(iso: str | None) -> datetime.datetime | None:
    if not iso:
        return None
    try:
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.datetime.fromisoformat(iso)
    except ValueError:
        return None


def sale_from_transaction(tx, tz) -> Sale | None:
    created = _parse_dt(getattr(tx, "created_at", None))
    if created is None:
        return None
    value = float(getattr(tx, "value", 0) or 0)
    fee = float(getattr(tx, "fee", 0) or 0)
    status = getattr(getattr(tx, "status", None), "name", None) or str(getattr(tx, "status", "") or "")
    return Sale(
        day=created.astimezone(tz).date(),
        gross=value + fee,
        net=value,
        refunded=status == "ROLLED_BACK",
        frozen=status in ("PENDING", "PROCESSING"),
    )


def fetch_sales(account, since: datetime.date, tz) -> list[Sale]:
    """Продажи с даты `since` (включительно), от новых к старым. Блокирующий — звать в потоке."""
    sales: list[Sale] = []
    cursor = None
    for _ in range(MAX_PAGES):
        page = account.get_transactions(PAGE_SIZE, cursor, {"operation": ["SELL"]})
        txs = list(page.transactions) if page and page.transactions else []
        reached_older = False
        for tx in txs:
            sale = sale_from_transaction(tx, tz)
            if sale is None:
                continue
            if sale.day < since:
                reached_older = True
                continue
            sales.append(sale)
        info = getattr(page, "page_info", None) if page else None
        next_cursor = getattr(info, "end_cursor", None) if info else None
        if reached_older or not txs or not getattr(info, "has_next_page", False) or not next_cursor \
                or next_cursor == cursor:
            break
        cursor = next_cursor
    return sales


def totals_by_day(sales: list[Sale]) -> dict[datetime.date, DayTotals]:
    days: dict[datetime.date, DayTotals] = {}
    for sale in sales:
        t = days.setdefault(sale.day, DayTotals())
        if sale.refunded:
            t.refunds += 1
            continue
        t.count += 1
        t.gross += sale.gross
        t.net += sale.net
    return days


def sum_totals(days: dict[datetime.date, DayTotals], since: datetime.date) -> DayTotals:
    total = DayTotals()
    for day, t in days.items():
        if day >= since:
            total.count += t.count
            total.gross += t.gross
            total.net += t.net
            total.refunds += t.refunds
    return total


class SalesHistory:
    """Загрузка истории продаж с кэшем на несколько минут."""

    def __init__(self, ttl: float = CACHE_TTL, clock=time.monotonic):
        self.ttl = ttl
        self._clock = clock
        self._cached: tuple[float, datetime.date, list[Sale]] | None = None

    def get(self, account, since: datetime.date, tz) -> list[Sale]:
        if self._cached is not None:
            loaded_at, cached_since, sales = self._cached
            if self._clock() - loaded_at < self.ttl and cached_since <= since:
                return [s for s in sales if s.day >= since]
        sales = fetch_sales(account, since, tz)
        self._cached = (self._clock(), since, sales)
        return sales


def fmt_rub(value: float) -> str:
    """1234.5 → «1 234.5 ₽», 330 → «330 ₽»."""
    text = f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{text} ₽"
