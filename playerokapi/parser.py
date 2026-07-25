"""
Сборка объектов `types.py` из "сырых" GraphQL dict-ответов Playerok.

Все функции терпимы к отсутствующим полям (используют `dict.get`) и возвращают `None`,
если на вход передан пустой/отсутствующий `dict` — это упрощает работу с опциональными
вложенными объектами GraphQL-ответа.
"""
from __future__ import annotations

from . import types
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

# "Сырые" статусы сделки, которые считаются завершёнными автоматически (без действия покупателя).
_AUTOCONFIRMED_STATUSES = {"CONFIRMED_AUTOMATICALLY"}

# Соответствие "сырых" статусов сделки Playerok дружелюбным статусам `DealStatuses`.
_DEAL_STATUS_MAP = {
    "PAID": DealStatuses.PAID,
    "PENDING": DealStatuses.PENDING,
    "SENT": DealStatuses.SENT,
    "CONFIRMED": DealStatuses.COMPLETED,
    "CONFIRMED_AUTOMATICALLY": DealStatuses.COMPLETED,
    "ROLLED_BACK": DealStatuses.CANCELED,
}


def file(data: dict | None) -> types.FileObject | None:
    """Собирает `FileObject` из "сырых" данных файла."""
    if not data:
        return None
    return types.FileObject(
        id=data.get("id"),
        url=data.get("url"),
        filename=data.get("filename"),
        mime=data.get("mime"),
    )


def account_balance(data: dict | None) -> types.AccountBalance | None:
    """Собирает `AccountBalance` из "сырых" данных баланса."""
    if not data:
        return None
    return types.AccountBalance(
        id=data.get("id"),
        value=data.get("value"),
        frozen=data.get("frozen"),
        available=data.get("available"),
        withdrawable=data.get("withdrawable"),
        pending_income=data.get("pendingIncome"),
    )


def account_items_stats(data: dict | None) -> types.AccountItemsStats | None:
    """Собирает `AccountItemsStats`."""
    if not data:
        return None
    return types.AccountItemsStats(total=data.get("total"), finished=data.get("finished"))


def account_incoming_deals_stats(data: dict | None) -> types.AccountIncomingDealsStats | None:
    """Собирает `AccountIncomingDealsStats`."""
    if not data:
        return None
    return types.AccountIncomingDealsStats(total=data.get("total"), finished=data.get("finished"))


def account_outgoing_deals_stats(data: dict | None) -> types.AccountOutgoingDealsStats | None:
    """Собирает `AccountOutgoingDealsStats`."""
    if not data:
        return None
    return types.AccountOutgoingDealsStats(total=data.get("total"), finished=data.get("finished"))


def account_deals_stats(data: dict | None) -> types.AccountDealsStats | None:
    """Собирает `AccountDealsStats`."""
    if not data:
        return None
    return types.AccountDealsStats(
        incoming=account_incoming_deals_stats(data.get("incoming")),
        outgoing=account_outgoing_deals_stats(data.get("outgoing")),
    )


def account_stats(data: dict | None) -> types.AccountStats | None:
    """Собирает `AccountStats`."""
    if not data:
        return None
    return types.AccountStats(
        items=account_items_stats(data.get("items")),
        deals=account_deals_stats(data.get("deals")),
    )


def account_profile(data: dict | None) -> types.AccountProfile | None:
    """Собирает `AccountProfile` из ответа запроса `user` для собственного аккаунта."""
    if not data:
        return None
    profile_data: dict = data.get("profile") or {}
    profile = types.AccountProfile(
        id=data.get("id"),
        username=profile_data.get("username") or data.get("username"),
        email=data.get("email"),
        balance=account_balance(data.get("balance")),
        stats=account_stats(data.get("stats")),
        role=UserTypes.__members__.get(data.get("role")),
        avatar_url=profile_data.get("avatarURL"),
        is_online=profile_data.get("isOnline"),
        is_blocked=data.get("isBlocked"),
        is_blocked_for=data.get("isBlockedFor"),
        is_verified=data.get("isVerified"),
        rating=profile_data.get("rating"),
        reviews_count=profile_data.get("testimonialCounter"),
        # В ответе `viewer`/`user` эти поля лежат в корне узла (фрагмент Viewer on User);
        # вложенный profile оставлен как fallback для других форм ответа.
        created_at=data.get("createdAt") or profile_data.get("createdAt"),
        support_chat_id=data.get("supportChatId") or profile_data.get("supportChatId"),
        system_chat_id=data.get("systemChatId") or profile_data.get("systemChatId"),
        has_frozen_balance=data.get("hasFrozenBalance"),
        has_enabled_notifications=data.get("hasEnabledNotifications"),
        unread_chats_counter=data.get("unreadChatsCounter"),
    )
    profile.chosen_verified_card = verified_card(data.get("chosenVerifiedCard"))
    return profile


