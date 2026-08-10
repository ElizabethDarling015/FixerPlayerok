"""
Типы данных (классы) библиотеки `playerokapi`.

Поля классов максимально близки к оригинальным полям GraphQL API Playerok (см.
`alleexxeeyy/PlayerokAPI`), чтобы поведение библиотеки было предсказуемым и покрывало весь
нужный функционал сайта — но каждое поле имеет понятный русский докстринг.

Финансовые сущности представлены типами `Transaction`, `Payout`, `VerifiedCard` (и списками).
Лёгкий снимок транзакции у сделки/лота — по-прежнему `ItemDealTransaction`.
"""
from __future__ import annotations

from .common.enums import (
    UserTypes,
    ChatTypes,
    ChatStatuses,
    ChatMessageButtonTypes,
    ChatMessageEvents,
    ItemDealStatuses,
    DealStatuses,
    ItemDealDirections,
    ItemStatuses,
    PriorityTypes,
    ReviewStatuses,
    GameTypes,
    GameCategoryAgreementIconTypes,
    GameCategoryOptionTypes,
    GameCategoryDataFieldTypes,
    GameCategoryDataFieldInputTypes,
    GameCategoryAutoConfirmPeriods,
    ItemLogEvents,
    TransactionOperations,
    TransactionDirections,
    TransactionProviderIds,
    TransactionStatuses,
    MessageTemplateTypes,
)


class FileObject:
    """Файл (изображение, приложенное к лоту, сообщению чата и т.п.)."""

    def __init__(self, id: str, url: str, filename: str | None, mime: str | None):
        self.id: str = id
        """ID файла."""
        self.url: str = url
        """URL файла."""
        self.filename: str | None = filename
        """Имя файла."""
        self.mime: str | None = mime
        """MIME-тип файла."""


class AccountBalance:
    """Баланс аккаунта."""

    def __init__(self, id: str | None, value: int, frozen: int | None, available: int | None,
                 withdrawable: int | None, pending_income: int | None):
        self.id: str | None = id
        """ID объекта баланса."""
        self.value: int = value
        """Сумма общего баланса."""
        self.frozen: int | None = frozen
        """Сумма замороженного баланса."""
        self.available: int | None = available
        """Сумма доступного к использованию баланса."""
        self.withdrawable: int | None = withdrawable
        """Сумма, доступная для вывода."""
        self.pending_income: int | None = pending_income
        """Ожидаемый доход (в обработке)."""


class AccountItemsStats:
    """Статистика по лотам аккаунта."""

    def __init__(self, total: int | None, finished: int | None):
        self.total: int | None = total
        """Всего лотов."""
        self.finished: int | None = finished
        """Кол-во завершённых (проданных) лотов."""


class AccountIncomingDealsStats:
    """Статистика входящих сделок аккаунта (покупки)."""

    def __init__(self, total: int | None, finished: int | None):
        self.total: int | None = total
        """Всего входящих сделок."""
        self.finished: int | None = finished
        """Кол-во завершённых входящих сделок."""


class AccountOutgoingDealsStats:
    """Статистика исходящих сделок аккаунта (продажи)."""

    def __init__(self, total: int | None, finished: int | None):
        self.total: int | None = total
        """Всего исходящих сделок."""
        self.finished: int | None = finished
        """Кол-во завершённых исходящих сделок."""


class AccountDealsStats:
    """Статистика сделок аккаунта."""

    def __init__(self, incoming: AccountIncomingDealsStats | None, outgoing: AccountOutgoingDealsStats | None):
        self.incoming: AccountIncomingDealsStats | None = incoming
        """Статистика входящих сделок (покупок)."""
        self.outgoing: AccountOutgoingDealsStats | None = outgoing
        """Статистика исходящих сделок (продаж)."""


class AccountStats:
    """Общая статистика аккаунта."""

    def __init__(self, items: AccountItemsStats | None, deals: AccountDealsStats | None):
        self.items: AccountItemsStats | None = items
        """Статистика лотов."""
        self.deals: AccountDealsStats | None = deals
        """Статистика сделок."""


class AccountProfile:
    """Расширенный профиль своего аккаунта (заполняется в `Account.get()`)."""

    def __init__(self, id: str, username: str | None, email: str | None, balance: AccountBalance | None,
                 stats: AccountStats | None, role: UserTypes | None, avatar_url: str | None, is_online: bool | None,
                 is_blocked: bool | None, is_blocked_for: str | None, is_verified: bool | None, rating: int | None,
                 reviews_count: int | None, created_at: str | None, support_chat_id: str | None,
                 system_chat_id: str | None, has_frozen_balance: bool | None, has_enabled_notifications: bool | None,
                 unread_chats_counter: int | None):
        self.id: str = id
        """ID аккаунта."""
        self.username: str | None = username
        """Никнейм аккаунта."""
        self.email: str | None = email
        """Email аккаунта."""
        self.balance: AccountBalance | None = balance
        """Баланс аккаунта."""
        self.stats: AccountStats | None = stats
        """Статистика аккаунта (лоты/сделки)."""
        self.role: UserTypes | None = role
        """Роль аккаунта."""
        self.avatar_url: str | None = avatar_url
        """URL аватара аккаунта."""
        self.is_online: bool | None = is_online
        """В сети ли аккаунт прямо сейчас."""
        self.is_blocked: bool | None = is_blocked
        """Заблокирован ли аккаунт."""
        self.is_blocked_for: str | None = is_blocked_for
        """Причина блокировки аккаунта."""
        self.is_verified: bool | None = is_verified
        """Верифицирован ли аккаунт."""
        self.rating: int | None = rating
        """Рейтинг аккаунта (0-5)."""
        self.reviews_count: int | None = reviews_count
        """Количество отзывов об аккаунте."""
        self.created_at: str | None = created_at
        """Дата создания аккаунта (ISO 8601)."""
        self.support_chat_id: str | None = support_chat_id
        """ID чата поддержки."""
        self.system_chat_id: str | None = system_chat_id
        """ID системного чата (уведомления)."""
        self.has_frozen_balance: bool | None = has_frozen_balance
        """Заморожена ли часть баланса."""
        self.has_enabled_notifications: bool | None = has_enabled_notifications
        """Включены ли уведомления."""
        self.unread_chats_counter: int | None = unread_chats_counter
        """Количество непрочитанных чатов."""
        self.chosen_verified_card: "VerifiedCard | None" = None
        """Выбранная верифицированная карта для вывода (если есть)."""


