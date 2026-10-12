"""Витрина продавца: свои лоты на Playerok (то же, что страница «Мои товары» на сайте).

* активные — статусы APPROVED / PENDING_MODERATION / PENDING_APPROVAL (вкладка «Активные»);
* снятые и заблокированные — DISCONTINUED / BLOCKED / DECLINED / EXPIRED (из вкладки
  «Неактивные»; проданные копии и черновики не нужны — проданное есть в «Последних сделках»).

Список лотов Playerok отдаёт страницами; здесь он собирается целиком (с ограничением
на число страниц) и держится в памяти несколько минут.
"""
from __future__ import annotations

import time

from playerokapi.common.enums import ItemStatuses

ACTIVE_STATUSES = [ItemStatuses.APPROVED, ItemStatuses.PENDING_MODERATION, ItemStatuses.PENDING_APPROVAL]
INACTIVE_STATUSES = [ItemStatuses.DISCONTINUED, ItemStatuses.BLOCKED, ItemStatuses.DECLINED,
                     ItemStatuses.EXPIRED]

PAGE_SIZE = 24
MAX_PAGES = 15
CACHE_TTL = 180

STATUS_EMOJI = {
    "APPROVED": "🟢",
    "PENDING_MODERATION": "🔵",
    "PENDING_APPROVAL": "🟡",
    "EXPIRED": "🟠",
    "DECLINED": "🔴",
    "BLOCKED": "⛔",
    "DISCONTINUED": "⏸",
    "SOLD": "⚫",
    "DRAFT": "⚪",
}


def status_name(item) -> str | None:
    status = getattr(item, "status", None)
    return getattr(status, "name", None) or (str(status) if status else None)


def section_of(item) -> str:
    """«Игра → Категория» (как в уведомлениях и «Последних сделках»)."""
    game = getattr(getattr(item, "game", None), "name", None)
    category = getattr(getattr(item, "category", None), "name", None)
    if game and category:
        return f"{game} → {category}"
    return game or category or "?"


def fetch_items(account, statuses) -> list:
    """Все свои лоты с указанными статусами (блокирующий — звать в потоке)."""
    items: list = []
    cursor = None
    for _ in range(MAX_PAGES):
        page = account.get_my_items(statuses, PAGE_SIZE, cursor)
        items.extend(page.items if page and page.items else [])
        info = getattr(page, "page_info", None) if page else None
        next_cursor = getattr(info, "end_cursor", None) if info else None
        if not info or not getattr(info, "has_next_page", False) or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return items


def group_by_section(items) -> list[tuple[str, list]]:
    """[(раздел, лоты)] — разделы по алфавиту, лоты внутри — по названию."""
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(section_of(item), []).append(item)
    return [(name, sorted(groups[name], key=lambda it: (getattr(it, "name", None) or "").lower()))
            for name in sorted(groups, key=str.lower)]


class ItemsCache:
    """Активные лоты в памяти на `ttl` секунд (кнопка «Обновить» сбрасывает)."""

    def __init__(self, ttl: float = CACHE_TTL, clock=time.monotonic):
        self.ttl = ttl
        self._clock = clock
        self._loaded_at: float | None = None
        self._items: list = []

    def get(self, account) -> list:
        if self._loaded_at is None or self._clock() - self._loaded_at >= self.ttl:
            self._items = fetch_items(account, ACTIVE_STATUSES)
            self._loaded_at = self._clock()
        return self._items

    def peek(self) -> list:
        return self._items

    def invalidate(self) -> None:
        self._loaded_at = None


def find_on_sale(account, name: str | None):
    """Лот с таким названием на витрине (свежий запрос, без кэша) или None."""
    if not name:
        return None
    wanted = name.strip().lower()
    for item in fetch_items(account, ACTIVE_STATUSES):
        if (getattr(item, "name", None) or "").strip().lower() == wanted:
            return item
    return None