def verified_card(data: dict | None) -> types.VerifiedCard | None:
    """Собирает `VerifiedCard`."""
    if not data or not data.get("id"):
        return None
    return types.VerifiedCard(
        id=data["id"],
        card_first_six=data.get("cardFirstSix"),
        card_last_four=data.get("cardLastFour"),
        card_type=data.get("cardType"),
        is_chosen=data.get("isChosen"),
    )


def user_profile(data: dict | None) -> types.UserProfile | None:
    """Собирает `UserProfile`."""
    if not data:
        return None
    return types.UserProfile(
        id=data.get("id"),
        username=data.get("username"),
        role=UserTypes.__members__.get(data.get("role")),
        avatar_url=data.get("avatarURL"),
        is_online=data.get("isOnline"),
        is_blocked=data.get("isBlocked"),
        rating=data.get("rating"),
        reviews_count=data.get("testimonialCounter"),
        support_chat_id=data.get("supportChatId"),
        system_chat_id=data.get("systemChatId"),
        created_at=data.get("createdAt"),
    )


def message_template(data: dict | None) -> types.MessageTemplate | None:
    """Собирает `MessageTemplate`."""
    if not data:
        return None
    return types.MessageTemplate(
        id=data.get("id"),
        type=MessageTemplateTypes.__members__.get(data.get("type")),
        title=data.get("title"),
        text=data.get("text"),
        sequence=data.get("sequence"),
        created_at=data.get("createdAt"),
        group=data.get("group"),
    )


def moderator(data: dict | None) -> types.Moderator | None:
    """Собирает `Moderator`."""
    if not data:
        return None
    return types.Moderator(id=data.get("id"), username=data.get("username"))


def game_category_props(data: dict | None) -> types.GameCategoryProps | None:
    """Собирает `GameCategoryProps`."""
    if not data:
        return None
    return types.GameCategoryProps(
        min_reviews=data.get("minTestimonials"),
        min_reviews_for_seller=data.get("minTestimonialsForSeller"),
    )


def game_category_option_value_range(data: dict | None) -> types.GameCategoryOptionValueRange | None:
    """Собирает `GameCategoryOptionValueRange` (объект `{min, max}` из `valueRangeLimit`)."""
    if not data or not isinstance(data, dict):
        return None
    return types.GameCategoryOptionValueRange(min=data.get("min"), max=data.get("max"))


def game_category_option(data: dict | None) -> types.GameCategoryOption | None:
    """Собирает `GameCategoryOption`."""
    if not data:
        return None
    return types.GameCategoryOption(
        id=data.get("id"),
        group=data.get("group"),
        label=data.get("label"),
        type=GameCategoryOptionTypes.__members__.get(data.get("type")),
        field=data.get("field"),
        value=data.get("value"),
        value_range_limit=game_category_option_value_range(data.get("valueRangeLimit")),
    )


def game_category_agreement(data: dict | None) -> types.GameCategoryAgreement | None:
    """Собирает `GameCategoryAgreement`."""
    if not data:
        return None
    return types.GameCategoryAgreement(
        id=data.get("id"),
        description=data.get("description"),
        icontype=GameCategoryAgreementIconTypes.__members__.get(data.get("iconType")),
        sequence=data.get("sequence"),
    )