class VerifiedCard:
    """Верифицированная банковская карта аккаунта (минимум полей с сайта)."""

    def __init__(self, id: str, card_first_six: str | None, card_last_four: str | None,
                 card_type: str | None, is_chosen: bool | None):
        self.id: str = id
        """ID карты."""
        self.card_first_six: str | None = card_first_six
        """Первые 6 цифр номера."""
        self.card_last_four: str | None = card_last_four
        """Последние 4 цифры номера."""
        self.card_type: str | None = card_type
        """Тип карты (Visa/Mir/…)."""
        self.is_chosen: bool | None = is_chosen
        """Выбрана ли карта как основная для вывода."""


class UserProfile:
    """Профиль пользователя (продавца/покупателя/собеседника в чате)."""

    def __init__(self, id: str, username: str | None, role: UserTypes | None, avatar_url: str | None,
                 is_online: bool | None, is_blocked: bool | None, rating: int | None, reviews_count: int | None,
                 support_chat_id: str | None, system_chat_id: str | None, created_at: str | None):
        self.id: str = id
        """ID пользователя."""
        self.username: str | None = username
        """Никнейм пользователя."""
        self.role: UserTypes | None = role
        """Роль пользователя."""
        self.avatar_url: str | None = avatar_url
        """URL аватара пользователя."""
        self.is_online: bool | None = is_online
        """В сети ли пользователь прямо сейчас."""
        self.is_blocked: bool | None = is_blocked
        """Заблокирован ли пользователь."""
        self.rating: int | None = rating
        """Рейтинг пользователя (0-5)."""
        self.reviews_count: int | None = reviews_count
        """Количество отзывов о пользователе."""
        self.support_chat_id: str | None = support_chat_id
        """ID чата поддержки пользователя."""
        self.system_chat_id: str | None = system_chat_id
        """ID системного чата пользователя."""
        self.created_at: str | None = created_at
        """Дата регистрации пользователя (ISO 8601)."""


class GameCategoryAgreement:
    """Соглашение, которое покупатель/продавец должен принять перед сделкой в категории."""

    def __init__(self, id: str, description: str | None, icontype: GameCategoryAgreementIconTypes | None,
                 sequence: int | None):
        self.id: str = id
        """ID соглашения."""
        self.description: str | None = description
        """Текст соглашения."""
        self.icontype: GameCategoryAgreementIconTypes | None = icontype
        """Тип иконки соглашения."""
        self.sequence: int | None = sequence
        """Порядковый номер соглашения (для сортировки на странице)."""


class GameCategoryProps:
    """Дополнительные требования (пропорции) категории игры."""

    def __init__(self, min_reviews: int | None, min_reviews_for_seller: int | None):
        self.min_reviews: int | None = min_reviews
        """Минимальное количество отзывов, необходимое для покупки в категории."""
        self.min_reviews_for_seller: int | None = min_reviews_for_seller
        """Минимальное количество отзывов, необходимое для продажи в категории."""


class GameCategoryOptionValueRange:
    """Диапазон допустимых значений опции категории (`valueRangeLimit`)."""

    def __init__(self, min: int | None, max: int | None):
        self.min: int | None = min
        """Минимальное допустимое значение."""
        self.max: int | None = max
        """Максимальное допустимое значение."""


class GameCategoryOption:
    """
    Опция (атрибут) категории игры — например, вариант подарка.

    При создании/обновлении лота выбранные опции передаются с проставленным `value`
    (см. `Account.create_item`/`Account.update_item`).
    """

    def __init__(self, id: str, group: str | None, label: str | None, type: GameCategoryOptionTypes | None,
                 field: str | None, value: str | None,
                 value_range_limit: "GameCategoryOptionValueRange | None"):
        self.id: str = id
        """ID опции."""
        self.group: str | None = group
        """Группа, к которой относится опция."""
        self.label: str | None = label
        """Отображаемое название опции."""
        self.type: GameCategoryOptionTypes | None = type
        """Тип опции (выбор из списка/переключатель)."""
        self.field: str | None = field
        """Имя поля, под которым опция передаётся в запросе на создание/обновление лота."""
        self.value: str | None = value
        """Значение опции (проставляется перед созданием/обновлением лота)."""
        self.value_range_limit: GameCategoryOptionValueRange | None = value_range_limit
        """Диапазон допустимых значений опции `{min, max}` (если применимо)."""


class GameCategoryDataField:
    """
    Поле с данными предмета в категории.

    Поля с `type=ITEM_DATA` заполняет продавец при создании лота, поля с `type=OBTAINING_DATA`
    заполняет покупатель при оформлении покупки (продавцу их заполнять и передавать не нужно).
    """

    def __init__(self, id: str, label: str | None, type: GameCategoryDataFieldTypes | None,
                 input_type: GameCategoryDataFieldInputTypes | None, copyable: bool | None, hidden: bool | None,
                 required: bool | None, value: str | None):
        self.id: str = id
        """ID поля."""
        self.label: str | None = label
        """Отображаемое название поля."""
        self.type: GameCategoryDataFieldTypes | None = type
        """Тип поля (данные предмета/данные для покупателя)."""
        self.input_type: GameCategoryDataFieldInputTypes | None = input_type
        """Тип элемента ввода значения."""
        self.copyable: bool | None = copyable
        """Разрешено ли копирование значения поля (в интерфейсе сайта)."""
        self.hidden: bool | None = hidden
        """Скрыто ли значение поля от посторонних (например, пароль)."""
        self.required: bool | None = required
        """Обязательно ли заполнение поля."""
        self.value: str | None = value
        """Значение поля (заполняется перед созданием/обновлением лота)."""


