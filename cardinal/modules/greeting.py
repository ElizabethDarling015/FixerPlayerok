"""
Приветствие новых собеседников: первое сообщение от нового пользователя получает автоответ.

Чтобы не здороваться повторно (в том числе после перезапуска), поприветствованные чаты
хранятся в SQLite (`storage/greeting.sqlite3`). При самом первом запуске все существующие
чаты аккаунта помечаются как уже поприветствованные — иначе бот поздоровался бы со всеми
старыми клиентами при первом же их сообщении.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import sqlite3
import threading
import time
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes

from ..stats_store import ACTION_GREETING
from .base import BaseModule
from .humanize import sleep_before_reply

DB_FILE = os.path.join("storage", "greeting.sqlite3")


class GreetingModule(BaseModule):
    name = "greeting"

    def __init__(self, cardinal, db_path: str = DB_FILE):
        super().__init__(cardinal)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS greeted (chat_id TEXT PRIMARY KEY, greeted_at REAL NOT NULL)"
            )

    # ------------------------------------------------------------------
    # Хранилище
    # ------------------------------------------------------------------

    def is_greeted(self, chat_id: str) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM greeted WHERE chat_id = ?", (chat_id,)).fetchone()
        return row is not None

    def mark_greeted(self, chat_id: str) -> bool:
        """Атомарно помечает чат поприветствованным. `False`, если он уже был помечен."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO greeted (chat_id, greeted_at) VALUES (?, ?)",
                (chat_id, time.time()),
            )
        return cursor.rowcount > 0

    def _db_is_empty(self) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM greeted LIMIT 1").fetchone()
        return row is None

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------

    async def on_start(self) -> None:
        # Первый запуск (пустая база): существующие чаты — не «новые покупатели».
        if not self._db_is_empty():
            return
        seeded = await asyncio.to_thread(self._seed_existing_chats)
        if seeded:
            logger.info("Приветствие: {} существующих чатов помечены как уже поприветствованные", seeded)

    #: Предохранитель от бесконечной пагинации: 400 страниц × 50 = 20 000 чатов.
    SEED_MAX_PAGES = 400

    def _seed_existing_chats(self) -> int:
        account = self.cardinal.account
        seeded = 0
        after_cursor = None
        for page_number in range(1, self.SEED_MAX_PAGES + 1):
            try:
                page = account.get_chats(count=50, after_cursor=after_cursor)
            except Exception:
                logger.exception("Приветствие: не удалось получить список чатов для первичной разметки")
                break
            if not page:
                break
            for chat in page.chats:
                if self.mark_greeted(chat.id):
                    seeded += 1
            if not page.page_info or not page.page_info.has_next_page:
                break
            if page_number == self.SEED_MAX_PAGES:
                # Чатов больше лимита: часть старых не размечена — бот может
                # поздороваться со старым клиентом как с новым.
                logger.warning("Приветствие: разметка остановлена на {} чатах (лимит {} страниц) — "
                               "старые чаты за пределами лимита не помечены", seeded, self.SEED_MAX_PAGES)
                break
            next_cursor = page.page_info.end_cursor
            if not next_cursor or next_cursor == after_cursor:
                break
            after_cursor = next_cursor
        return seeded

    def format_greeting(self, username: str, chat_id: str) -> str:
        return Template(self.cardinal.settings.greeting.text).safe_substitute(
            username=username, chat_id=chat_id,
        )

    async def on_event(self, event) -> None:
        if not self.enabled or event.type is not EventTypes.NEW_MESSAGE:
            return
        message = event.message
        account = self.cardinal.account
        if message is None or message.user is None or message.user.id == account.id:
            return
        if self.cardinal.is_blacklisted(message.user.username):
            return  # покупатель в чёрном списке — не приветствуем
        if not self.mark_greeted(event.chat.id):
            return  # уже здоровались (или чат размечен при первом запуске)

        username = message.user.username or "?"
        logger.info("Приветствуем нового собеседника {} (чат {})", username, event.chat.id)
        greeting_text = self.format_greeting(username, event.chat.id)
        # «Человеческая» пауза перед приветствием — мгновенный ответ выдаёт автоматизацию.
        await sleep_before_reply(getattr(self.cardinal.settings, "humanize", None), greeting_text)
        await asyncio.to_thread(account.send_message, event.chat.id, greeting_text)
        stats = getattr(self.cardinal, "stats", None)
        if stats is not None:
            with contextlib.suppress(Exception):
                stats.record(ACTION_GREETING)

    async def on_stop(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
