"""События, которые генерирует `Runner.listen()` (аналог `FunPayAPI.updater.events`)."""
from __future__ import annotations

from .. import types
from ..common.enums import EventTypes


class BaseEvent:
    """Базовый класс всех событий `Runner`."""

    def __init__(self, type: EventTypes, runner):
        self.type: EventTypes = type
        """Тип события (см. `common.enums.EventTypes`)."""
        self.runner = runner
        """Экземпляр `Runner`, породившего событие."""


class ChatInitializedEvent(BaseEvent):
    """Чат обнаружен впервые (например, при первом запуске `Runner`, до этого момента о нём не было известно)."""

    def __init__(self, runner, chat: types.Chat):
        super().__init__(EventTypes.CHAT_INITIALIZED, runner)
        self.chat: types.Chat = chat
        """Обнаруженный чат."""


class NewMessageEvent(BaseEvent):
    """Новое сообщение в чате."""

    def __init__(self, runner, chat: types.Chat, message: types.ChatMessage):
        super().__init__(EventTypes.NEW_MESSAGE, runner)
        self.chat: types.Chat = chat
        """Чат, в котором появилось сообщение."""
        self.message: types.ChatMessage = message
        """Новое сообщение."""


class NewDealEvent(BaseEvent):
    """Новая сделка (обнаружена при периодическом опросе `Account.get_deals()`)."""

    def __init__(self, runner, deal: types.ItemDeal):
        super().__init__(EventTypes.NEW_DEAL, runner)
        self.deal: types.ItemDeal = deal
        """Новая сделка."""


class DealStatusChangedEvent(BaseEvent):
    """Статус сделки изменился (общее событие — срабатывает вместе с более конкретными, если применимо)."""

    _event_type = EventTypes.DEAL_STATUS_CHANGED

    def __init__(self, runner, deal: types.ItemDeal, previous_status, new_status):
        super().__init__(self._event_type, runner)
        self.deal: types.ItemDeal = deal
        """Сделка с изменившимся статусом."""
        self.previous_status = previous_status
        """Предыдущий "сырой" статус сделки (см. `common.enums.ItemDealStatuses`)."""
        self.new_status = new_status
        """Новый "сырой" статус сделки."""


class DealConfirmedEvent(DealStatusChangedEvent):
    """Сделка подтверждена покупателем."""

    _event_type = EventTypes.DEAL_CONFIRMED


class DealConfirmedAutomaticallyEvent(DealStatusChangedEvent):
    """Сделка подтверждена автоматически (истёк срок ожидания ответа покупателя)."""

    _event_type = EventTypes.DEAL_CONFIRMED_AUTOMATICALLY


class DealRolledBackEvent(DealStatusChangedEvent):
    """Сделка отменена/возвращена."""

    _event_type = EventTypes.DEAL_ROLLED_BACK


class ItemSentEvent(DealStatusChangedEvent):
    """Продавец подтвердил выполнение сделки (товар отправлен)."""

    _event_type = EventTypes.ITEM_SENT


class ItemPaidEvent(BaseEvent):
    """
    Покупатель оплатил лот.

    Определяется по системному сообщению-маркеру в чате (аналогично оригинальному
    `alleexxeeyy/PlayerokAPI`) либо по появлению новой сделки со статусом `PAID`.
    Именно на это событие реагирует `AutoDeliveryManager` (см. `playerokapi/autodelivery.py`).
    """

    def __init__(self, runner, chat: types.Chat, message: types.ChatMessage | None, deal: types.ItemDeal | None):
        super().__init__(EventTypes.ITEM_PAID, runner)
        self.chat: types.Chat = chat
        """Чат, в котором произошла оплата."""
        self.message: types.ChatMessage | None = message
        """Системное сообщение об оплате (если событие обнаружено через чат)."""
        self.deal: types.ItemDeal | None = deal
        """Оплаченная сделка (если известна на момент события)."""


class NewReviewEvent(BaseEvent):
    """
    Новый отзыв от покупателя.

    Обнаруживается при периодическом опросе (`Account.get_my_reviews()`) — сравнением списка ID
    отзывов со снимком с предыдущего опроса, аналогично `NewDealEvent`.
    """

    def __init__(self, runner, review: types.Review):
        super().__init__(EventTypes.NEW_REVIEW, runner)
        self.review: types.Review = review
        """Новый отзыв."""


class DealHasProblemEvent(BaseEvent):
    """
    В сделке заявлена проблема.

    Обнаруживается при периодическом опросе (`Account.get_deals()`) — сравнением поля
    `ItemDeal.has_problem` со снимком с предыдущего опроса (`False` → `True`). Срабатывает
    независимо от того, кто заявил проблему (покупатель или продавец).
    """

    def __init__(self, runner, deal: types.ItemDeal):
        super().__init__(EventTypes.DEAL_HAS_PROBLEM, runner)
        self.deal: types.ItemDeal = deal
        """Сделка, в которой заявлена проблема."""


class DealProblemResolvedEvent(BaseEvent):
    """
    Проблема в сделке решена.

    Обнаруживается при периодическом опросе (`Account.get_deals()`) — сравнением поля
    `ItemDeal.has_problem` со снимком с предыдущего опроса (`True` → `False`).
    """

    def __init__(self, runner, deal: types.ItemDeal):
        super().__init__(EventTypes.DEAL_PROBLEM_RESOLVED, runner)
        self.deal: types.ItemDeal = deal
        """Сделка, в которой проблема была решена."""


class ItemRaisedEvent(BaseEvent):
    """
    Лот успешно поднят автоподнятием (см. `playerokapi.autoraise.AutoRaiseManager`).

    :ivar result: `playerokapi.autoraise.RaiseAttemptResult` — содержит `item_id`, `item_name`,
        купленный `priority_status` и потраченную сумму (`spent`).
    """

    def __init__(self, runner, result):
        super().__init__(EventTypes.ITEM_RAISED, runner)
        self.result = result


class InsufficientBalanceEvent(BaseEvent):
    """
    Не хватило баланса, чтобы поднять лот автоподнятием.

    Дождитесь пополнения баланса (например, от новой продажи) — при следующем цикле
    `AutoRaiseManager` попробует поднять лот снова.

    :ivar result: `playerokapi.autoraise.RaiseAttemptResult` — содержит `item_id`, `item_name`,
        желаемый `priority_status` (и его цену — `priority_status.price`) и то, сколько реально
        было доступно на балансе (`available`).
    """

    def __init__(self, runner, result):
        super().__init__(EventTypes.INSUFFICIENT_BALANCE, runner)
        self.result = result


class ItemUpdatedEvent(BaseEvent):
    """Лот обновлён (WS `itemUpdated`)."""

    def __init__(self, runner, item: types.MyItem | types.Item | None):
        super().__init__(EventTypes.ITEM_UPDATED, runner)
        self.item = item


class ItemCreatedEvent(BaseEvent):
    """Создан новый лот (WS `itemCreated`)."""

    def __init__(self, runner, item: types.MyItem | types.Item | None):
        super().__init__(EventTypes.ITEM_CREATED, runner)
        self.item = item


class ChatCreatedEvent(BaseEvent):
    """Создан новый чат (WS `chatCreated`)."""

    def __init__(self, runner, chat: types.Chat):
        super().__init__(EventTypes.CHAT_CREATED, runner)
        self.chat: types.Chat = chat
