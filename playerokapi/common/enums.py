"""
Перечисления (Enum), используемые библиотекой `playerokapi`.

Значения максимально близки к "сырым" строковым значениям, которые присылает GraphQL API Playerok
(имя члена enum совпадает с сырым значением сайта), чтобы `parser.py` мог сопоставлять их через
`SomeEnum.__members__.get(raw_value)`.
"""
from enum import Enum


class EventTypes(Enum):
    """Типы событий `Runner`."""

    CHAT_INITIALIZED = 0
    """Чат обнаружен (например, при первом запуске `Runner`)."""
    NEW_MESSAGE = 1
    """Новое сообщение в чате."""
    NEW_DEAL = 2
    """Новая сделка (покупатель оплатил лот)."""
    NEW_REVIEW = 3
    """Новый отзыв от покупателя."""
    DEAL_CONFIRMED = 4
    """Сделка подтверждена покупателем (получение товара подтверждено)."""
    DEAL_CONFIRMED_AUTOMATICALLY = 5
    """Сделка подтверждена автоматически (истёк срок ожидания ответа покупателя)."""
    DEAL_ROLLED_BACK = 6
    """Сделка отменена/возвращена."""
    DEAL_HAS_PROBLEM = 7
    """В сделке заявлена проблема."""
    DEAL_PROBLEM_RESOLVED = 8
    """Проблема в сделке решена."""
    DEAL_STATUS_CHANGED = 9
    """Статус сделки изменился (общее событие, срабатывает вместе с более конкретными)."""
    ITEM_PAID = 10
    """Покупатель оплатил лот (совпадает по смыслу с `NEW_DEAL`, но относится к самому предмету)."""
    ITEM_SENT = 11
    """Продавец подтвердил выполнение сделки (отправил товар)."""
    ITEM_RAISED = 12
    """Лот успешно поднят автоподнятием (`AutoRaiseManager`, см. `playerokapi/autoraise.py`)."""
    INSUFFICIENT_BALANCE = 13
    """
    Не хватило баланса, чтобы поднять лот автоподнятием.

    Само поднятие не отменяется навсегда — при следующем цикле `AutoRaiseManager` попробует снова
    (например, после того как на баланс поступят деньги от новой продажи).
    """
    ITEM_UPDATED = 14
    """Лот обновлён (WS-подписка `itemUpdated`)."""
    ITEM_CREATED = 15
    """Создан новый лот (WS-подписка `itemCreated`)."""
    CHAT_CREATED = 16
    """Создан новый чат (WS-подписка `chatCreated`)."""