class GameCategoryObtainingType:
    """Способ получения предмета в категории (например, «Подарок» или «Автовыдача»)."""

    def __init__(self, id: str, name: str | None, description: str | None, game_category_id: str | None,
                 no_comment_from_buyer: bool | None, instruction_for_buyer: str | None,
                 instruction_for_seller: str | None, sequence: int | None, fee_multiplier: float | None,
                 agreements: list[GameCategoryAgreement], props: GameCategoryProps | None):
        self.id: str = id
        """ID способа получения."""
        self.name: str | None = name
        """Название способа получения."""
        self.description: str | None = description
        """Описание способа получения."""
        self.game_category_id: str | None = game_category_id
        """ID категории игры, к которой относится способ."""
        self.no_comment_from_buyer: bool | None = no_comment_from_buyer
        """Не требуется ли комментарий от покупателя при покупке этим способом."""
        self.instruction_for_buyer: str | None = instruction_for_buyer
        """Инструкция для покупателя."""
        self.instruction_for_seller: str | None = instruction_for_seller
        """Инструкция для продавца."""
        self.sequence: int | None = sequence
        """Порядковый номер способа (для сортировки на странице)."""
        self.fee_multiplier: float | None = fee_multiplier
        """Множитель комиссии сайта для этого способа получения."""
        self.agreements: list[GameCategoryAgreement] = agreements
        """Соглашения, привязанные к этому способу получения."""
        self.props: GameCategoryProps | None = props
        """Дополнительные требования (пропорции) способа получения."""


class GameCategory:
    """Категория внутри игры/приложения (например, «Аккаунты», «Валюта», «Услуги»)."""

    def __init__(self, id: str, slug: str | None, name: str | None, category_id: str | None, game_id: str | None,
                 obtaining: str | None, options: list[GameCategoryOption], props: GameCategoryProps | None,
                 no_comment_from_buyer: bool | None, instruction_for_buyer: str | None,
                 instruction_for_seller: str | None, use_custom_obtaining: bool | None,
                 auto_confirm_period: GameCategoryAutoConfirmPeriods | None, auto_moderation_mode: bool | None,
                 agreements: list[GameCategoryAgreement], fee_multiplier: float | None):
        self.id: str = id
        """ID категории."""
        self.slug: str | None = slug
        """Имя страницы категории (используется в URL)."""
        self.name: str | None = name
        """Название категории."""
        self.category_id: str | None = category_id
        """ID родительской категории (если это подкатегория)."""
        self.game_id: str | None = game_id
        """ID игры/приложения, которой принадлежит категория."""
        self.obtaining: str | None = obtaining
        """Тип получения товара в категории (сырое значение сайта)."""
        self.options: list[GameCategoryOption] = options
        """Доступные опции (атрибуты) лотов этой категории."""
        self.props: GameCategoryProps | None = props
        """Дополнительные требования (пропорции) категории."""
        self.no_comment_from_buyer: bool | None = no_comment_from_buyer
        """Не требуется ли комментарий от покупателя по умолчанию в категории."""
        self.instruction_for_buyer: str | None = instruction_for_buyer
        """Инструкция для покупателя по умолчанию в категории."""
        self.instruction_for_seller: str | None = instruction_for_seller
        """Инструкция для продавца по умолчанию в категории."""
        self.use_custom_obtaining: bool | None = use_custom_obtaining
        """Используется ли собственный (нестандартный) способ получения."""
        self.auto_confirm_period: GameCategoryAutoConfirmPeriods | None = auto_confirm_period
        """Период автоматического подтверждения сделки в категории."""
        self.auto_moderation_mode: bool | None = auto_moderation_mode
        """Включена ли автоматическая модерация лотов категории."""
        self.agreements: list[GameCategoryAgreement] = agreements
        """Соглашения категории."""
        self.fee_multiplier: float | None = fee_multiplier
        """Множитель комиссии сайта для лотов категории."""


class GameProfile:
    """Краткий профиль игры/приложения (используется внутри лотов/сделок)."""

    def __init__(self, id: str, slug: str | None, name: str | None, type: GameTypes | None, logo: FileObject | None):
        self.id: str = id
        """ID игры/приложения."""
        self.slug: str | None = slug
        """Имя страницы игры/приложения (используется в URL)."""
        self.name: str | None = name
        """Название игры/приложения."""
        self.type: GameTypes | None = type
        """Тип: игра или приложение."""
        self.logo: FileObject | None = logo
        """Логотип игры/приложения."""


class Game:
    """Полная информация об игре/приложении, включая список категорий."""

    def __init__(self, id: str, slug: str | None, name: str | None, type: GameTypes | None,
                 logo: FileObject | None, banner: FileObject | None, categories: list[GameCategory],
                 created_at: str | None):
        self.id: str = id
        """ID игры/приложения."""
        self.slug: str | None = slug
        """Имя страницы игры/приложения (используется в URL)."""
        self.name: str | None = name
        """Название игры/приложения."""
        self.type: GameTypes | None = type
        """Тип: игра или приложение."""
        self.logo: FileObject | None = logo
        """Логотип игры/приложения."""
        self.banner: FileObject | None = banner
        """Баннер игры/приложения."""
        self.categories: list[GameCategory] = categories
        """Список категорий игры/приложения."""
        self.created_at: str | None = created_at
        """Дата добавления игры/приложения на сайт."""


class ItemPriorityStatusPriceRange:
    """Диапазон цен предмета, для которого действует статус приоритета."""

    def __init__(self, min: int | None, max: int | None):
        self.min: int | None = min
        """Минимальная цена предмета (в рублях)."""
        self.max: int | None = max
        """Максимальная цена предмета (в рублях)."""


