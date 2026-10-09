"""
Сводка дня и статистика продаж.

Цифры берутся из истории транзакций Playerok (продажи, см. `fixer/sales_stats.py`), а не
из счётчика бота: поэтому они не обнуляются после перезапуска и учитывают продажи, пока
бот был выключен, а возвраты в продажи не попадают. Раз в день, во время из `[digest] time`
главного конфига, сводка отправляется всем администраторам; кнопка «Сводка сейчас»
в главном меню панели строит её в любой момент.
"""
from __future__ import annotations

import asyncio
import datetime

from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from ..sales_stats import SalesHistory, fmt_rub, seller_tz, sum_totals, totals_by_day
from .base import BaseModule


class DigestModule(BaseModule):
    name = "digest"

    def __init__(self, fixer):
        super().__init__(fixer)
        self.history = SalesHistory()

    # ------------------------------------------------------------------
    # Статистика продаж (из Playerok)
    # ------------------------------------------------------------------

    def _tz(self):
        return seller_tz(self.fixer.settings)

    def _now(self) -> datetime.datetime:
        """Текущее время в часовом поясе продавца (`[digest] timezone`), иначе — сервера."""
        return datetime.datetime.now(self._tz())

    async def get_days(self, days: int) -> tuple[dict, datetime.date]:
        """Итоги по дням за последние `days` дней (включая сегодня) и сегодняшняя дата."""
        today = self._now().date()
        since = today - datetime.timedelta(days=days - 1)
        account = self.fixer.account
        if account is None:
            raise RuntimeError("Playerok не подключён")
        sales = await asyncio.to_thread(self.history.get, account, since, self._tz())
        return totals_by_day(sales), today

    # ------------------------------------------------------------------
    # Текст сводки
    # ------------------------------------------------------------------

    async def build_digest(self) -> str:
        """Сводка за сегодня: продажи, выручка, возвраты, баланс (+ склады авто-выдачи, если есть)."""
        l10n = self.fixer.l10n
        days, today = await self.get_days(1)
        t = sum_totals(days, today)

        account = self.fixer.account
        profile = getattr(account, "profile", None)
        balance = profile.balance.format_balance(detailed=True) if profile is not None and profile.balance is not None else "?"

        manager = self.fixer.autodelivery_manager
        stock_lines = []
        if manager is not None:
            for name in sorted(manager.stock_paths):
                stock_lines.append(l10n("digest_stock_line", name=name, stock=manager.get_stock_size(name)))
        stocks = l10n("digest_stocks_block", stocks="\n".join(stock_lines)) if stock_lines else ""

        return l10n(
            "digest_text",
            date=self._now().strftime("%d.%m.%Y"),
            sales=t.count,
            revenue=fmt_rub(t.gross),
            net=fmt_rub(t.net),
            refunds=t.refunds,
            balance=balance,
            stocks=stocks,
            uptime=self.fixer.uptime,
        )

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------

    async def on_start(self) -> None:
        self.fixer.spawn(self._schedule_loop())

    def _next_run_at(self) -> datetime.datetime:
        """Ближайший момент отправки сводки по текущей настройке `[digest] time`."""
        hours, minutes = (int(part) for part in self.fixer.settings.digest.time.split(":"))
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
        if not self.enabled or self.fixer.notifier is None:
            return
        try:
            text = await self.build_digest()
            
            # Создаём клавиатуру с кнопкой "Закрыть" для сводки
            builder = InlineKeyboardBuilder()
            builder.button(
                text=self.fixer.l10n("btn_close"),
                callback_data="close"
            )
            markup = builder.as_markup()
            
            await self.fixer.notifier.send_text(text, reply_markup=markup)
            logger.info("Ежедневная сводка отправлена администраторам")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Не удалось отправить ежедневую сводку")