class Hooks(Enum):
    """
    Хуки плагинной системы (`playerokapi.plugins.PluginManager`).

    Помимо этих фиксированных хуков жизненного цикла и событий, `PluginManager` также поддерживает
    автоматические хуки `PRE_<имя_метода>` / `POST_<имя_метода>` на каждый публичный метод `Account`
    (например `PRE_send_message`, `POST_create_item`) — они не перечислены здесь явно, так как
    генерируются динамически по названию метода.
    """

    PRE_INIT = "PRE_INIT"
    """До вызова `Account.get()`."""
    POST_INIT = "POST_INIT"
    """После вызова `Account.get()`."""
    PRE_START = "PRE_START"
    """До запуска `Runner.listen()`."""
    POST_START = "POST_START"
    """После запуска `Runner.listen()`."""
    PRE_STOP = "PRE_STOP"
    """До остановки `Runner`."""
    POST_STOP = "POST_STOP"
    """После остановки `Runner`."""
    INIT_MESSAGE = "INIT_MESSAGE"
    """При первом обнаружении чата (см. `ChatInitializedEvent`)."""
    NEW_MESSAGE = "NEW_MESSAGE"
    """Новое сообщение в чате."""
    NEW_DEAL = "NEW_DEAL"
    """Новая сделка."""
    DEAL_STATUS_CHANGED = "DEAL_STATUS_CHANGED"
    """Изменение статуса сделки."""
    DEAL_CONFIRMED = "DEAL_CONFIRMED"
    """Сделка подтверждена покупателем (см. `updater.events.DealConfirmedEvent`)."""
    DEAL_CONFIRMED_AUTOMATICALLY = "DEAL_CONFIRMED_AUTOMATICALLY"
    """Сделка подтверждена автоматически (см. `updater.events.DealConfirmedAutomaticallyEvent`)."""
    DEAL_ROLLED_BACK = "DEAL_ROLLED_BACK"
    """Сделка отменена/возвращена (см. `updater.events.DealRolledBackEvent`)."""
    ITEM_PAID = "ITEM_PAID"
    """Покупатель оплатил лот (см. `updater.events.ItemPaidEvent`)."""
    ITEM_SENT = "ITEM_SENT"
    """Продавец подтвердил выполнение сделки (см. `updater.events.ItemSentEvent`)."""
    ITEM_RAISED = "ITEM_RAISED"
    """Лот успешно поднят автоподнятием (см. `updater.events.ItemRaisedEvent`)."""
    DEAL_HAS_PROBLEM = "DEAL_HAS_PROBLEM"
    """В сделке заявлена проблема (см. `updater.events.DealHasProblemEvent`)."""
    DEAL_PROBLEM_RESOLVED = "DEAL_PROBLEM_RESOLVED"
    """Проблема в сделке решена (см. `updater.events.DealProblemResolvedEvent`)."""
    NEW_REVIEW = "NEW_REVIEW"
    """Новый отзыв от покупателя (см. `updater.events.NewReviewEvent`)."""
    PRE_LOTS_RAISE = "PRE_LOTS_RAISE"
    """До вызова `increase_item_priority_status` (поднятие лота)."""
    POST_LOTS_RAISE = "POST_LOTS_RAISE"
    """После вызова `increase_item_priority_status`."""
    PRE_DELIVERY = "PRE_DELIVERY"
    """До авто-выдачи товара."""
    POST_DELIVERY = "POST_DELIVERY"
    """После авто-выдачи товара."""
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    """Не хватило баланса на поднятие лота автоподнятием (см. `EventTypes.INSUFFICIENT_BALANCE`)."""


class ItemLogEvents(Enum):
    """События в логах предмета (`ItemLog.event`)."""

    PAID = 0
    """Предмет оплачен."""
    SENT = 1
    """Товар сделки отправлен продавцом."""
    DEAL_CONFIRMED = 2
    """Сделка подтверждена покупателем."""
    DEAL_ROLLED_BACK = 3
    """Сделка возвращена."""
    PROBLEM_REPORTED = 4
    """Отправлена жалоба (создана проблема)."""
    PROBLEM_RESOLVED = 5
    """Проблема решена."""


class ItemDealStatuses(Enum):
    """"Сырые" статусы сделки, как они приходят от GraphQL API Playerok."""

    PAID = 0
    """Сделка оплачена, ожидает отправки товара."""
    PENDING = 1
    """Сделка в ожидании (промежуточный статус)."""
    SENT = 2
    """Продавец подтвердил выполнение сделки (товар отправлен)."""
    CONFIRMED = 3
    """Сделка подтверждена покупателем."""
    CONFIRMED_AUTOMATICALLY = 4
    """Сделка подтверждена автоматически (по истечении срока ожидания)."""
    ROLLED_BACK = 5
    """Сделка отменена/возвращена."""


class DealStatuses(Enum):
    """
    "Дружелюбные" статусы сделки (аналог `FunPayAPI.common.enums.OrderStatuses`).

    В отличие от `ItemDealStatuses` (сырые значения сайта), этот enum группирует статусы
    в понятные категории. Сопоставление делается в `parser.py`:
    `PAID`→`PAID`, `PENDING`→`PENDING`, `SENT`→`SENT`,
    `CONFIRMED`/`CONFIRMED_AUTOMATICALLY`→`COMPLETED`, `ROLLED_BACK`→`CANCELED`.
    """

    PAID = 0
    """Сделка оплачена, ожидает отправки товара продавцом."""
    PENDING = 1
    """Сделка в ожидании (промежуточный статус)."""
    SENT = 2
    """Товар отправлен, ожидает подтверждения покупателем."""
    COMPLETED = 3
    """Сделка завершена (см. `ItemDeal.completed_automatically`, чтобы узнать, было ли это автоматически)."""
    CANCELED = 4
    """Сделка отменена/возвращена."""