def game_category_data_field(data: dict | None) -> types.GameCategoryDataField | None:
    """Собирает `GameCategoryDataField`."""
    if not data:
        return None
    return types.GameCategoryDataField(
        id=data.get("id"),
        label=data.get("label"),
        type=GameCategoryDataFieldTypes.__members__.get(data.get("type")),
        input_type=GameCategoryDataFieldInputTypes.__members__.get(data.get("inputType")),
        copyable=data.get("copyable"),
        hidden=data.get("hidden"),
        required=data.get("required"),
        value=data.get("value"),
    )


def game_category_obtaining_type(data: dict | None) -> types.GameCategoryObtainingType | None:
    """Собирает `GameCategoryObtainingType`."""
    if not data:
        return None
    return types.GameCategoryObtainingType(
        id=data.get("id"),
        name=data.get("name"),
        description=data.get("description"),
        game_category_id=data.get("gameCategoryId"),
        no_comment_from_buyer=data.get("noCommentFromBuyer"),
        instruction_for_buyer=data.get("instructionForBuyer"),
        instruction_for_seller=data.get("instructionForSeller"),
        sequence=data.get("sequence"),
        fee_multiplier=data.get("feeMultiplier"),
        agreements=[game_category_agreement(agr) for agr in (data.get("agreements") or []) if agr],
        props=game_category_props(data.get("props")),
    )


def game_category(data: dict | None) -> types.GameCategory | None:
    """Собирает `GameCategory`."""
    if not data:
        return None
    return types.GameCategory(
        id=data.get("id"),
        slug=data.get("slug"),
        name=data.get("name"),
        category_id=data.get("categoryId"),
        game_id=data.get("gameId"),
        obtaining=data.get("obtaining"),
        options=[game_category_option(opt) for opt in (data.get("options") or []) if opt],
        props=game_category_props(data.get("props")),
        no_comment_from_buyer=data.get("noCommentFromBuyer"),
        instruction_for_buyer=data.get("instructionForBuyer"),
        instruction_for_seller=data.get("instructionForSeller"),
        use_custom_obtaining=data.get("useCustomObtaining"),
        auto_confirm_period=GameCategoryAutoConfirmPeriods.__members__.get(data.get("autoConfirmPeriod")),
        auto_moderation_mode=data.get("autoModerationMode"),
        agreements=[game_category_agreement(agr) for agr in (data.get("agreements") or []) if agr],
        fee_multiplier=data.get("feeMultiplier"),
    )


def game_profile(data: dict | None) -> types.GameProfile | None:
    """Собирает `GameProfile`."""
    if not data:
        return None
    return types.GameProfile(
        id=data.get("id"),
        slug=data.get("slug"),
        name=data.get("name"),
        type=GameTypes.__members__.get(data.get("type")),
        logo=file(data.get("logo")),
    )


def game(data: dict | None) -> types.Game | None:
    """Собирает `Game`."""
    if not data:
        return None
    return types.Game(
        id=data.get("id"),
        slug=data.get("slug"),
        name=data.get("name"),
        type=GameTypes.__members__.get(data.get("type")),
        logo=file(data.get("logo")),
        banner=file(data.get("banner")),
        categories=[game_category(cat) for cat in (data.get("categories") or []) if cat],
        created_at=data.get("createdAt"),
    )


def item_priority_status_price_range(data: dict | None) -> types.ItemPriorityStatusPriceRange | None:
    """Собирает `ItemPriorityStatusPriceRange`."""
    if not data:
        return None
    return types.ItemPriorityStatusPriceRange(min=data.get("min"), max=data.get("max"))


def item_priority_status(data: dict | None) -> types.ItemPriorityStatus | None:
    """Собирает `ItemPriorityStatus`."""
    if not data:
        return None
    return types.ItemPriorityStatus(
        id=data.get("id"),
        price=data.get("price"),
        name=data.get("name"),
        type=PriorityTypes.__members__.get(data.get("type")),
        period=data.get("period"),
        price_range=item_priority_status_price_range(data.get("priceRange")),
    )