class ItemPriorityStatus:
    """
    Статус приоритета лота (уровень поднятия в списке).

    Получается через `Account.get_item_priority_statuses(item_id, price)` и передаётся в
    `Account.publish_item()`/`Account.increase_item_priority_status()`.
    """

    def __init__(self, id: str, price: int | None, name: str | None, type: PriorityTypes | None,
                 period: int | None, price_range: ItemPriorityStatusPriceRange | None):
        self.id: str = id
        """ID статуса приоритета."""
        self.price: int | None = price
        """Стоимость статуса (в рублях)."""
        self.name: str | None = name
        """Название статуса."""
        self.type: PriorityTypes | None = type
        """Тип приоритета (стандартный/премиум)."""
        self.period: int | None = period
        """Длительность действия статуса (в днях)."""
        self.price_range: ItemPriorityStatusPriceRange | None = price_range
        """Диапазон цен предмета, для которого действует этот статус."""


class ItemLog:
    """Запись в истории действий с лотом (например, «оплачен», «отправлен»)."""

    def __init__(self, id: str, event: ItemLogEvents | None, created_at: str | None, user: UserProfile | None):
        self.id: str = id
        """ID записи лога."""
        self.event: ItemLogEvents | None = event
        """Тип события в логе."""
        self.created_at: str | None = created_at
        """Дата события (ISO 8601)."""
        self.user: UserProfile | None = user
        """Пользователь, совершивший действие."""


class ItemDealTransaction:
    """
    Лёгкий "снимок" транзакции, привязанной к сделке или к оплате приоритета лота.

    Это не полноценная финансовая подсистема (см. README, раздел "Бэклог / Фаза 2") — только
    минимум полей, чтобы понимать, чем и когда была оплачена конкретная сделка/поднятие лота.
    """

    def __init__(self, id: str, operation: TransactionOperations | None, direction: TransactionDirections | None,
                 provider_id: TransactionProviderIds | None, status: TransactionStatuses | None,
                 status_description: str | None, status_expiration_date: str | None, value: int | None,
                 created_at: str | None, payment_method_id: str | None):
        self.id: str = id
        """ID транзакции."""
        self.operation: TransactionOperations | None = operation
        """Тип операции."""
        self.direction: TransactionDirections | None = direction
        """Направление движения средств."""
        self.provider_id: TransactionProviderIds | None = provider_id
        """ID провайдера транзакции (например, `LOCAL` — оплата с баланса сайта)."""
        self.status: TransactionStatuses | None = status
        """Статус обработки транзакции."""
        self.status_description: str | None = status_description
        """Описание статуса транзакции."""
        self.status_expiration_date: str | None = status_expiration_date
        """Дата истечения текущего статуса транзакции."""
        self.value: int | None = value
        """Сумма транзакции."""
        self.created_at: str | None = created_at
        """Дата создания транзакции (ISO 8601)."""
        self.payment_method_id: str | None = payment_method_id
        """ID способа оплаты, если применимо."""


class MessageTemplate:
    """
    Шаблонное сообщение.

    Получается через `Account.get_message_templates()` — используется, например, как список
    доступных причин при заявке проблемы в сделке (`problem_type_id` в `Account.report_deal_problem()`).
    """

    def __init__(self, id: str, type: MessageTemplateTypes | None, title: str | None, text: str | None,
                 sequence: int | None, created_at: str | None, group: str | None):
        self.id: str = id
        """ID шаблонного сообщения."""
        self.type: MessageTemplateTypes | None = type
        """Тип шаблонного сообщения."""
        self.title: str | None = title
        """Заголовок шаблонного сообщения."""
        self.text: str | None = text
        """Текст шаблонного сообщения."""
        self.sequence: int | None = sequence
        """Порядковый номер шаблона (для сортировки на странице)."""
        self.created_at: str | None = created_at
        """Дата создания шаблона."""
        self.group: str | None = group
        """Группа, к которой относится шаблон (если применимо)."""


class Moderator:
    """Профиль модератора (заготовка — Playerok отдаёт по модераторам минимум данных)."""

    def __init__(self, id: str | None = None, username: str | None = None):
        self.id: str | None = id
        """ID модератора."""
        self.username: str | None = username
        """Никнейм модератора."""


class Item:
    """
    Лот (предмет) — версия для чужих/общих запросов (например, `ForeignItem` на сайте).

    Для лотов своего аккаунта с полным набором служебных полей (статистика просмотров, историю цены
    и т.п.) используйте `MyItem`, который возвращает `Account.get_item()`/`Account.get_my_items()`.
    """

    def __init__(self, id: str, slug: str | None, name: str | None, description: str | None,
                 obtaining_type: GameCategoryObtainingType | None, price: int | None, raw_price: int | None,
                 priority: PriorityTypes | None, priority_position: int | None, attachments: list[FileObject],
                 attributes: dict | None, category: GameCategory | None, comment: str | None,
                 data_fields: list[GameCategoryDataField], fee_multiplier: float | None, game: GameProfile | None,
                 seller_type: UserTypes | None, status: ItemStatuses | None, user: UserProfile | None):
        self.id: str = id
        """ID лота."""
        self.slug: str | None = slug
        """Имя страницы лота (используется в URL)."""
        self.name: str | None = name
        """Название лота."""
        self.description: str | None = description
        """Описание лота."""
        self.obtaining_type: GameCategoryObtainingType | None = obtaining_type
        """Способ получения товара."""
        self.price: int | None = price
        """Итоговая цена лота (с учётом скидки, если есть)."""
        self.raw_price: int | None = raw_price
        """Цена лота без учёта скидки."""
        self.priority: PriorityTypes | None = priority
        """Текущий статус приоритета лота."""
        self.priority_position: int | None = priority_position
        """Позиция лота в списке приоритета."""
        self.attachments: list[FileObject] = attachments
        """Файлы-приложения (изображения) лота."""
        self.attributes: dict | None = attributes
        """Атрибуты (выбранные опции) лота."""
        self.category: GameCategory | None = category
        """Категория игры, к которой относится лот."""
        self.comment: str | None = comment
        """Комментарий продавца к лоту."""
        self.data_fields: list[GameCategoryDataField] = data_fields
        """Поля с данными лота."""
        self.fee_multiplier: float | None = fee_multiplier
        """Множитель комиссии сайта для этого лота."""
        self.game: GameProfile | None = game
        """Игра/приложение, к которой относится лот."""
        self.seller_type: UserTypes | None = seller_type
        """Тип (роль) продавца лота."""
        self.status: ItemStatuses | None = status
        """Статус лота."""
        self.user: UserProfile | None = user
        """Профиль продавца лота."""


