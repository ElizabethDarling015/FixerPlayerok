"""
`DeliveryLedger` — долговечный SQLite-журнал авто-выдачи (stdlib `sqlite3`, без внешних зависимостей).

Хранит по одной записи на сделку (`deal_id`) с текущим состоянием выдачи:

- `seen_paid` — событие оплаты замечено (событие `ItemPaidEvent` уже эмитилось или сделка была
  оплачена ещё до первого запуска — "seed", выдача по ней не выполняется);
- `reserved` — товар забран со склада, но отправка покупателю ещё не подтверждена;
- `sent` — товар успешно отправлен покупателю (выдача завершена);
- `restored` — отправка не удалась, товар возвращён на склад.

Журнал решает две задачи:

1. **Дедупликация `ItemPaidEvent`** между источниками (WS-маркер и поллинг сделок) и между
   перезапусками процесса — одна сделка порождает не более одной выдачи.
2. **Восстановление после сбоя**: сделки, оставшиеся в состоянии `reserved` (процесс упал между
   забором товара и отправкой сообщения), при старте логируются как требующие ручной проверки —
   без автоматического повтора, чтобы не выдать товар дважды.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time

logger = logging.getLogger("playerokapi.delivery_ledger")

#: Допустимые состояния записи журнала.
STATES = ("seen_paid", "reserved", "sent", "restored")


class DeliveryLedger:
    """
    SQLite-журнал авто-выдачи по `deal_id`.

    Потокобезопасен: соединение открывается с `check_same_thread=False`, все операции
    сериализуются внутренним lock'ом (Runner работает из нескольких потоков).

    :param path: Путь к файлу базы SQLite (создаётся при первом обращении).
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deliveries (
                    deal_id    TEXT PRIMARY KEY,
                    state      TEXT NOT NULL,
                    item_name  TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )

    def get_state(self, deal_id: str) -> str | None:
        """Возвращает текущее состояние сделки в журнале (`None`, если записи нет)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT state FROM deliveries WHERE deal_id = ?", (deal_id,)
            ).fetchone()
        return row[0] if row else None

    def try_mark_seen_paid(self, deal_id: str, item_name: str | None = None) -> bool:
        """
        Атомарно записывает сделку как `seen_paid`, если о ней ещё нет записи.

        :return: `True`, если запись создана впервые (событие оплаты новое), `False`, если
            сделка уже есть в журнале в любом состоянии (дубль — событие эмитить не нужно).
        """
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO deliveries (deal_id, state, item_name, updated_at) VALUES (?, ?, ?, ?)",
                (deal_id, "seen_paid", item_name, time.time()),
            )
        return cursor.rowcount > 0

    def mark_reserved(self, deal_id: str, item_name: str | None = None) -> None:
        """Помечает сделку как `reserved` — товар забран со склада, отправка ещё не подтверждена."""
        self._set_state(deal_id, "reserved", item_name)

    def mark_sent(self, deal_id: str) -> None:
        """Помечает сделку как `sent` — товар успешно отправлен покупателю."""
        self._set_state(deal_id, "sent")

    def mark_restored(self, deal_id: str) -> None:
        """Помечает сделку как `restored` — отправка не удалась, товар возвращён на склад."""
        self._set_state(deal_id, "restored")

    def deals_in_state(self, state: str) -> list[tuple[str, str | None]]:
        """
        Возвращает все сделки в указанном состоянии.

        :param state: Одно из состояний `STATES`.
        :return: Список пар `(deal_id, item_name)`.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT deal_id, item_name FROM deliveries WHERE state = ? ORDER BY updated_at",
                (state,),
            ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def _set_state(self, deal_id: str, state: str, item_name: str | None = None) -> None:
        if state not in STATES:
            raise ValueError(f"Неизвестное состояние журнала выдач: {state!r}")
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO deliveries (deal_id, state, item_name, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(deal_id) DO UPDATE SET
                    state = excluded.state,
                    item_name = COALESCE(excluded.item_name, deliveries.item_name),
                    updated_at = excluded.updated_at
                """,
                (deal_id, state, item_name, time.time()),
            )

    def close(self) -> None:
        """Закрывает соединение с базой (журнал больше использовать нельзя)."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
