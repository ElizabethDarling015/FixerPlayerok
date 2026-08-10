"""
Автовосстановление лотов после продажи (аналог «автовосстановление лотов» FunPayCardinal).

На Playerok лот после продажи получает статус `SOLD` и исчезает из выдачи. Модуль на событие
оплаты (`ItemPaidEvent`) пересоздаёт лот: забирает полные данные проданного лота через
`get_item()`, создаёт копию `create_item()` и публикует её `publish_item()` с тем же типом
приоритета, что был у проданного (`DEFAULT` или `PREMIUM`).

Если у лота был PREMIUM, а на балансе не хватает денег (или publish падает) — лот
выставляется бесплатно (`DEFAULT`), а в Telegram уходит предупреждение.

Настраивается пофлагово на каждый лот в `configs/autodelivery.toml`:

- `restore = true` — восстанавливать лот после продажи;
- `deactivate_when_empty = true` — НЕ восстанавливать, если склад авто-выдачи этого лота пуст
  (и прислать уведомление о пустом складе).

Внимание: полнота копии (dataFields/attachments) подтверждена только по структуре API —
живой прогон на реальном аккаунте обязателен (см. HANDOFF).
"""
from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass

from loguru import logger

from playerokapi.common.enums import (
    EventTypes,
    GameCategoryDataFieldTypes,
    ItemDealDirections,
    ItemStatuses,
    PriorityTypes,
)

from .base import BaseModule


class RestoreError(Exception):
    """Не удалось восстановить лот (человекочитаемое сообщение для уведомления)."""


@dataclass
class RestoreResult:
    """Результат пересоздания лота (для выбора уведомления в `on_event`)."""

    item: object
    used_priority: PriorityTypes
    fallback_from_premium: bool = False
    fallback_reason: str = ""


def _pick_priority_status(statuses: list, wanted: PriorityTypes | None):
    """
    Возвращает статус приоритета нужного типа из списка `get_item_priority_statuses`.

    Если `wanted` нет или такого статуса в списке нет — `None`.
    """
    if wanted is None:
        return None
    return next(
        (s for s in statuses if s.type is not None and s.type is wanted),
        None,
    )