class MyItem:
    """Лот (предмет) своего аккаунта — полный набор служебных полей."""

    def __init__(self, id: str, slug: str | None, name: str | None, description: str | None,
                 obtaining_type: GameCategoryObtainingType | None, price: int | None, prev_price: int | None,
                 raw_price: int | None, priority_position: int | None, attachments: list[FileObject],
                 attributes: dict | None, buyer: UserProfile | None, category: GameCategory | None,
                 comment: str | None, data_fields: list[GameCategoryDataField], fee_multiplier: float | None,
                 prev_fee_multiplier: float | None, seller_notified_about_fee_change: bool | None,
                 game: GameProfile | None, seller_type: UserTypes | None, status: ItemStatuses | None,
                 user: UserProfile | None, priority: PriorityTypes | None, priority_price: int | None,
                 sequence: int | None, status_expiration_date: str | None, status_description: str | None,
                 status_payment: ItemDealTransaction | None, views_counter: int | None, is_editable: bool | None,
                 approval_date: str | None, deleted_at: str | None, updated_at: str | None, created_at: str | None):
        self.id: str = id
        """ID лота."""
        self.slug: str | None = slug
        """Имя страницы лота (используется в URL)."""
        self.name: str | None = name
        """Название лота."""
        self.description: str | None = description
        """Описание лота."""
        self.status: ItemStatuses | None = status
        """Статус лота (черновик/на проверке/активен/продан и т.п.)."""
        self.obtaining_type: GameCategoryObtainingType | None = obtaining_type
        """Способ получения товара."""
        self.price: int | None = price
        """Текущая цена лота."""
        self.prev_price: int | None = prev_price
        """Цена лота до последнего изменения."""
        self.raw_price: int | None = raw_price
        """Цена лота без учёта скидки."""
        self.priority_position: int | None = priority_position
        """Позиция лота в списке приоритета."""
        self.attachments: list[FileObject] = attachments
        """Файлы-приложения (изображения) лота."""
        self.attributes: dict | None = attributes
        """Атрибуты (выбранные опции) лота."""
        self.category: GameCategory | None = category
        """Категория игры, к которой относится лот."""
        self.comment: str | None = comment
        """Комментарий продавца к лоту."""
        self.data_fields: list[GameCategoryDataField] = data_fields
        """Поля с данными лота."""
        self.fee_multiplier: float | None = fee_multiplier
        """Текущий множитель комиссии сайта для этого лота."""
        self.prev_fee_multiplier: float | None = prev_fee_multiplier
        """Множитель комиссии до последнего изменения."""
        self.seller_notified_about_fee_change: bool | None = seller_notified_about_fee_change
        """Оповещён ли продавец об изменении комиссии."""
        self.game: GameProfile | None = game
        """Игра/приложение, к которой относится лот."""
        self.seller_type: UserTypes | None = seller_type
        """Тип (роль) продавца лота."""
        self.user: UserProfile | None = user
        """Профиль продавца лота (владельца)."""
        self.buyer: UserProfile | None = buyer
        """Профиль покупателя (если лот продан)."""
        self.priority: PriorityTypes | None = priority
        """Текущий статус приоритета лота."""
        self.priority_price: int | None = priority_price
        """Стоимость текущего статуса приоритета."""
        self.sequence: int | None = sequence
        """Позиция лота в общей таблице лотов пользователя."""
        self.status_expiration_date: str | None = status_expiration_date
        """Дата истечения текущего статуса приоритета."""
        self.status_description: str | None = status_description
        """Описание текущего статуса приоритета."""
        self.status_payment: ItemDealTransaction | None = status_payment
        """Транзакция оплаты текущего статуса приоритета (если платный)."""
        self.views_counter: int | None = views_counter
        """Количество просмотров лота."""
        self.is_editable: bool | None = is_editable
        """Можно ли сейчас редактировать лот."""
        self.approval_date: str | None = approval_date
        """Дата публикации (принятия модерацией) лота."""
        self.deleted_at: str | None = deleted_at
        """Дата удаления лота (если удалён)."""
        self.updated_at: str | None = updated_at
        """Дата последнего обновления лота."""
        self.created_at: str | None = created_at
        """Дата создания лота."""
        self.deals_counter: int | None = None
        """Счётчик сделок по лоту (если сервер вернул поле)."""
        self.may_be_published: bool | None = None
        """Можно ли опубликовать лот сейчас."""
        self.post_moderation_checked_at: str | None = None
        """Дата пост-модерации (ISO 8601)."""
        self.is_automated: bool | None = None
        """Автоматизированная выдача у лота."""
        self.multiple: bool | None = None
        """Множественный (складской) лот."""


class ItemProfile:
    """Краткий профиль лота — используется в списках лотов (`Account.get_items`/`get_my_items`)."""

    def __init__(self, id: str, slug: str | None, priority: PriorityTypes | None, status: ItemStatuses | None,
                 name: str | None, price: int | None, raw_price: int | None, seller_type: UserTypes | None,
                 attachment: FileObject | None, user: UserProfile | None, approval_date: str | None,
                 priority_position: int | None, views_counter: int | None, fee_multiplier: float | None,
                 created_at: str | None):
        self.id: str = id
        """ID лота."""
        self.slug: str | None = slug
        """Имя страницы лота (используется в URL)."""
        self.priority: PriorityTypes | None = priority
        """Статус приоритета лота."""
        self.status: ItemStatuses | None = status
        """Статус лота."""
        self.name: str | None = name
        """Название лота."""
        self.price: int | None = price
        """Цена лота."""
        self.raw_price: int | None = raw_price
        """Цена лота без учёта скидки."""
        self.seller_type: UserTypes | None = seller_type
        """Тип (роль) продавца лота."""
        self.attachment: FileObject | None = attachment
        """Главное изображение лота (для превью в списке)."""
        self.user: UserProfile | None = user
        """Профиль продавца лота."""
        self.approval_date: str | None = approval_date
        """Дата публикации лота."""
        self.priority_position: int | None = priority_position
        """Позиция лота в списке приоритета."""
        self.views_counter: int | None = views_counter
        """Количество просмотров лота."""
        self.fee_multiplier: float | None = fee_multiplier
        """Множитель комиссии сайта для этого лота."""
        self.created_at: str | None = created_at
        """Дата создания лота."""


