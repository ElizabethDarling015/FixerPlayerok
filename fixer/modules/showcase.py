"""Витрина после продаж и истёкшие лоты (работает всегда, отдельного тумблера нет).

После оплаты (через несколько секунд, чтобы Playerok успел сделать проданную копию):

* склад автовыдачи этого лота пуст → уведомление «Склад пуст»; если у лота включено
  «🛑 Снять с продажи при пустом складе» — бот снимает лот с продажи (иначе
  с «Оставлять в продаже» его продолжат покупать без товара);
* на уведомление «Новая сделка» ставится реакция: ⚡ — лот остался на витрине,
  👎 — лота на витрине нет (нужно выставить заново или он снят из-за пустого склада).

Раз в несколько часов бот смотрит истёкшие лоты: про каждый новый — уведомление
с кнопкой «🔄 Выставить заново» (платно, через экран с ценой). При первом запуске уже
истёкшие лоты только запоминаются — без уведомлений.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os

from loguru import logger

from playerokapi.common.enums import EventTypes, ItemDealDirections, ItemStatuses

from ..settings import STORAGE_DIR
from ..storefront import fetch_items, find_on_sale
from ..tg import reactions
from .base import BaseModule

#: Пауза после оплаты перед проверкой витрины.
CHECK_DELAY = 15.0
#: Как часто проверять истёкшие лоты (и первая проверка — через минуту после старта).
EXPIRED_INTERVAL = 6 * 3600
EXPIRED_FIRST_DELAY = 60.0
EXPIRED_SEEN_FILE = os.path.join(STORAGE_DIR, "expired_seen.json")


class ShowcaseModule(BaseModule):
    name = "showcase"

    def __init__(self, fixer):
        super().__init__(fixer)
        self.delay = CHECK_DELAY
        self._checked_deals: set[str] = set()

    @property
    def enabled(self) -> bool:  # всегда включён
        return True

    # ------------------------------------------------------------------
    # После продажи
    # ------------------------------------------------------------------

    async def on_event(self, event) -> None:
        if event.type is not EventTypes.ITEM_PAID:
            return
        deal = getattr(event, "deal", None)
        if deal is None or not getattr(deal, "id", None) or deal.id in self._checked_deals:
            return
        if deal.direction is not None and deal.direction is not ItemDealDirections.OUT:
            return
        self._checked_deals.add(deal.id)
        self.fixer.spawn(self._after_sale(deal))

    async def _after_sale(self, deal) -> None:
        await asyncio.sleep(self.delay)
        try:
            await self.check_after_sale(deal)
        except Exception:
            logger.exception("[витрина] Проверка после продажи упала (сделка {})", deal.id)

    async def check_after_sale(self, deal) -> None:
        account = self.fixer.account
        notifier = self.fixer.notifier
        if account is None:
            return
        name = getattr(getattr(deal, "item", None), "name", None)
        on_sale = await asyncio.to_thread(find_on_sale, account, name)

        lot = self.fixer.autodelivery_config.lots.get(name or "")
        manager = getattr(self.fixer, "autodelivery_manager", None)
        if lot is not None and manager is not None and manager.get_stock_size(name) <= 0:
            paused = False
            if lot.deactivate_when_empty and on_sale is not None:
                try:
                    await asyncio.to_thread(account.discontinue_item, on_sale.id)
                    paused, on_sale = True, None
                    logger.warning("[витрина] Склад «{}» пуст — лот снят с продажи", name)
                except Exception:
                    logger.exception("[витрина] Не удалось снять с продажи «{}»", name)
            if notifier is not None:
                with contextlib.suppress(Exception):
                    await notifier.notify_stock_empty(name, paused=paused)

        if notifier is not None:
            emoji = reactions.ON_SALE if on_sale is not None else reactions.OFF_SALE
            with contextlib.suppress(Exception):
                await notifier.react_deal(deal.id, emoji)

    # ------------------------------------------------------------------
    # Истёкшие лоты
    # ------------------------------------------------------------------

    async def on_start(self) -> None:
        self.fixer.spawn(self._expired_loop())

    async def _expired_loop(self) -> None:
        await asyncio.sleep(EXPIRED_FIRST_DELAY)
        while True:
            try:
                await self.check_expired()
            except Exception:
                logger.exception("[витрина] Проверка истёкших лотов упала")
            await asyncio.sleep(EXPIRED_INTERVAL)

    @staticmethod
    def _load_seen() -> set[str] | None:
        with contextlib.suppress(Exception):
            if os.path.isfile(EXPIRED_SEEN_FILE):
                with open(EXPIRED_SEEN_FILE, encoding="utf-8") as f:
                    return set(json.load(f))
        return None

    @staticmethod
    def _save_seen(ids: set[str]) -> None:
        with contextlib.suppress(Exception):
            os.makedirs(os.path.dirname(EXPIRED_SEEN_FILE) or ".", exist_ok=True)
            with open(EXPIRED_SEEN_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted(ids), f)

    async def check_expired(self) -> list:
        """Один проход: уведомляет о новых истёкших лотах. Возвращает новые."""
        account = self.fixer.account
        if account is None or not getattr(self.fixer, "playerok_connected", True):
            return []
        expired = await asyncio.to_thread(fetch_items, account, [ItemStatuses.EXPIRED])
        current = {item.id for item in expired if getattr(item, "id", None)}
        seen = self._load_seen()
        # Запоминаем только то, что истёкло сейчас: лот, который выставили и он истёк снова,
        # придёт уведомлением ещё раз.
        self._save_seen(current)
        if seen is None:  # первый запуск — старые истёкшие не присылаем
            return []
        fresh = [item for item in expired if item.id not in seen]
        notifier = self.fixer.notifier
        if notifier is not None:
            for item in fresh:
                with contextlib.suppress(Exception):
                    await notifier.notify_item_expired(item)
        return fresh
