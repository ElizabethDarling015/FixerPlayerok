"""
Ежедневная сводка: учёт продаж + отчёт админам в Telegram раз в день.

Продажи (событие «лот оплачен») записываются в SQLite (`storage/stats.sqlite3`) по дням,
поэтому статистика переживает перезапуски. Раз в день, во время из `[digest] time`
главного конфига, сводка отправляется всем администраторам; кнопка «Сводка сейчас»
в главном меню панели строит её в любой момент.
"""
from __future__ import annotations

import asyncio
import datetime
import os
import sqlite3
import threading
from zoneinfo import ZoneInfo

from loguru import logger

from playerokapi.common.enums import EventTypes

from .base import BaseModule

DB_FILE = os.path.join("storage", "stats.sqlite3")


class DigestModule(BaseModule):
    name = "digest"

    def __init__(self, cardinal, db_path: str = DB_FILE):
        super().__init__(cardinal)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS sales ("
                "day TEXT PRIMARY KEY, count INTEGER NOT NULL, revenue REAL NOT NULL)"
            )

    # ------------------------------------------------------------------
    # Статистика продаж
    # ------------------------------------------------------------------

    def _now(self) -> datetime.datetime:
        """Текущее время в часовом поясе продавца (`[digest] timezone`), иначе — сервера."""
        tz_name = self.cardinal.settings.digest.timezone
        return datetime.datetime.now(ZoneInfo(tz_name) if tz_name else None)

    def _today(self) -> str:
        return self._now().date().isoformat()

    def record_sale(self, price: float | None) -> None:
        """Учитывает одну продажу (продажи записываются всегда, даже при выключенной сводке)."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO sales (day, count, revenue) VALUES (?, 1, ?) "
                "ON CONFLICT(day) DO UPDATE SET count = count + 1, revenue = revenue + excluded.revenue",
                (self._today(), float(price or 0)),
            )

    def get_day_stats(self, day: str | None = None) -> tuple[int, float]:
        """Возвращает (число продаж, выручка) за день (по умолчанию — за сегодня)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT count, revenue FROM sales WHERE day = ?", (day or self._today(),)
            ).fetchone()
        return (row[0], row[1]) if row else (0, 0.0)

    def get_last_days(self, days: int) -> list[tuple[str, int, float]]:
        """
        Продажи за последние `days` дней (включая сегодня): список `(день, продаж, выручка)`,
        отсортированный от новых к старым. Дни без продаж не включаются.
        """
        since = (self._now().date() - datetime.timedelta(days=days - 1)).isoformat()
        with self._lock:
            rows = self._conn.execute(
                "SELECT day, count, revenue FROM sales WHERE day >= ? ORDER BY day DESC", (since,)
            ).fetchall()
        return [(row[0], row[1], row[2]) for row in rows]

    # ------------------------------------------------------------------
    # Текст сводки
    # ------------------------------------------------------------------

    def build_digest(self) -> str:
        """Строит текст сводки: продажи за сегодня, баланс, остатки складов, аптайм."""
        l10n = self.cardinal.l10n
        count, revenue = self.get_day_stats()

        account = self.cardinal.account
        profile = getattr(account, "profile", None)
        balance = profile.balance.format_balance(detailed=True) if profile is not None and profile.balance is not None else "?"

        manager = self.cardinal.autodelivery_manager
        stock_lines = []
        if manager is not None:
            for name in sorted(manager.stock_paths):
                stock_lines.append(l10n("digest_stock_line", name=name, stock=manager.get_stock_size(name)))
        stocks = "\n".join(stock_lines) if stock_lines else l10n("digest_no_stocks")

        return l10n(
            "digest_text",
            date=self._now().strftime("%d.%m.%Y"),
            sales=count,
            revenue=f"{revenue:g}",
            balance=balance,
            stocks=stocks,
            uptime=self.cardinal.uptime,
        )

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------

    async def on_event(self, event) -> None:
        if event.type is not EventTypes.ITEM_PAID:
            return
        deal = getattr(event, "deal", None)
        price = deal.item.price if deal is not None and deal.item is not None else None
        self.record_sale(price)

    async def on_start(self) -> None:
        self.cardinal.spawn(self._schedule_loop())

    def _next_run_at(self) -> datetime.datetime:
        """Ближайший момент отправки сводки по текущей настройке `[digest] time`."""
        hours, minutes = (int(part) for part in self.cardinal.settings.digest.time.split(":"))
        now = self._now()
        next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        if next_run <= now:
            next_run += datetime.timedelta(days=1)
        return next_run

    def _seconds_until_next_run(self) -> float:
        return (self._next_run_at() - self._now()).total_seconds()

    async def _schedule_loop(self) -> None:
        # Спим короткими интервалами (≤60 с) и держим цель актуальной: смена
        # [digest] time через перезагрузку конфигов подхватывается без рестарта.
        target = self._next_run_at()
        while True:
            now = self._now()
            if now >= target:
                await self._send_digest()
                target = self._next_run_at()
                continue
            candidate = self._next_run_at()
            if candidate.time() != target.time():
                # Администратор поменял время отправки — переносим цель.
                target = candidate
            await asyncio.sleep(min(60.0, max(0.0, (target - now).total_seconds())))

    async def _send_digest(self) -> None:
        if not self.enabled or self.cardinal.notifier is None:
            return
        try:
            text = await asyncio.to_thread(self.build_digest)
            await self.cardinal.notifier.send_text(text)
            logger.info("Ежедневная сводка отправлена администраторам")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Не удалось отправить ежедневную сводку")

    async def on_stop(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