class AutoRestoreModule(BaseModule):
    name = "autorestore"

    def _lot_config(self, item_name: str):
        return self.cardinal.autodelivery_config.lots.get(item_name)

    async def on_event(self, event) -> None:
        if not self.enabled or event.type is not EventTypes.ITEM_PAID:
            return
        deal = event.deal
        if deal is None or deal.item is None or not deal.item.name:
            return
        if deal.direction is not None and deal.direction is not ItemDealDirections.OUT:
            return  # восстанавливаем только свои продажи

        item_name = deal.item.name
        lot = self._lot_config(item_name)
        if lot is None or not lot.restore:
            return

        # Пустой склад + флаг деактивации: лот не восстанавливаем, продажи останавливаются сами.
        manager = self.cardinal.autodelivery_manager
        if lot.deactivate_when_empty and manager is not None and manager.get_stock_size(item_name) <= 0:
            logger.warning("Автовосстановление: склад лота {!r} пуст — лот не восстанавливается", item_name)
            if self.cardinal.notifier is not None:
                with contextlib.suppress(Exception):
                    await self.cardinal.notifier.notify_stock_empty(item_name)
            return

        try:
            result = await asyncio.to_thread(self.restore_item, deal.item.id)
        except Exception as exc:
            logger.exception("Автовосстановление лота {!r} не удалось", item_name)
            if self.cardinal.notifier is not None:
                with contextlib.suppress(Exception):
                    await self.cardinal.notifier.notify_restore_failed(item_name, str(exc))
            return

        logger.success(
            "Лот {!r} восстановлен после продажи (новый ID: {}, приоритет: {})",
            item_name,
            result.item.id,
            result.used_priority.name,
        )
        if self.cardinal.notifier is None:
            return
        with contextlib.suppress(Exception):
            if result.fallback_from_premium:
                await self.cardinal.notifier.notify_restore_premium_fallback(
                    item_name, result.item.id, result.fallback_reason,
                )
            else:
                await self.cardinal.notifier.notify_restore_ok(item_name, result.item.id)

    # ------------------------------------------------------------------
    # Синхронная часть (выполняется в to_thread)
    # ------------------------------------------------------------------

    def _available_balance(self) -> int | None:
        """Доступный баланс аккаунта (None — неизвестен)."""
        account = self.cardinal.account
        balance = None
        with contextlib.suppress(Exception):
            balance = account.get_balance()
        if balance is None:
            profile = getattr(account, "profile", None)
            balance = getattr(profile, "balance", None) if profile is not None else None
        if balance is None:
            return None
        available = getattr(balance, "available", None)
        if available is not None:
            return int(available)
        value = getattr(balance, "value", None)
        return int(value) if value is not None else None

    def restore_item(self, item_id: str) -> RestoreResult:
        """
        Пересоздаёт проданный лот: `get_item` → `create_item`-копия → `publish_item`
        с тем же типом приоритета (`DEFAULT`/`PREMIUM`). При невозможности оплатить
        PREMIUM — публикация с DEFAULT и флаг `fallback_from_premium`.

        :raises RestoreError: Данных лота не хватает для пересоздания, либо лот не продан.
        """
        account = self.cardinal.account
        full = account.get_item(id=item_id)
        if full is None:
            raise RestoreError("проданный лот не найден по ID")
        if full.status is not None and full.status is not ItemStatuses.SOLD:
            raise RestoreError(f"лот не в статусе SOLD (текущий: {full.status.name})")
        if full.game is None or full.category is None:
            raise RestoreError("у лота нет данных об игре/категории — копию создать нельзя")

        data_fields = {
            f.id: f.value
            for f in (full.data_fields or [])
            if f.value is not None and (f.type is None or f.type is GameCategoryDataFieldTypes.ITEM_DATA)
        }
        new_item = account.create_item(
            game_id=full.game.id,
            category_id=full.category.id,
            name=full.name,
            price=full.price,
            description=full.description or "",
            obtaining_type_id=full.obtaining_type.id if full.obtaining_type else None,
            data_fields=data_fields or None,
            comment=full.comment,
        )
        if new_item is None:
            raise RestoreError("createItem вернул пустой ответ")

        wanted = full.priority if full.priority is not None else PriorityTypes.DEFAULT
        if wanted not in (PriorityTypes.DEFAULT, PriorityTypes.PREMIUM):
            wanted = PriorityTypes.DEFAULT

        statuses: list = []
        with contextlib.suppress(Exception):
            statuses = account.get_item_priority_statuses(new_item.id, new_item.price or full.price) or []

        default_status = _pick_priority_status(statuses, PriorityTypes.DEFAULT)
        premium_status = _pick_priority_status(statuses, PriorityTypes.PREMIUM)

        fallback_from_premium = False
        fallback_reason = ""
        publish_status = default_status
        used_priority = PriorityTypes.DEFAULT

        if wanted is PriorityTypes.PREMIUM:
            if premium_status is None:
                fallback_from_premium = True
                fallback_reason = "премиум-статус недоступен для этого лота"
            else:
                price = getattr(premium_status, "price", None) or 0
                available = self._available_balance()
                if available is not None and price and available < price:
                    fallback_from_premium = True
                    fallback_reason = f"не хватает баланса (нужно {price}, доступно {available})"
                else:
                    try:
                        published = account.publish_item(
                            new_item.id, priority_status_id=premium_status.id,
                        )
                        return RestoreResult(
                            item=published or new_item,
                            used_priority=PriorityTypes.PREMIUM,
                        )
                    except Exception as exc:
                        fallback_from_premium = True
                        fallback_reason = str(exc) or "ошибка оплаты премиум-статуса"
                        logger.warning(
                            "Автовосстановление: PREMIUM для {!r} не удался ({}) — фолбэк на DEFAULT",
                            full.name, fallback_reason,
                        )

        published = account.publish_item(
            new_item.id,
            priority_status_id=publish_status.id if publish_status else None,
        )
        return RestoreResult(
            item=published or new_item,
            used_priority=used_priority,
            fallback_from_premium=fallback_from_premium,
            fallback_reason=fallback_reason,
        )