def item_log(data: dict | None) -> types.ItemLog | None:
    """Собирает `ItemLog`."""
    if not data:
        return None
    return types.ItemLog(
        id=data.get("id"),
        event=ItemLogEvents.__members__.get(data.get("event")),
        created_at=data.get("createdAt"),
        user=user_profile(data.get("user")),
    )


def item_deal_transaction(data: dict | None) -> types.ItemDealTransaction | None:
    """Собирает лёгкий `ItemDealTransaction` (снимок транзакции сделки/оплаты приоритета)."""
    if not data:
        return None
    return types.ItemDealTransaction(
        id=data.get("id"),
        operation=TransactionOperations.__members__.get(data.get("operation")),
        direction=TransactionDirections.__members__.get(data.get("direction")),
        provider_id=TransactionProviderIds.__members__.get(data.get("providerId")),
        status=TransactionStatuses.__members__.get(data.get("status")),
        status_description=data.get("statusDescription"),
        status_expiration_date=data.get("statusExpirationDate"),
        value=data.get("value"),
        created_at=data.get("createdAt"),
        payment_method_id=data.get("paymentMethodId"),
    )


def item(data: dict | None) -> types.Item | None:
    """Собирает `Item` (используется как для чужих лотов, так и для общих запросов `get_item`)."""
    if not data:
        return None
    return types.Item(
        id=data.get("id"),
        slug=data.get("slug"),
        name=data.get("name"),
        description=data.get("description"),
        obtaining_type=game_category_obtaining_type(data.get("obtainingType")),
        price=data.get("price"),
        raw_price=data.get("rawPrice"),
        priority=PriorityTypes.__members__.get(data.get("priority")),
        priority_position=data.get("priorityPosition"),
        attachments=[file(att) for att in (data.get("attachments") or []) if att],
        attributes=data.get("attributes"),
        category=game_category(data.get("category")),
        comment=data.get("comment"),
        data_fields=[game_category_data_field(f) for f in (data.get("dataFields") or []) if f],
        fee_multiplier=data.get("feeMultiplier"),
        game=game_profile(data.get("game")),
        seller_type=UserTypes.__members__.get(data.get("sellerType")),
        status=ItemStatuses.__members__.get(data.get("status")),
        user=user_profile(data.get("user")),
    )


def my_item(data: dict | None) -> types.MyItem | None:
    """Собирает `MyItem` (лот своего аккаунта)."""
    if not data:
        return None
    item = types.MyItem(
        id=data.get("id"),
        slug=data.get("slug"),
        name=data.get("name"),
        description=data.get("description"),
        obtaining_type=game_category_obtaining_type(data.get("obtainingType")),
        price=data.get("price"),
        prev_price=data.get("prevPrice"),
        raw_price=data.get("rawPrice"),
        priority_position=data.get("priorityPosition"),
        attachments=[file(att) for att in (data.get("attachments") or []) if att],
        attributes=data.get("attributes"),
        buyer=user_profile(data.get("buyer")),
        category=game_category(data.get("category")),
        comment=data.get("comment"),
        data_fields=[game_category_data_field(f) for f in (data.get("dataFields") or []) if f],
        fee_multiplier=data.get("feeMultiplier"),
        prev_fee_multiplier=data.get("prevFeeMultiplier"),
        seller_notified_about_fee_change=data.get("sellerNotifiedAboutFeeChange"),
        game=game_profile(data.get("game")),
        seller_type=UserTypes.__members__.get(data.get("sellerType")),
        status=ItemStatuses.__members__.get(data.get("status")),
        user=user_profile(data.get("user")),
        priority=PriorityTypes.__members__.get(data.get("priority")),
        priority_price=data.get("priorityPrice"),
        sequence=data.get("sequence"),
        status_expiration_date=data.get("statusExpirationDate"),
        status_description=data.get("statusDescription"),
        status_payment=item_deal_transaction(data.get("statusPayment")),
        views_counter=data.get("viewsCounter"),
        is_editable=data.get("editable"),
        approval_date=data.get("approvalDate"),
        deleted_at=data.get("deletedAt"),
        updated_at=data.get("updatedAt"),
        created_at=data.get("createdAt"),
    )
    item.deals_counter = data.get("dealsCounter")
    item.may_be_published = data.get("mayBePublished")
    item.post_moderation_checked_at = data.get("postModerationCheckedAt")
    item.is_automated = data.get("isAutomated")
    item.multiple = data.get("multiple")
    return item