class Review:
    """Отзыв о продавце после совершённой сделки."""

    def __init__(self, id: str, status: ReviewStatuses | None, text: str | None, rating: int | None,
                 created_at: str | None, updated_at: str | None, deal: "ItemDeal | None", creator: UserProfile | None,
                 moderator: Moderator | None, user: UserProfile | None):
        self.id: str = id
        """ID отзыва."""
        self.status: ReviewStatuses | None = status
        """Статус отзыва (активен/удалён)."""
        self.text: str | None = text
        """Текст отзыва."""
        self.rating: int | None = rating
        """Оценка отзыва (1-5)."""
        self.created_at: str | None = created_at
        """Дата создания отзыва."""
        self.updated_at: str | None = updated_at
        """Дата последнего изменения отзыва."""
        self.deal: "ItemDeal | None" = deal
        """Сделка, к которой относится отзыв."""
        self.creator: UserProfile | None = creator
        """Профиль автора отзыва (покупателя)."""
        self.moderator: Moderator | None = moderator
        """Модератор, обработавший отзыв (если применимо)."""
        self.user: UserProfile | None = user
        """Профиль продавца, к которому относится отзыв."""


class ItemDealProps:
    """Дополнительные параметры сделки."""

    def __init__(self, auto_confirm_period: int | None):
        self.auto_confirm_period: int | None = auto_confirm_period
        """Срок автоматического подтверждения сделки (в днях)."""


class ItemDeal:
    """
    Сделка (заказ) с лотом.

    Помимо "сырого" статуса (`raw_status`), содержит дружелюбный `status: DealStatuses`
    (аналог `FunPayAPI` `OrderStatuses`) — см. `common.enums.DealStatuses`.
    """

    def __init__(self, id: str, status: DealStatuses | None, raw_status: ItemDealStatuses | None,
                 completed_automatically: bool, status_expiration_date: str | None, status_description: str | None,
                 direction: ItemDealDirections | None, obtaining: str | None, has_problem: bool | None,
                 report_problem_enabled: bool | None, completed_user: UserProfile | None,
                 props: ItemDealProps | None, previous_status: ItemDealStatuses | None, completed_at: str | None,
                 created_at: str | None, logs: list[ItemLog], transaction: ItemDealTransaction | None,
                 user: UserProfile | None, chat: "Chat | None", item: Item | None, review: Review | None,
                 obtaining_fields: list[GameCategoryDataField], comment_from_buyer: str | None):
        self.id: str = id
        """ID сделки."""
        self.status: DealStatuses | None = status
        """Дружелюбный статус сделки (см. `common.enums.DealStatuses`)."""
        self.raw_status: ItemDealStatuses | None = raw_status
        """"Сырой" статус сделки — как он приходит от Playerok."""
        self.completed_automatically: bool = completed_automatically
        """Была ли сделка подтверждена автоматически (истёк срок ожидания ответа покупателя)."""
        self.status_expiration_date: str | None = status_expiration_date
        """Дата истечения текущего статуса."""
        self.status_description: str | None = status_description
        """Описание текущего статуса сделки."""
        self.direction: ItemDealDirections | None = direction
        """Направление сделки (покупка/продажа) относительно вашего аккаунта."""
        self.obtaining: str | None = obtaining
        """Способ получения товара по сделке (сырое значение)."""
        self.has_problem: bool | None = has_problem
        """Есть ли заявленная проблема по сделке."""
        self.report_problem_enabled: bool | None = report_problem_enabled
        """Доступна ли сейчас возможность заявить проблему по сделке."""
        self.completed_user: UserProfile | None = completed_user
        """Профиль пользователя, подтвердившего сделку."""
        self.props: ItemDealProps | None = props
        """Дополнительные параметры сделки."""
        self.previous_status: ItemDealStatuses | None = previous_status
        """Предыдущий "сырой" статус сделки."""
        self.completed_at: str | None = completed_at
        """Дата подтверждения сделки (если подтверждена)."""
        self.created_at: str | None = created_at
        """Дата создания сделки."""
        self.logs: list[ItemLog] = logs
        """История действий по сделке."""
        self.transaction: ItemDealTransaction | None = transaction
        """Транзакция оплаты сделки."""
        self.user: UserProfile | None = user
        """Профиль второй стороны сделки (покупателя или продавца — смотря на `direction`)."""
        self.chat: "Chat | None" = chat
        """Чат, связанный со сделкой (обычно приходит только с `id`)."""
        self.item: Item | None = item
        """Лот, с которым связана сделка."""
        self.review: Review | None = review
        """Отзыв по сделке (если оставлен)."""
        self.obtaining_fields: list[GameCategoryDataField] = obtaining_fields
        """Заполненные покупателем поля получения товара."""
        self.comment_from_buyer: str | None = comment_from_buyer
        """Комментарий покупателя при оформлении сделки."""


class ChatMessageButton:
    """Кнопка в системном сообщении чата (например, ссылка на розыгрыш)."""

    def __init__(self, type: ChatMessageButtonTypes | None, url: str | None, text: str | None):
        self.type: ChatMessageButtonTypes | None = type
        """Тип кнопки."""
        self.url: str | None = url
        """URL, на который ведёт кнопка (если применимо)."""
        self.text: str | None = text
        """Текст на кнопке."""


