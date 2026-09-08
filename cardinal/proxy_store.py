"""
Хранение прокси, из которых Cardinal собирает две НЕЗАВИСИМЫЕ связки:
- прокси для Playerok (Account/REST + Runner/WebSocket);
- прокси для Telegram-сессии бота (aiogram).

Это осознанно разделено: один и тот же IP может быть отлично рабочим для
Telegram, но уже забаненным на Playerok антибот-защитой (DDoS-Guard) — и
наоборот. Поэтому у каждого сохранённого прокси — два независимых флага
активности (`active_playerok`, `active_telegram`) и два независимых
результата последней проверки: активным для каждой цели может быть только
один прокси одновременно (в рамках этой цели), но это может быть как один
и тот же прокси для обеих целей, так и два разных, так и вообще прокси
только под одну из целей.

Нумерация «по порядку» для CLI-флага --proxyN (позиция в списке, отсортированном
по `id`, считая с 1) — CLI-флаг задаёт прокси именно для Telegram-сессии
(разово, только на этот запуск): это единственный сценарий, ради которого он
создавался — оживить Telegram-панель, когда основной путь наружу (VPN/sing-box)
недоступен, при этом Playerok продолжает идти как настроено отдельно (обычно —
напрямую, домашним IP).
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(_BASE_DIR, "storage", "proxies.sqlite3")

_TARGETS = ("playerok", "telegram")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """
    Доращивает недостающие колонки до актуальной схемы, по одной, независимо друг от
    друга — а не одним блоком, завязанным на наличие конкретной старой колонки
    (`is_active`). Так переживает любую промежуточную версию таблицы: и совсем старую
    (единый `is_active`/`last_*`), и любую другую, где почему-либо не хватает части
    новых колонок. На новых БД (созданных уже с актуальной схемой) ничего не делает —
    `cols` будет пуст (таблицу только что создал `CREATE TABLE IF NOT EXISTS` выше).
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(proxies)")}
    if not cols:
        return  # свежесозданная таблица уже с актуальной схемой, мигрировать нечего

    needed = {
        "active_playerok": "INTEGER NOT NULL DEFAULT 0",
        "active_telegram": "INTEGER NOT NULL DEFAULT 0",
        "playerok_ok": "INTEGER",
        "playerok_ms": "INTEGER",
        "playerok_error": "TEXT",
        "telegram_ok": "INTEGER",
        "telegram_ms": "INTEGER",
        "telegram_error": "TEXT",
    }
    had_active_playerok = "active_playerok" in cols
    for col, decl in needed.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE proxies ADD COLUMN {col} {decl}")

    # Перенос данных из совсем старой (единый is_active/last_*) схемы — только один
    # раз, когда active_playerok реально только что добавили этим вызовом, и только
    # если было откуда переносить (была старая колонка is_active).
    if not had_active_playerok and "is_active" in cols:
        conn.execute(
            "UPDATE proxies SET active_playerok = is_active, "
            "playerok_ok = last_ok, playerok_ms = last_ms, playerok_error = last_error"
        )


def _get_conn(db_path: str = DB_FILE) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _conn = sqlite3.connect(db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        with _lock, _conn:
            _conn.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_type       TEXT    NOT NULL,
                    host             TEXT    NOT NULL,
                    port             INTEGER NOT NULL,
                    username         TEXT,
                    password         TEXT,
                    country_code     TEXT,
                    country_name     TEXT,
                    city             TEXT,
                    active_playerok  INTEGER NOT NULL DEFAULT 0,
                    active_telegram  INTEGER NOT NULL DEFAULT 0,
                    playerok_ok      INTEGER,
                    playerok_ms      INTEGER,
                    playerok_error   TEXT,
                    telegram_ok      INTEGER,
                    telegram_ms      INTEGER,
                    telegram_error   TEXT,
                    created_at       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            _migrate_schema(_conn)
    return _conn


def _check_target(target: str) -> None:
    if target not in _TARGETS:
        raise ValueError(f"Неизвестное назначение прокси: {target!r} (ожидается playerok/telegram)")


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


def get_active_proxy(target: str) -> dict | None:
    """Активный прокси для указанной цели ("playerok" или "telegram"), если есть."""
    _check_target(target)
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            f"SELECT * FROM proxies WHERE active_{target}=1 LIMIT 1"
        ).fetchone()
    return _row_to_dict(row)


def set_active(proxy_id: int, target: str, active: bool) -> None:
    """Включает/выключает прокси `proxy_id` для цели `target`, не трогая другую цель."""
    _check_target(target)
    conn = _get_conn()
    col = f"active_{target}"
    with _lock, conn:
        if active:
            conn.execute(f"UPDATE proxies SET {col}=0")
            conn.execute(f"UPDATE proxies SET {col}=1 WHERE id=?", (proxy_id,))
        else:
            conn.execute(f"UPDATE proxies SET {col}=0 WHERE id=?", (proxy_id,))


def update_check(proxy_id: int, target: str, res: dict) -> None:
    """Сохраняет результат проверки (`proxy_tools.check_proxy_playerok/telegram`) для цели."""
    _check_target(target)
    conn = _get_conn()
    with _lock, conn:
        conn.execute(
            f"""UPDATE proxies
                SET {target}_ok=?, {target}_ms=?, {target}_error=?,
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