def item_profile(data: dict | None) -> types.ItemProfile | None:
    """Собирает `ItemProfile` (краткий профиль лота для списков)."""
    if not data:
        return None
    return types.ItemProfile(
        id=data.get("id"),
        slug=data.get("slug"),
        priority=PriorityTypes.__members__.get(data.get("priority")),
        status=ItemStatuses.__members__.get(data.get("status")),
        name=data.get("name"),
        price=data.get("price"),
        raw_price=data.get("rawPrice"),
        seller_type=UserTypes.__members__.get(data.get("sellerType")),
        attachment=file(data.get("attachment")),
        user=user_profile(data.get("user")),
        approval_date=data.get("approvalDate"),
        priority_position=data.get("priorityPosition"),
        views_counter=data.get("viewsCounter"),
        fee_multiplier=data.get("feeMultiplier"),
        created_at=data.get("createdAt"),
    )


def review(data: dict | None) -> types.Review | None:
    """Собирает `Review`."""
    if not data:
        return None
    return types.Review(
        id=data.get("id"),
        status=ReviewStatuses.__members__.get(data.get("status")),
        text=data.get("text"),
        rating=data.get("rating"),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
        deal=None,  # избегаем циклического парсинга ItemDeal <-> Review при сборке из testimonials
        creator=user_profile(data.get("creator")),
        moderator=moderator(data.get("moderator")),
        user=user_profile(data.get("user")),
    )


def item_deal_props(data: dict | None) -> types.ItemDealProps | None:
    """Собирает `ItemDealProps`."""
    if not data:
        return None
    return types.ItemDealProps(auto_confirm_period=data.get("autoConfirmPeriod"))


def item_deal(data: dict | None) -> types.ItemDeal | None:
    """
    Собирает `ItemDeal`, включая маппинг "сырого" статуса Playerok в дружелюбный `DealStatuses`
    (см. `common.enums.DealStatuses` и `_DEAL_STATUS_MAP`).
    """
    if not data:
        return None
    raw_status_value = data.get("status")
    return types.ItemDeal(
        id=data.get("id"),
        status=_DEAL_STATUS_MAP.get(raw_status_value),
        raw_status=ItemDealStatuses.__members__.get(raw_status_value),
        completed_automatically=raw_status_value in _AUTOCONFIRMED_STATUSES,
        status_expiration_date=data.get("statusExpirationDate"),
        status_description=data.get("statusDescription"),
        direction=ItemDealDirections.__members__.get(data.get("direction")),
        obtaining=data.get("obtaining"),
        has_problem=data.get("hasProblem"),
        report_problem_enabled=data.get("reportProblemEnabled"),
        completed_user=user_profile(data.get("completedBy")),
        props=item_deal_props(data.get("props")),
        previous_status=ItemDealStatuses.__members__.get(data.get("prevStatus")),
        completed_at=data.get("completedAt"),
        created_at=data.get("createdAt"),
        logs=[item_log(log) for log in (data.get("logs") or []) if log],
        transaction=item_deal_transaction(data.get("transaction")),
        user=user_profile(data.get("user")),
        chat=chat(data.get("chat")),
        item=item(data.get("item")),
        review=review(data.get("testimonial")),
        obtaining_fields=[game_category_data_field(f) for f in (data.get("obtainingFields") or []) if f],
        comment_from_buyer=data.get("commentFromBuyer"),
    )


def chat_message_button(data: dict | None) -> types.ChatMessageButton | None:
    """Собирает `ChatMessageButton`."""
    if not data:
        return None
    return types.ChatMessageButton(
        type=ChatMessageButtonTypes.__members__.get(data.get("type")),
        url=data.get("url"),
        text=data.get("text"),
    )