class ItemDealDirections(Enum):
    """Направление сделки относительно вашего аккаунта."""

    IN = 0
    """Покупка (вы — покупатель)."""
    OUT = 1
    """Продажа (вы — продавец)."""


class GameTypes(Enum):
    """Типы игр/приложений на Playerok."""

    GAME = 0
    """Игра."""
    APPLICATION = 1
    """Приложение."""


class UserTypes(Enum):
    """Типы (роли) пользователей."""

    USER = 0
    """Обычный пользователь."""
    MODERATOR = 1
    """Модератор."""
    BOT = 2
    """Бот."""
    CHECKER = 3
    """Проверяющий."""


class ChatTypes(Enum):
    """Типы чатов."""

    PM = 0
    """Приватный чат (диалог с другим пользователем)."""
    NOTIFICATIONS = 1
    """Чат уведомлений."""
    SUPPORT = 2
    """Чат поддержки."""


class ChatStatuses(Enum):
    """Статусы чатов."""

    NEW = 0
    """Новый чат (нет ни одного прочитанного сообщения)."""
    FINISHED = 1
    """Чат доступен, переписка в нём возможна."""


class ChatMessageButtonTypes(Enum):
    """Типы кнопок сообщений."""

    REDIRECT = 0
    """Кнопка-ссылка (перенаправляет на URL)."""
    LOTTERY = 1
    """Кнопка розыгрыша/акции."""


class ChatMessageEvents(Enum):
    """Системные события внутри сообщений чата."""

    CHAT_STARTED = 0
    """Переписка началась (например, к чату поддержки подключился помощник)."""
    CHAT_FINISHED = 1
    """Переписка завершилась."""


class ItemStatuses(Enum):
    """Статусы лота (предмета)."""

    PENDING_APPROVAL = 0
    """Ожидает первичной проверки модерацией."""
    PENDING_MODERATION = 1
    """Ожидает проверки изменений модерацией."""
    APPROVED = 2
    """Активен (опубликован, принят модерацией)."""
    DECLINED = 3
    """Отклонён модерацией."""
    BLOCKED = 4
    """Заблокирован."""
    EXPIRED = 5
    """Истёк срок размещения."""
    SOLD = 6
    """Продан."""
    DRAFT = 7
    """Черновик (создан, но не выставлен на продажу)."""


class PriorityTypes(Enum):
    """Типы приоритета лота."""

    DEFAULT = 0
    """Стандартный (бесплатный) приоритет."""
    PREMIUM = 1
    """Премиум (платный) приоритет — поднимает лот выше в списке."""


class ReviewStatuses(Enum):
    """Статусы отзывов."""

    APPROVED = 0
    """Отзыв активен и виден на сайте."""
    DELETED = 1
    """Отзыв удалён."""


class SortDirections(Enum):
    """Направление сортировки при запросах списков."""

    DESC = 0
    """По убыванию."""
    ASC = 1
    """По возрастанию."""


class GameCategoryAgreementIconTypes(Enum):
    """Типы иконок соглашений покупателя/продавца в категории."""

    RESTRICTION = 0
    """Иконка ограничения."""
    CONFIRMATION = 1
    """Иконка подтверждения."""


class GameCategoryOptionTypes(Enum):
    """Типы опций (атрибутов) категории."""

    SELECTOR = 0
    """Выбор значения из списка."""
    SWITCH = 1
    """Переключатель (да/нет)."""


class GameCategoryDataFieldTypes(Enum):
    """Типы полей с данными категории."""

    ITEM_DATA = 0
    """Данные о самом предмете, заполняются продавцом при создании лота."""
    OBTAINING_DATA = 1
    """Данные, которые заполняет покупатель при оформлении покупки (продавцу заполнять не нужно)."""


