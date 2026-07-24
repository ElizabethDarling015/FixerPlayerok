"""
Авто-поднятие лотов по таймеру (аналог функции "поднятие лотов" в `FunPayCardinal`).

`AutoRaiseManager` периодически проходит по своим активным лотам и пытается купить для них
статус приоритета (`Account.increase_item_priority_status`). Если на балансе не хватает денег —
лот не поднимается в этом цикле (и не кидает исключение), а помечается как "пропущен по балансу";
`Runner` в этом случае породит `updater.events.InsufficientBalanceEvent`, на которое можно
подписаться (например, чтобы прислать себе уведомление в Telegram).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from . import types
from .common.enums import ItemStatuses, PriorityTypes

logger = logging.getLogger("playerokapi.autoraise")


@dataclass
class RaiseAttemptResult:
    """Результат попытки поднять один лот в рамках одного цикла `AutoRaiseManager.raise_all()`."""

    item_id: str
    """ID лота."""
    item_name: str | None
    """Название лота (для логов/уведомлений)."""
    raised: bool
    """Удалось ли поднять лот в этом цикле."""
    skipped_reason: str | None = None
    """
    Почему лот не был поднят (если `raised=False`): `"insufficient_balance"` (не хватило баланса),
    `"no_matching_status"` (нет статуса приоритета нужного типа для этого лота/цены),
    `"priority_statuses_error"`/`"raise_error"` (сетевая/GraphQL-ошибка — см. `error`).
    """
    priority_status: types.ItemPriorityStatus | None = None
    """Статус приоритета, который покупался/планировался к покупке."""
    spent: int | None = None
    """Сколько списано с баланса (заполнено только при `raised=True`)."""
    available: int | None = None
    """Сколько было доступно на балансе на момент попытки (заполнено при `skipped_reason="insufficient_balance"`)."""
    error: Exception | None = None
    """Исключение, если попытка завершилась ошибкой запроса."""


class AutoRaiseManager:
    """
    Периодически поднимает лоты продавца, покупая для них статус приоритета.

    :param item_ids: Список ID лотов, которые нужно поднимать. Если `None` — поднимаются все
        свои активные (`ItemStatuses.APPROVED`) лоты. Пустой список означает «не поднимать ничего»
        (в отличие от `None`).
    :param raise_interval: Как часто запускать цикл поднятия, в секундах — таймер, который
        использует `Runner`, если передать этот менеджер в `Runner(account, autoraise_manager=...)`.
        По умолчанию — 4 часа (`4 * 60 * 60`).
    :param priority_type: Какой тип статуса приоритета покупать (см. `common.enums.PriorityTypes`).
        По умолчанию `PREMIUM` — платный статус, реально поднимающий лот в списке (бесплатный
        `DEFAULT`-статус обычно и так активен, поднимать его не нужно).
    :param min_balance_reserve: Сколько денег на балансе всегда оставлять нетронутыми (не тратить
        на поднятие) — например, чтобы не залезать в сумму, отложенную на вывод.
    :param provider_id: ID провайдера оплаты статуса приоритета (см. `common.enums.TransactionProviderIds`).
        По умолчанию `"LOCAL"` — оплата с баланса аккаунта на сайте.
    :param should_raise: Опциональная функция `(item) -> bool` — дополнительное условие, стоит ли
        поднимать конкретный лот в этом цикле (например, пропускать лоты, которые и так на первом
        месте: `lambda item: item.priority_position != 1`). По умолчанию поднимаются все подходящие лоты.
    """

    def __init__(self, item_ids: list[str] | None = None, raise_interval: float = 4 * 60 * 60,
                 priority_type: PriorityTypes = PriorityTypes.PREMIUM, min_balance_reserve: int = 0,
                 provider_id: str = "LOCAL", should_raise: Callable[[types.ItemProfile], bool] | None = None):
        # Пустой список — это «не поднимать ничего», а не «поднимать все лоты» (все — только None).
        self.item_ids = set(item_ids) if item_ids is not None else None
        self.raise_interval = raise_interval
        self.priority_type = priority_type
        # Принимаем и член enum TransactionProviderIds, и голую строку "LOCAL".
        self.provider_id = provider_id.name if hasattr(provider_id, "name") else provider_id
        self.min_balance_reserve = min_balance_reserve
        self.should_raise = should_raise or (lambda item: True)

    def _get_target_items(self, account) -> list[types.ItemProfile]:
        items: list[types.ItemProfile] = []
        after_cursor = None
        while True:
            page = account.get_my_items(status=ItemStatuses.APPROVED, count=50, after_cursor=after_cursor)
            if not page:
                break
            items.extend(page.items)
            if not page.page_info or not page.page_info.has_next_page:
                break
            next_cursor = page.page_info.end_cursor
            if not next_cursor or next_cursor == after_cursor:
                # Защита от зацикливания при пустом/неподвижном курсоре пагинации.
                break
            after_cursor = next_cursor

        if self.item_ids is not None:
            items = [item for item in items if item.id in self.item_ids]
        return items

    def _select_priority_status(self, statuses: list[types.ItemPriorityStatus]) -> types.ItemPriorityStatus | None:
        matching = [s for s in statuses if s.type is self.priority_type]
        if not matching:
            return None
        return min(matching, key=lambda s: s.price if s.price is not None else 0)

    def raise_all(self, account) -> list[RaiseAttemptResult]:
        """
        Выполняет один цикл автоподнятия: находит подходящие лоты и пытается поднять каждый по очереди.

        Баланс проверяется один раз в начале цикла и уменьшается "в уме" по мере трат внутри цикла
        (без лишних запросов баланса между лотами), поэтому порядок обработки лотов имеет значение —
        при нехватке денег раньше в списке будут подняты лоты, идущие раньше.

        :param account: Аккаунт (должен быть после `Account(...).get()`).
        :return: Список результатов по каждому обработанному лоту (пустой список, если подходящих лотов нет).
        """
        results: list[RaiseAttemptResult] = []

        try:
            items = self._get_target_items(account)
        except Exception:
            logger.exception("Не удалось получить список лотов для автоподнятия")
            return results

        try:
            balance = account.get_balance()
        except Exception:
            # Ошибка запроса баланса — это не «нет денег»: пропускаем цикл целиком, чтобы не
            # завалить пользователя ложными InsufficientBalanceEvent по каждому лоту.
            logger.exception("Не удалось получить баланс аккаунта для автоподнятия — цикл пропущен")
            return results
        # Тратить можно только доступную часть баланса (замороженные средства не в счёт).
        raw_available = balance.available if balance and balance.available is not None else (
            balance.value if balance else 0)
        available = (raw_available or 0) - self.min_balance_reserve

        for item in items:
            if not self.should_raise(item):
                continue
            result = self._raise_one(account, item, available)
            results.append(result)
            if result.raised and result.spent:
                available -= result.spent

        return results

    def _raise_one(self, account, item: types.ItemProfile, available: int) -> RaiseAttemptResult:
        try:
            statuses = account.get_item_priority_statuses(item.id, item.price or 0)
        except Exception as exc:
            logger.warning("Не удалось получить статусы приоритета для лота %s: %s", item.id, exc)
            return RaiseAttemptResult(item.id, item.name, raised=False, skipped_reason="priority_statuses_error",
                                       error=exc)

        status = self._select_priority_status(statuses)
        if status is None:
            return RaiseAttemptResult(item.id, item.name, raised=False, skipped_reason="no_matching_status")

        price = status.price or 0
        if price > available:
            logger.info("Недостаточно баланса для поднятия лота %s (%r): нужно %d, доступно %d",
                        item.id, item.name, price, available)
            return RaiseAttemptResult(item.id, item.name, raised=False, skipped_reason="insufficient_balance",
                                       priority_status=status, available=available)

        try:
            # Само поднятие уже логируется на уровне Account.increase_item_priority_status (INFO),
            # здесь достаточно debug-отметки, что оно было инициировано именно автоподнятием.
            logger.debug("Автоподнятие: поднимаем лот %s (%r) за %d", item.id, item.name, price)
            raised_item = account.increase_item_priority_status(item.id, status.id, provider_id=self.provider_id)
        except Exception as exc:
            logger.warning("Не удалось поднять лот %s (%r): %s", item.id, item.name, exc)
            return RaiseAttemptResult(item.id, item.name, raised=False, skipped_reason="raise_error", error=exc)

        if raised_item is None:
            # Сервер не вернул обновлённый лот — считать поднятие успешным (и списывать баланс
            # "в уме") нельзя.
            logger.warning("Поднятие лота %s (%r) не подтверждено сервером (пустой ответ)", item.id, item.name)
            return RaiseAttemptResult(item.id, item.name, raised=False, skipped_reason="raise_error")

        return RaiseAttemptResult(item.id, item.name, raised=True, priority_status=status, spent=price)