def chat_message(data: dict | None) -> types.ChatMessage | None:
    """Собирает `ChatMessage`."""
    if not data:
        return None
    return types.ChatMessage(
        id=data.get("id"),
        text=data.get("text"),
        created_at=data.get("createdAt"),
        deleted_at=data.get("deletedAt"),
        is_read=data.get("isRead"),
        is_suspicious=data.get("isSuspicious"),
        is_bulk_messaging=data.get("isBulkMessaging"),
        game=game_profile(data.get("game")),
        images=[file(img) for img in (data.get("images") or []) if img],
        user=user_profile(data.get("user")),
        deal=item_deal(data.get("deal")),
        item=item(data.get("item")),
        moderator=moderator(data.get("moderator")),
        event_by_user=user_profile(data.get("eventByUser")),
        event_to_user=user_profile(data.get("eventToUser")),
        is_auto_response=data.get("isAutoResponse"),
        event=ChatMessageEvents.__members__.get(data.get("event")),
        buttons=[chat_message_button(btn) for btn in (data.get("buttons") or []) if btn],
        file=file(data.get("file")),
    )


def chat(data: dict | None) -> types.Chat | None:
    """Собирает `Chat`."""
    if not data:
        return None
    return types.Chat(
        id=data.get("id"),
        type=ChatTypes.__members__.get(data.get("type")),
        status=ChatStatuses.__members__.get(data.get("status")),
        unread_messages_counter=data.get("unreadMessagesCounter"),
        bookmarked=data.get("bookmarked"),
        is_texting_allowed=data.get("isTextingAllowed"),
        owner=user_profile(data.get("owner")),
        deals=[item_deal(deal) for deal in (data.get("deals") or []) if deal],
        started_at=data.get("startedAt"),
        finished_at=data.get("finishedAt"),
        last_message=chat_message(data.get("lastMessage")),
        users=[user_profile(u) for u in (data.get("participants") or []) if u],
    )


def temporary_attachment_upload_output(data: dict | None) -> types.TemporaryAttachmentUploadOutput | None:
    """Собирает `TemporaryAttachmentUploadOutput`."""
    if not data:
        return None
    return types.TemporaryAttachmentUploadOutput(
        id=data.get("id"),
        url=data.get("url"),
        chat_id=data.get("chatId"),
        client_attachment_id=data.get("clientAttachmentId"),
        expires_at=data.get("expiresAt"),
    )


# ---------------------------------------------------------------------------
# Страницы (courser-based pagination): единая логика для всех Relay-style списков GraphQL API
# ---------------------------------------------------------------------------

def page_info(data: dict | None) -> types.PageInfo | None:
    """Собирает `PageInfo`."""
    if not data:
        return None
    return types.PageInfo(
        start_cursor=data.get("startCursor"),
        end_cursor=data.get("endCursor"),
        has_previous_page=data.get("hasPreviousPage"),
        has_next_page=data.get("hasNextPage"),
    )


def _nodes(edges, builder) -> list:
    """
    Собирает объекты из Relay-обёрток `edges`, отбрасывая пустые узлы.

    Без фильтрации пустой `node` превращался бы в `None` внутри итогового списка —
    и падал бы у пользователя при обращении к атрибутам элементов.
    """
    result = []
    for edge in edges or []:
        if not edge:
            continue
        obj = builder(edge.get("node"))
        if obj is not None:
            result.append(obj)
    return result