class ChatMessage:
    """Сообщение в чате."""

    def __init__(self, id: str, text: str | None, created_at: str | None, deleted_at: str | None,
                 is_read: bool | None, is_suspicious: bool | None, is_bulk_messaging: bool | None,
                 game: GameProfile | None, images: list[FileObject], user: UserProfile | None,
                 deal: ItemDeal | None, item: Item | None, moderator: Moderator | None,
                 event_by_user: UserProfile | None, event_to_user: UserProfile | None,
                 is_auto_response: bool | None, event: ChatMessageEvents | None, buttons: list[ChatMessageButton],
                 file: FileObject | None = None):
        self.id: str = id
        """ID сообщения."""
        self.text: str | None = text
        """Текст сообщения (может быть системным маркером вида `{{ITEM_PAID}}`)."""
        self.file: FileObject | None = file
        """Файл-вложение сообщения (например, изображение из WS-кадра `lastMessage.file`)."""
        self.created_at: str | None = created_at
        """Дата отправки сообщения."""
        self.deleted_at: str | None = deleted_at
        """Дата удаления сообщения (если удалено)."""
        self.is_read: bool | None = is_read
        """Прочитано ли сообщение."""
        self.is_suspicious: bool | None = is_suspicious
        """Помечено ли сообщение как подозрительное (антифрод)."""
        self.is_bulk_messaging: bool | None = is_bulk_messaging
        """Является ли сообщение частью массовой рассылки."""
        self.game: GameProfile | None = game
        """Игра, к которой относится сообщение (если применимо)."""
        self.images: list[FileObject] = images
        """Изображения, прикреплённые к сообщению."""
        self.user: UserProfile | None = user
        """Отправитель сообщения."""
        self.deal: ItemDeal | None = deal
        """Сделка, к которой относится сообщение (если применимо)."""
        self.item: Item | None = item
        """Лот, к которому относится сообщение (обычно связь идёт через `deal`)."""
        self.moderator: Moderator | None = moderator
        """Модератор, если сообщение отправлено от лица модерации."""
        self.event_by_user: UserProfile | None = event_by_user
        """Пользователь-инициатор системного события сообщения."""
        self.event_to_user: UserProfile | None = event_to_user
        """Пользователь-получатель системного события сообщения."""
        self.is_auto_response: bool | None = is_auto_response
        """Является ли сообщение автоматическим ответом."""
        self.event: ChatMessageEvents | None = event
        """Тип системного события сообщения (если применимо)."""
        self.buttons: list[ChatMessageButton] = buttons
        """Кнопки, прикреплённые к сообщению."""


class Chat:
    """Чат (диалог с пользователем, чат поддержки или уведомлений)."""

    def __init__(self, id: str, type: ChatTypes | None, status: ChatStatuses | None,
                 unread_messages_counter: int | None, bookmarked: bool | None, is_texting_allowed: bool | None,
                 owner: UserProfile | None, deals: list[ItemDeal], started_at: str | None, finished_at: str | None,
                 last_message: ChatMessage | None, users: list[UserProfile]):
        self.id: str = id
        """ID чата."""
        self.type: ChatTypes | None = type
        """Тип чата."""
        self.status: ChatStatuses | None = status
        """Статус чата."""
        self.unread_messages_counter: int | None = unread_messages_counter
        """Количество непрочитанных сообщений в чате."""
        self.bookmarked: bool | None = bookmarked
        """Добавлен ли чат в закладки."""
        self.is_texting_allowed: bool | None = is_texting_allowed
        """Разрешено ли отправлять сообщения в этот чат."""
        self.owner: UserProfile | None = owner
        """Владелец чата (заполняется только для чатов с ботом/поддержкой)."""
        self.deals: list[ItemDeal] = deals
        """Активные сделки, связанные с чатом."""
        self.started_at: str | None = started_at
        """Дата начала переписки."""
        self.finished_at: str | None = finished_at
        """Дата завершения переписки (если завершена)."""
        self.last_message: ChatMessage | None = last_message
        """Последнее сообщение в чате."""
        self.users: list[UserProfile] = users
        """Участники чата."""


class TemporaryAttachmentUploadOutput:
    """Результат загрузки изображения во временное хранилище (перед отправкой сообщения с картинкой)."""

    def __init__(self, id: str, url: str | None, chat_id: str | None, client_attachment_id: str | None,
                 expires_at: str | None):
        self.id: str = id
        """ID временного вложения (используется при отправке сообщения)."""
        self.url: str | None = url
        """URL загруженного изображения."""
        self.chat_id: str | None = chat_id
        """ID чата, для которого загружено изображение."""
        self.client_attachment_id: str | None = client_attachment_id
        """ID вложения на стороне клиента (сгенерированный при загрузке)."""
        self.expires_at: str | None = expires_at
        """Дата, до которой временное вложение действительно."""


# ---------------------------------------------------------------------------
# Классы страниц (используются везде, где GraphQL API отдаёт список с пагинацией по курсору)
# ---------------------------------------------------------------------------

class PageInfo:
    """Информация о текущей странице курсорной пагинации GraphQL."""

    def __init__(self, start_cursor: str | None, end_cursor: str | None, has_previous_page: bool | None,
                 has_next_page: bool | None):
        self.start_cursor: str | None = start_cursor
        """Курсор начала страницы."""
        self.end_cursor: str | None = end_cursor
        """Курсор конца страницы (используется как `after_cursor` для следующего запроса)."""
        self.has_previous_page: bool | None = has_previous_page
        """Есть ли предыдущая страница."""
        self.has_next_page: bool | None = has_next_page
        """Есть ли следующая страница."""


class ChatList:
    """Страница списка чатов."""

    def __init__(self, chats: list[Chat], page_info: PageInfo | None, total_count: int | None):
        self.chats: list[Chat] = chats
        """Чаты текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество чатов (по всем страницам)."""


class ChatMessageList:
    """Страница списка сообщений чата."""

    def __init__(self, messages: list[ChatMessage], page_info: PageInfo | None, total_count: int | None):
        self.messages: list[ChatMessage] = messages
        """Сообщения текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество сообщений в чате."""