class GameCategoryDataFieldInputTypes(Enum):
    """Типы полей ввода данных категории."""

    INPUT = 0
    """Текстовое поле ввода."""


class GameCategoryAutoConfirmPeriods(Enum):
    """Периоды автоматического подтверждения сделки в категории."""

    SEVEN_DAYS = 0
    """Семь дней."""


class GameCategoryInstructionTypes(Enum):
    """Типы инструкций категории по продаже/покупке."""

    FOR_SELLER = 0
    """Инструкция для продавца."""
    FOR_BUYER = 1
    """Инструкция для покупателя."""


class TransactionProviderIds(Enum):
    """
    ID провайдеров транзакции.

    Используется, например, при публикации/поднятии лота (`publish_item`, `increase_item_priority_status`),
    где `LOCAL` означает оплату с баланса аккаунта на сайте — без необходимости в полноценной
    финансовой подсистеме (вывод средств, карты, СБП — вне охвата Фазы 1).
    """

    LOCAL = 0
    """Оплата с баланса аккаунта на сайте."""
    SBP = 1
    """Оплата через СБП."""
    BANK_CARD_RU = 2
    """Оплата банковской картой (Россия)."""
    BANK_CARD_BY = 3
    """Оплата банковской картой (Беларусь)."""
    BANK_CARD = 4
    """Оплата иностранной банковской картой."""
    YMONEY = 5
    """Оплата через ЮMoney."""
    USDT = 6
    """Оплата криптовалютой USDT (TRC20)."""
    PENDING_INCOME = 7
    """Оплата из замороженных (ожидающих поступления) средств."""


class TransactionPaymentMethodIds(Enum):
    """ID способов оплаты транзакции."""

    MIR = 0
    """Банковская карта МИР."""
    VISA_MASTERCARD = 1
    """Банковская карта VISA/Mastercard."""
    ERIP = 2
    """Оплата через ЕРИП."""


class TransactionOperations(Enum):
    """
    Типы операций транзакции.

    Полноценная финансовая подсистема (история транзакций, вывод средств, карты) вне охвата Фазы 1,
    но этот enum используется в лёгком снимке `ItemDealTransaction`, привязанном к конкретной сделке/лоту.
    """

    DEPOSIT = 0
    """Пополнение баланса."""
    BUY = 1
    """Оплата покупки."""
    SELL = 2
    """Продажа (поступление средств продавцу)."""
    ITEM_DEFAULT_PRIORITY = 3
    """Оплата бесплатного приоритета лота."""
    ITEM_PREMIUM_PRIORITY = 4
    """Оплата премиум-приоритета лота."""
    WITHDRAW = 5
    """Вывод средств."""
    MANUAL_BALANCE_INCREASE = 6
    """Начисление на баланс аккаунта вручную (администрацией)."""
    MANUAL_BALANCE_DECREASE = 7
    """Списание с баланса аккаунта вручную (администрацией)."""
    REFERRAL_BONUS = 8
    """Бонус за приглашение друга (реферал)."""
    STEAM_DEPOSIT = 9
    """Оплата пополнения Steam."""


class TransactionDirections(Enum):
    """Направление движения средств по транзакции."""

    IN = 0
    """Начисление."""
    OUT = 1
    """Списание."""


class TransactionStatuses(Enum):
    """Статусы обработки транзакции."""

    PENDING = 0
    """В ожидании (оплачена, но средства ещё не поступили)."""
    PROCESSING = 1
    """В заморозке/обработке."""
    CONFIRMED = 2
    """Подтверждена."""
    ROLLED_BACK = 3
    """Возвращена."""
    FAILED = 4
    """Завершилась с ошибкой."""


class MessageTemplateTypes(Enum):
    """Типы шаблонных сообщений (используются, например, при жалобе на проблему в сделке)."""

    ACTIVE_DEAL_PROBLEM = 0
    """Проблема в активной сделке."""
    FINISHED_DEAL_PROBLEM = 1
    """Проблема в завершённой сделке."""