def chat_list(data: dict | None) -> types.ChatList | None:
    """Собирает `ChatList`."""
    if not data:
        return None
    return types.ChatList(
        chats=_nodes(data.get("edges"), chat),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def chat_message_list(data: dict | None) -> types.ChatMessageList | None:
    """Собирает `ChatMessageList`."""
    if not data:
        return None
    return types.ChatMessageList(
        messages=_nodes(data.get("edges"), chat_message),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def item_deal_list(data: dict | None) -> types.ItemDealList | None:
    """Собирает `ItemDealList`."""
    if not data:
        return None
    return types.ItemDealList(
        deals=_nodes(data.get("edges"), item_deal),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def game_list(data: dict | None) -> types.GameList | None:
    """Собирает `GameList`."""
    if not data:
        return None
    return types.GameList(
        games=_nodes(data.get("edges"), game),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def game_category_obtaining_type_list(data: dict | None) -> types.GameCategoryObtainingTypeList | None:
    """Собирает `GameCategoryObtainingTypeList`."""
    if not data:
        return None
    return types.GameCategoryObtainingTypeList(
        obtaining_types=_nodes(data.get("edges"), game_category_obtaining_type),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def game_category_data_field_list(data: dict | None) -> types.GameCategoryDataFieldList | None:
    """Собирает `GameCategoryDataFieldList`."""
    if not data:
        return None
    return types.GameCategoryDataFieldList(
        data_fields=_nodes(data.get("edges"), game_category_data_field),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def item_profile_list(data: dict | None) -> types.ItemProfileList | None:
    """Собирает `ItemProfileList`."""
    if not data:
        return None
    return types.ItemProfileList(
        items=_nodes(data.get("edges"), item_profile),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def review_list(data: dict | None) -> types.ReviewList | None:
    """Собирает `ReviewList`."""
    if not data:
        return None
    return types.ReviewList(
        reviews=_nodes(data.get("edges"), review),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def message_template_list(data: dict | None) -> types.MessageTemplateList | None:
    """Собирает `MessageTemplateList`."""
    if not data:
        return None
    return types.MessageTemplateList(
        message_templates=_nodes(data.get("edges"), message_template),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def transaction_provider(data: dict | None) -> types.TransactionProvider | None:
    if not data:
        return None
    return types.TransactionProvider(
        id=data.get("id"),
        name=data.get("name"),
        fee=data.get("fee"),
        min_fee_amount=data.get("minFeeAmount"),
        description=data.get("description"),
    )


def transaction(data: dict | None) -> types.Transaction | None:
    """Собирает финансовую `Transaction`."""
    if not data or not data.get("id"):
        return None
    return types.Transaction(
        id=data["id"],
        operation=TransactionOperations.__members__.get(data.get("operation")),
        direction=TransactionDirections.__members__.get(data.get("direction")),
        provider_id=data.get("providerId"),
        provider=transaction_provider(data.get("provider")),
        status=TransactionStatuses.__members__.get(data.get("status")),
        status_description=data.get("statusDescription"),
        status_expiration_date=data.get("statusExpirationDate"),
        value=data.get("value"),
        fee=data.get("fee"),
        created_at=data.get("createdAt"),
        props=data.get("props") if isinstance(data.get("props"), dict) else data.get("props"),
        user=user_profile(data.get("user")),
        creator=user_profile(data.get("creator")),
    )


def transaction_list(data: dict | None) -> types.TransactionList | None:
    if not data:
        return None
    return types.TransactionList(
        transactions=_nodes(data.get("edges"), transaction),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def payout(data: dict | None) -> types.Payout | None:
    if not data or not data.get("id"):
        return None
    return types.Payout(
        id=data["id"],
        status=data.get("status"),
        completed_at=data.get("completedAt"),
        to=data.get("to"),
        ip_address=data.get("ipAddress"),
        value=data.get("value"),
        remote_id=data.get("remoteId"),
        payment_gateway=data.get("paymentGateway"),
        provider_id=data.get("providerId"),
        created_at=data.get("createdAt"),
        creator=user_profile(data.get("creator")),
    )


def payout_list(data: dict | None) -> types.PayoutList | None:
    if not data:
        return None
    return types.PayoutList(
        payouts=_nodes(data.get("edges"), payout),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def verified_card_list(data: dict | None) -> types.VerifiedCardList | None:
    if not data:
        return None
    return types.VerifiedCardList(
        cards=_nodes(data.get("edges"), verified_card),
        page_info=page_info(data.get("pageInfo")),
        total_count=data.get("totalCount"),
    )


def chat_bulk_message(data: dict | None) -> types.ChatBulkMessage | None:
    if not data or not data.get("id"):
        return None
    return types.ChatBulkMessage(
        id=data["id"],
        text=data.get("text"),
        created_at=data.get("createdAt"),
        started_at=data.get("startedAt"),
        finished_at=data.get("finishedAt"),
        send_after=data.get("sendAfter"),
        queue_status=data.get("queueStatus"),
        stats=data.get("stats"),
    )