class ItemDealList:
    """Страница списка сделок."""

    def __init__(self, deals: list[ItemDeal], page_info: PageInfo | None, total_count: int | None):
        self.deals: list[ItemDeal] = deals
        """Сделки текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество сделок (по всем страницам)."""


class GameList:
    """Страница списка игр/приложений."""

    def __init__(self, games: list[Game], page_info: PageInfo | None, total_count: int | None):
        self.games: list[Game] = games
        """Игры/приложения текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество игр/приложений."""


class GameCategoryObtainingTypeList:
    """Страница списка способов получения предмета в категории."""

    def __init__(self, obtaining_types: list[GameCategoryObtainingType], page_info: PageInfo | None,
                 total_count: int | None):
        self.obtaining_types: list[GameCategoryObtainingType] = obtaining_types
        """Способы получения на текущей странице."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество способов получения."""


class GameCategoryDataFieldList:
    """Страница списка полей с данными категории."""

    def __init__(self, data_fields: list[GameCategoryDataField], page_info: PageInfo | None,
                 total_count: int | None):
        self.data_fields: list[GameCategoryDataField] = data_fields
        """Поля с данными на текущей странице."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество полей с данными."""


class ItemProfileList:
    """Страница списка кратких профилей лотов."""

    def __init__(self, items: list[ItemProfile], page_info: PageInfo | None, total_count: int | None):
        self.items: list[ItemProfile] = items
        """Лоты текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество лотов."""


class ReviewList:
    """Страница списка отзывов."""

    def __init__(self, reviews: list[Review], page_info: PageInfo | None, total_count: int | None):
        self.reviews: list[Review] = reviews
        """Отзывы текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество отзывов."""


class MessageTemplateList:
    """Страница списка шаблонных сообщений."""

    def __init__(self, message_templates: list[MessageTemplate], page_info: PageInfo | None,
                 total_count: int | None):
        self.message_templates: list[MessageTemplate] = message_templates
        """Шаблонные сообщения текущей страницы."""
        self.page_info: PageInfo | None = page_info
        """Информация о странице."""
        self.total_count: int | None = total_count
        """Общее количество шаблонных сообщений."""


class TransactionProvider:
    """Провайдер финансовой операции (пополнение/вывод)."""

    def __init__(self, id: str | None, name: str | None, fee: float | None,
                 min_fee_amount: int | None, description: str | None):
        self.id: str | None = id
        self.name: str | None = name
        self.fee: float | None = fee
        self.min_fee_amount: int | None = min_fee_amount
        self.description: str | None = description


class Transaction:
    """Финансовая транзакция аккаунта (пополнение, вывод, оплата лота и т.п.)."""

    def __init__(self, id: str, operation: TransactionOperations | None,
                 direction: TransactionDirections | None, provider_id: str | None,
                 provider: TransactionProvider | None, status: TransactionStatuses | None,
                 status_description: str | None, status_expiration_date: str | None,
                 value: int | None, fee: int | None, created_at: str | None,
                 props: dict | None, user: UserProfile | None = None,
                 creator: UserProfile | None = None):
        self.id: str = id
        self.operation: TransactionOperations | None = operation
        self.direction: TransactionDirections | None = direction
        self.provider_id: str | None = provider_id
        self.provider: TransactionProvider | None = provider
        self.status: TransactionStatuses | None = status
        self.status_description: str | None = status_description
        self.status_expiration_date: str | None = status_expiration_date
        self.value: int | None = value
        self.fee: int | None = fee
        self.created_at: str | None = created_at
        self.props: dict | None = props
        """Сырые props транзакции (реквизиты и т.п.)."""
        self.user: UserProfile | None = user
        self.creator: UserProfile | None = creator


class TransactionList:
    """Страница списка транзакций."""

    def __init__(self, transactions: list[Transaction], page_info: PageInfo | None,
                 total_count: int | None):
        self.transactions: list[Transaction] = transactions
        self.page_info: PageInfo | None = page_info
        self.total_count: int | None = total_count


class Payout:
    """Выплата (payout) с аккаунта."""

    def __init__(self, id: str, status: str | None, completed_at: str | None, to: str | None,
                 ip_address: str | None, value: int | None, remote_id: str | None,
                 payment_gateway: str | None, provider_id: str | None, created_at: str | None,
                 creator: UserProfile | None = None):
        self.id: str = id
        self.status: str | None = status
        self.completed_at: str | None = completed_at
        self.to: str | None = to
        self.ip_address: str | None = ip_address
        self.value: int | None = value
        self.remote_id: str | None = remote_id
        self.payment_gateway: str | None = payment_gateway
        self.provider_id: str | None = provider_id
        self.created_at: str | None = created_at
        self.creator: UserProfile | None = creator


class PayoutList:
    """Страница списка выплат."""

    def __init__(self, payouts: list[Payout], page_info: PageInfo | None, total_count: int | None):
        self.payouts: list[Payout] = payouts
        self.page_info: PageInfo | None = page_info
        self.total_count: int | None = total_count


class VerifiedCardList:
    """Страница списка верифицированных карт."""

    def __init__(self, cards: list[VerifiedCard], page_info: PageInfo | None, total_count: int | None):
        self.cards: list[VerifiedCard] = cards
        self.page_info: PageInfo | None = page_info
        self.total_count: int | None = total_count


class ChatBulkMessage:
    """Массовая рассылка в чаты (createChatBulkMessage)."""

    def __init__(self, id: str, text: str | None, created_at: str | None, started_at: str | None,
                 finished_at: str | None, send_after: str | None, queue_status: str | None,
                 stats: dict | None = None):
        self.id: str = id
        self.text: str | None = text
        self.created_at: str | None = created_at
        self.started_at: str | None = started_at
        self.finished_at: str | None = finished_at
        self.send_after: str | None = send_after
        self.queue_status: str | None = queue_status
        self.stats: dict | None = stats
