"""
Счётчики «что бот сделал сам» — SQLite-хранилище (`storage/stats.sqlite`).

Учитывает автоматические действия бота по дням: выдачи товаров, поднятия лотов,
автоответы и приветствия. Записи переживают перезапуски; раздел «Статистика»
TG-панели показывает суммы за сегодня / 7 дней / всё время.

Действия именуются модульными константами `ACTION_*` — их же используют ядро
(`Cardinal._record_bot_action`) и модули при записи.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
import threading

DB_FILE = os.path.join("storage", "stats.sqlite")

#: Товар выдан авто-выдачей (журнал выдач подтвердил отправку).
ACTION_DELIVERY = "delivery"
#: Лот поднят автоподнятием.
ACTION_RAISE = "raise"
#: Ответ автоответчика.
ACTION_AUTORESPONSE = "autoresponse"
#: Приветствие нового покупателя.
ACTION_GREETING = "greeting"


class StatsStore:
    """Потокобезопасный учёт действий бота: `+1` к счётчику `(день, действие)`."""

    def __init__(self, db_path: str = DB_FILE):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS bot_actions ("
                "day TEXT NOT NULL, action TEXT NOT NULL, count INTEGER NOT NULL, "
                "PRIMARY KEY (day, action))"
            )

    @staticmethod
    def _today() -> str:
        return datetime.date.today().isoformat()

    def record(self, action: str, day: str | None = None) -> None:
        """Учитывает одно действие бота (`day` — ISO-день, по умолчанию сегодня)."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO bot_actions (day, action, count) VALUES (?, ?, 1) "
                "ON CONFLICT(day, action) DO UPDATE SET count = count + 1",
                (day or self._today(), action),
            )

    def totals(self, action: str) -> int:
        """Сколько раз действие выполнено за всё время."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM bot_actions WHERE action = ?",
                (action,),
            ).fetchone()
        return int(row[0])

    def for_period(self, action: str, days: int) -> int:
        """Сколько раз действие выполнено за последние `days` дней (включая сегодня)."""
        since = (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM bot_actions WHERE action = ? AND day >= ?",
                (action, since),
            ).fetchone()
        return int(row[0])

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
