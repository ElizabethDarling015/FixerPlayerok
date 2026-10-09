"""Небольшой кэш ответов Playerok для уведомлений.

Зачем: на одно входящее сообщение уведомления раньше делали цепочку запросов
(чат → лот → каждая сделка чата), а на новую сделку — до шести `get_deal` с повторами.
Лишние запросы — лишний повод для антибот-защиты Playerok.

Как устроен:

* хранится только в памяти процесса — после перезапуска/падения/обновления просто пуст,
  на диске портиться нечему;
* у каждой записи срок жизни (``ttl``), по истечении — запрос заново;
* размер ограничен (``maxsize``), самые старые записи вытесняются;
* ``None`` и ошибки не кэшируются — неудачный запрос повторится при следующем событии.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Callable


class TTLCache:
    """Словарь с временем жизни записей и ограничением размера (LRU)."""

    def __init__(self, ttl: float, maxsize: int = 500, clock: Callable[[], float] = time.monotonic):
        self.ttl = ttl
        self.maxsize = maxsize
        self._clock = clock
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()

    def get(self, key: Any) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: Any, value: Any) -> None:
        if value is None:
            return
        self._data[key] = (self._clock() + self.ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def invalidate(self, key: Any) -> None:
        self._data.pop(key, None)

    def __len__(self) -> int:
        return len(self._data)
