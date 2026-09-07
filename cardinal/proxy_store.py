"""
Хранение прокси, через которые Cardinal подключается к Playerok (REST + WebSocket).

Один бот = одна активная связка (в отличие от Shinoa, где прокси привязан к
пользователю Telegram — тут прокси общий для всего аккаунта Playerok, поэтому
`user_id` не нужен). Активным может быть только один прокси одновременно —
как только активируется новый, предыдущий автоматически снимается.

Нумерация «по порядку» для CLI-флагов --proxy1/--proxy2/... — это позиция в
списке, отсортированном по `id` (по возрастанию, т.е. по порядку добавления),
считая с 1. Она НЕ совпадает со значением `id` в БД, если прокси удалялись.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(_BASE_DIR, "storage", "proxies.sqlite3")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _get_conn(db_path: str = DB_FILE) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _conn = sqlite3.connect(db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        with _lock, _conn:
            _conn.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_type   TEXT    NOT NULL,
                    host         TEXT    NOT NULL,
                    port         INTEGER NOT NULL,
                    username     TEXT,
                    password     TEXT,
                    country_code TEXT,
                    country_name TEXT,
                    city         TEXT,
                    is_active    INTEGER NOT NULL DEFAULT 0,
                    last_ok      INTEGER,
                    last_ms      INTEGER,
                    last_error   TEXT,
                    activated_at TEXT,
                    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
    return _conn


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def add_or_update_proxy(proxy_type: str, host: str, port: int,
                         username: str | None = None, password: str | None = None) -> dict:
    """Добавляет прокси или обновляет пароль, если такой (type+host+port+username) уже есть."""
    conn = _get_conn()
    with _lock, conn:
        row = conn.execute(
            """SELECT id FROM proxies
               WHERE proxy_type=? AND host=? AND port=? AND username IS ?""",
            (proxy_type, host, port, username),
        ).fetchone()
        if row:
            proxy_id = row["id"]
            conn.execute("UPDATE proxies SET password=? WHERE id=?", (password, proxy_id))
        else:
            cur = conn.execute(
                """INSERT INTO proxies (proxy_type, host, port, username, password)
                   VALUES (?, ?, ?, ?, ?)""",
                (proxy_type, host, port, username, password),
            )
            proxy_id = cur.lastrowid
    return get_proxy(proxy_id)


def get_proxy(proxy_id: int) -> dict | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM proxies WHERE id=?", (proxy_id,)).fetchone()
    return _row_to_dict(row)


def list_proxies() -> list[dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM proxies ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_by_ordinal(n: int) -> dict | None:
    """N-й прокси по порядку добавления, считая с 1 (для --proxy1/--proxy2/...)."""
    if n < 1:
        return None
    proxies = list_proxies()
    if n > len(proxies):
        return None
    return proxies[n - 1]


def get_active_proxy() -> dict | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM proxies WHERE is_active=1 LIMIT 1").fetchone()
    return _row_to_dict(row)


def set_active(proxy_id: int, active: bool) -> None:
    conn = _get_conn()
    with _lock, conn:
        if active:
            conn.execute("UPDATE proxies SET is_active=0")
            conn.execute(
                "UPDATE proxies SET is_active=1, activated_at=? WHERE id=?",
                (datetime.now().isoformat(), proxy_id),
            )
        else:
            conn.execute("UPDATE proxies SET is_active=0 WHERE id=?", (proxy_id,))


def update_check(proxy_id: int, res: dict) -> None:
    conn = _get_conn()
    with _lock, conn:
        conn.execute(
            """UPDATE proxies
               SET last_ok=?, last_ms=?, last_error=?,
                   country_code=COALESCE(?, country_code),
                   country_name=COALESCE(?, country_name),
                   city=COALESCE(?, city)
               WHERE id=?""",
            (
                1 if res.get("ok") else 0,
                res.get("ms"),
                res.get("error"),
                res.get("country_code"),
                res.get("country_name"),
                res.get("city"),
                proxy_id,
            ),
        )


def remove_proxy(proxy_id: int) -> bool:
    conn = _get_conn()
    with _lock, conn:
        cur = conn.execute("DELETE FROM proxies WHERE id=?", (proxy_id,))
    return cur.rowcount > 0
