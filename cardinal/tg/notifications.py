"""Уведомления Cardinal: отправка сообщений администраторам."""
from __future__ import annotations

import html
from typing import Any

from loguru import logger

from playerokapi.common.enums import EventTypes

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# ---------------------------------------------------------------------------
# Системные маркеры в сообщениях, которые дублируют отдельные события.
# Если сообщение содержит такой маркер — не отправляем NEW_MESSAGE,
# так как событие придёт отдельно через опрос сделок.
# ---------------------------------------------------------------------------
KNOWN_SYSTEM_MARKERS = {
    "{{ITEM_PAID}}",
    "{{DEAL_CONFIRMED}}",
    "{{DEAL_CONFIRMED_AUTOMATICALLY}}",
    "{{DEAL_PROBLEM_RESOLVED}}",
    "{{DEAL_ROLLED_BACK}}",
    "{{DEAL_HAS_PROBLEM}}",
}


def _esc(value: Any) -> str:
    """HTML-экранирование для безопасной вставки в Telegram."""
    if value is None:
        return "?"
    return html.escape(str(value))


def _is_system_marker_message(text: str | None) -> bool:
    """Проверяет, является ли сообщение системным маркером."""
    if not text:
        return False
    return any(marker in text for marker in KNOWN_SYSTEM_MARKERS)


def _is_support_message(message: Any) -> bool:
    """Проверяет, является ли сообщение от поддержки/модератора."""
    if not message:
        return False
    
    # Проверяем поле moderator (если оно заполнено)
    if getattr(message, "moderator", None) is not None:
        return True
    
    # Проверяем роль пользователя
    user = getattr(message, "user", None)
    if user:
        role = getattr(user, "role", None)
        if role is not None:
            role_name = getattr(role, "name", str(role))
            if role_name.upper() in ("MODERATOR", "CHECKER"):
                return True
    
    return False


def _get_section_from_deal(deal: Any) -> str:
    """Извлекает раздел (игра → категория) из сделки."""
    if not deal:
        return "Не определено"
    
    item = getattr(deal, "item", None)
    if not item:
        return "Не определено"
    
    game = getattr(item, "game", None)
    category = getattr(item, "category", None)
    
    game_name = getattr(game, "name", None) if game else None
    category_name = getattr(category, "name", None) if category else None
    
    if game_name and category_name:
        return f"{game_name} → {category_name}"
    elif game_name:
        return game_name
    elif category_name:
        return category_name
    return "Не определено"


def _get_support_context(message: Any, chat: Any) -> dict:
    """
    Определяет контекст сообщения поддержки.
    
    Возвращает словарь:
    {
        "is_support_chat": bool,      # True если это отдельный чат поддержки
        "is_deal_chat": bool,         # True если поддержка в чате с покупателем
        "buyer": str | None,          # Имя покупателя (если есть)
        "item_name": str | None,      # Название лота (если есть)
        "section": str,               # Раздел (игра → категория)
    }
    """
    result = {
        "is_support_chat": False,
        "is_deal_chat": False,
        "buyer": None,
        "item_name": None,
        "section": "🛠 Служба поддержки",
    }
    
    if not chat:
        return result
    
    # Проверяем тип чата
    chat_type = getattr(chat, "type", None)
    if chat_type is not None:
        type_name = getattr(chat_type, "name", str(chat_type))
        if type_name.upper() in ("SUPPORT", "ПОДДЕРЖКА"):
            result["is_support_chat"] = True
            return result
    
    # Если это не чат поддержки, проверяем есть ли сделки в чате
    deals = getattr(chat, "deals", [])
    if deals:
        result["is_deal_chat"] = True
        
        # Берём первую активную сделку для контекста
        for deal in deals:
            if deal is None:
                continue
            
            # Получаем покупателя
            deal_user = getattr(deal, "user", None)
            if deal_user:
                result["buyer"] = getattr(deal_user, "username", None)
            
            # Получаем лот и раздел
            deal_item = getattr(deal, "item", None)
            if deal_item:
                result["item_name"] = getattr(deal_item, "name", None)
                result["section"] = _get_section_from_deal(deal)
            
            # Прерываемся после первой найденной сделки с данными
            if result["buyer"] or result["item_name"]:
                break
    
    return result


def _get_section_from_message(message: Any, chat: Any) -> str:
    """Извлекает раздел из сообщения."""
    if not message:
        return "Не определено"
    
    # Проверяем, является ли сообщение от поддержки/модератора
    if _is_support_message(message):
        return "🛠 Служба поддержки"
    
    # Пробуем получить из самого сообщения
    game = getattr(message, "game", None)
    item = getattr(message, "item", None)
    
    game_name = getattr(game, "name", None) if game else None
    category = getattr(item, "category", None) if item else None
    category_name = getattr(category, "name", None) if category else None
    
    # Если не нашли в сообщении, пробуем из сделки
    deal = getattr(message, "deal", None)
    if deal:
        return _get_section_from_deal(deal)
    
    # Если не нашли в сделке, пробуем из чата
    if chat and not game_name and not category_name:
        deals = getattr(chat, "deals", [])
        if deals:
            for chat_deal in deals:
                section = _get_section_from_deal(chat_deal)
                if section != "Не определено":
                    return section
    
    if game_name and category_name:
        return f"{game_name} → {category_name}"
    elif game_name:
        return game_name
    elif category_name:
        return category_name
    
    # Специальный случай для чата поддержки (по типу чата)
    if chat:
        chat_type = getattr(chat, "type", None)
        if chat_type is not None:
            type_name = getattr(chat_type, "name", str(chat_type))
            if type_name.upper() in ("SUPPORT", "ПОДДЕРЖКА"):
                return "🛠 Служба поддержки"
    
    return "Не определено"


class Notifier:
    """Отправляет уведомления о событиях всем администраторам."""

    def __init__(self, cardinal, bot, admins):
        self.cardinal = cardinal
        self.bot = bot
        self.admins = admins
        #: (tg_chat_id, tg_message_id) -> id чата Playerok — для ответов reply'ем из TG.
        self.reply_map: dict[tuple[int, int], str] = {}
        self.session_expired_messages: set[tuple[int, int]] = set()
        self._recent_errors: dict[str, float] = {}
        # Дедупликация: защита от повторных уведомлений по одной и той же сделке
        self._notified_deal_events: set[str] = set()

    @property
    def _toggles(self):
        return self.cardinal.settings.notifications

    async def _send_all(self, text: str, remember_chat: str | None = None, reply_markup=None) -> None:
        """Шлёт текст всем админам; при `remember_chat` запоминает сообщения для ответа reply'ем."""
        for admin_id in self.admins.all_ids:
            try:
                sent = await self.bot.send_message(admin_id, text, reply_markup=reply_markup)
            except Exception:
                logger.exception("Не удалось отправить уведомление админу {}", admin_id)
                continue
            if remember_chat is not None:
                self.reply_map[(sent.chat.id, sent.message_id)] = remember_chat

    async def send_text(self, text: str) -> None:
        """Отправляет произвольный текст всем админам (используется модулями, например сводкой)."""
        await self._send_all(text)

    # ------------------------------------------------------------------
    # События Runner
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Уведомления о пропущенных сделках (при старте бота)
    # ------------------------------------------------------------------

    async def notify_missed_deals(self, missed_deals: list) -> None:
        """
        Уведомляет админов о сделках, которые произошли, пока бот был выключен.
        Вызывается при старте Cardinal — только информирует, автовыдачу не запускает.
        """
        if not missed_deals:
            return
        l10n = self.cardinal.l10n
        count = len(missed_deals)
        
        # Заголовок
        header = f"🌙 <b>Сделок за время простоя: {count}</b>\n\n"
        
        # Список сделок
        lines = []
        for i, deal in enumerate(missed_deals, 1):
            item_name = deal.item.name if deal and deal.item else "?"
            buyer = deal.user.username if deal and deal.user else "?"
            raw_status = deal.raw_status.name if deal and deal.raw_status else "?"
            section = _get_section_from_deal(deal)
            lines.append(
                f"{i}. <b>{_esc(item_name)}</b>\n"
                f"   📂 {_esc(section)}\n"
                f"   👤 Покупатель: {_esc(buyer)}\n"
                f"   📋 Статус: {_esc(raw_status)}"
            )
        
        text = header + "\n\n".join(lines)
        
        # Если текст слишком длинный, Telegram его не примет — разбиваем
        if len(text) > 4000:
            text = text[:4000] + "\n\n<i>...и ещё сделки (список обрезан)</i>"
        
        await self._send_all(text)

    async def on_event(self, event) -> None:
        l10n = self.cardinal.l10n
        event_type = event.type

        # --- ДЕДУПЛИКАЦИЯ (ЗАЩИТА ОТ ДУБЛЕЙ) ---
        # Должна быть ПЕРВЫМ блоком в on_event!
        deal = getattr(event, "deal", None)
        if deal and getattr(deal, "id", None):
            # Для NEW_DEAL и ITEM_PAID используем общий ключ — они дублируют друг друга
            if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID):
                dedup_key = f"DEAL:{deal.id}"
            else:
                dedup_key = f"{event_type.name}:{deal.id}"
            
            if dedup_key in self._notified_deal_events:
                logger.debug("Пропущен дубль уведомления: {}", dedup_key)
                return

            # Запоминаем ключ. Ограничиваем размер множества, чтобы не было утечки памяти.
            self._notified_deal_events.add(dedup_key)
            if len(self._notified_deal_events) > 500:
                self._notified_deal_events.clear()
        # ---------------------------------------

        # Объединяем NEW_DEAL и ITEM_PAID в одно уведомление
        # Оба события означают одно и то же: покупатель оплатил лот
        if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID):
            # Проверяем переключатели: достаточно одного включённого
            if self._toggles.new_deal or self._toggles.item_paid:
                deal = event.deal
                section = _get_section_from_deal(deal)
                item_name = deal.item.name if deal and deal.item else "?"
                buyer = deal.user.username if deal and deal.user else "?"
                status = deal.raw_status.name if deal and deal.raw_status else "?"
                price = deal.item.price if deal and deal.item and getattr(deal.item, "price", None) is not None else "?"
                
                await self._send_all(l10n(
                    "notif_new_deal",
                    section=_esc(section),
                    item=_esc(item_name),
                    buyer=_esc(buyer),
                    status=_esc(status),
                    price=_esc(price),
                ))
            
            # Авто-выдача выполняется Runner'ом до того, как событие дошло сюда: если журнал
            # говорит «sent» — товар выдан, шлём отдельное уведомление с остатком склада.
            # Работает только для ITEM_PAID (именно к этому событию привязана авто-выдача)
            if event_type is EventTypes.ITEM_PAID:
                deal = event.deal
                manager = self.cardinal.autodelivery_manager
                if (self._toggles.delivery and deal is not None and manager is not None
                        and manager.ledger is not None
                        and manager.ledger.get_state(deal.id) == "sent"):
                    section = _get_section_from_deal(deal)
                    item_name = deal.item.name if deal and deal.item else "?"
                    await self._send_all(l10n(
                        "notif_delivery_ok",
                        section=_esc(section),
                        item=_esc(item_name),
                        stock=manager.get_stock_size(item_name),
                    ))

        elif event_type is EventTypes.NEW_MESSAGE and self._toggles.new_message:
            message = event.message
            chat = event.chat
            account = self.cardinal.account
            if message is None:
                return
            
            # Игнорируем только если это наше собственное исходящее сообщение
            if message.user is not None and message.user.id == account.id:
                return

            # --- ФИЛЬТРАЦИЯ СИСТЕМНЫХ МАРКЕРОВ ---
            # Если сообщение содержит известный маркер — пропускаем,
            # так как событие придёт отдельно через опрос сделок
            if _is_system_marker_message(message.text):
                logger.debug("Пропущено системное сообщение с маркером: {}", message.text)
                return
            # ---------------------------------------

            # Для системных уведомлений (где user=None) подставляем имя "Система"
            username = message.user.username if message.user else "Система"
            
            # Проверяем, является ли сообщение от поддержки
            is_support = _is_support_message(message)
            
            if is_support:
                # Получаем контекст поддержки
                support_ctx = _get_support_context(message, chat)
                
                if support_ctx["is_deal_chat"]:
                    # Поддержка в чате с покупателем — показываем контекст сделки
                    buyer = support_ctx["buyer"] or "?"
                    item_name = support_ctx["item_name"] or "?"
                    section = support_ctx["section"]
                    
                    await self._send_all(
                        l10n(
                            "notif_support_in_deal_chat",
                            username=_esc(f"🛠 {username}"),
                            section=_esc(section),
                            buyer=_esc(buyer),
                            item=_esc(item_name),
                            text=_esc(message.text or ""),
                        ),
                        remember_chat=event.chat.id,
                    )
                else:
                    # Отдельный чат поддержки
                    await self._send_all(
                        l10n(
                            "notif_new_message",
                            username=_esc(f"🛠 {username}"),
                            section=_esc("🛠 Служба поддержки"),
                            text=_esc(message.text or ""),
                        ),
                        remember_chat=event.chat.id,
                    )
            else:
                # Обычное сообщение от покупателя
                section = _get_section_from_message(message, chat)
                text = message.text or ""
                
                await self._send_all(
                    l10n(
                        "notif_new_message",
                        username=_esc(username),
                        section=_esc(section),
                        text=_esc(text),
                    ),
                    remember_chat=event.chat.id,
                )

        elif event_type is EventTypes.NEW_REVIEW and self._toggles.new_review:
            review = event.review
            rating = getattr(review, "rating", "?")
            author = review.creator.username if getattr(review, "creator", None) else "?"
            text = getattr(review, "text", "") or ""
            
            await self._send_all(l10n(
                "notif_new_review",
                rating=_esc(rating),
                author=_esc(author),
                text=_esc(text),
            ))

        elif event_type is EventTypes.DEAL_HAS_PROBLEM and self._toggles.deal_problem:
            deal = event.deal
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"
            
            await self._send_all(l10n(
                "notif_deal_problem",
                section=_esc(section),
                item=_esc(item_name),
                deal_id=_esc(deal.id),
            ))

        elif event_type is EventTypes.DEAL_PROBLEM_RESOLVED and self._toggles.deal_problem:
            deal = event.deal
            section = _get_section_from_deal(deal)
            
            await self._send_all(l10n(
                "notif_deal_problem_resolved",
                section=_esc(section),
                deal_id=_esc(deal.id),
            ))

        elif event_type in (EventTypes.DEAL_CONFIRMED, EventTypes.DEAL_CONFIRMED_AUTOMATICALLY) \
                and self._toggles.deal_confirmed:
            deal = event.deal
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"
            price = deal.item.price if deal.item and getattr(deal.item, "price", None) is not None else "?"
            
            await self._send_all(l10n(
                "notif_deal_confirmed",
                section=_esc(section),
                item=_esc(item_name),
                price=_esc(price),
            ))

        elif event_type is EventTypes.DEAL_ROLLED_BACK and self._toggles.deal_rolled_back:
            deal = event.deal
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"
            
            await self._send_all(l10n(
                "notif_deal_rolled_back",
                section=_esc(section),
                item=_esc(item_name),
            ))

        elif event_type is EventTypes.ITEM_RAISED and self._toggles.item_raised:
            result = event.result
            item_name = getattr(result, "item_name", "?")
            spent = getattr(result, "spent", "?")
            
            await self._send_all(l10n(
                "notif_item_raised",
                item=_esc(item_name),
                spent=_esc(spent),
            ))

        elif event_type is EventTypes.INSUFFICIENT_BALANCE and self._toggles.insufficient_balance:
            result = event.result
            priority_status = getattr(result, "priority_status", None)
            item_name = getattr(result, "item_name", "?")
            price = priority_status.price if priority_status else "?"
            available = getattr(result, "available", "?")
            
            await self._send_all(l10n(
                "notif_insufficient_balance",
                item=_esc(item_name),
                price=_esc(price),
                available=_esc(available),
            ))

        # Отдельное предупреждение (независимо от остальных переключателей): сделка
        # с покупателем из чёрного списка.
        # ДОЛЖНО БЫТЬ ПОСЛЕДНИМ блоком, отдельный if (не elif)!
        if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID) and self._toggles.blacklist:
            deal = getattr(event, "deal", None)
            buyer = deal.user.username if deal is not None and deal.user is not None else None
            if self.cardinal.is_blacklisted(buyer):
                section = _get_section_from_deal(deal)
                item_name = deal.item.name if deal and deal.item else "?"
                
                await self._send_all(l10n(
                    "notif_blacklist_deal",
                    section=_esc(section),
                    buyer=_esc(buyer),
                    item=_esc(item_name),
                ))

    # ------------------------------------------------------------------
    # Служебные уведомления (не из событий Runner)
    # ------------------------------------------------------------------

    async def notify_started(self, missed_deals: list | None = None) -> None:
        """Уведомление о старте Cardinal (аккаунт, баланс, модули + пропущенные сделки)."""
        account = self.cardinal.account
        profile = getattr(account, "profile", None)
        balance = profile.balance.format_balance(detailed=True) if profile is not None and profile.balance is not None else "?"
        modules_settings = self.cardinal.settings.modules
        modules = ", ".join(
            name for name in type(modules_settings).model_fields if getattr(modules_settings, name)
        ) or "—"

        # Считаем пропущенные сделки и помечаем их, чтобы Runner не прислал дубли
        missed_count = 0
        if missed_deals:
            missed_count = len(missed_deals)
            for deal in missed_deals:
                if deal and getattr(deal, "id", None):
                    # Помечаем как "уже уведомлённые" для дедупликации
                    # Используем общий ключ DEAL: для объединения NEW_DEAL и ITEM_PAID
                    self._notified_deal_events.add(f"DEAL:{deal.id}")

        # --- Считаем непрочитанные сообщения ---
        unread_count = 0
        if profile is not None and getattr(profile, "unread_chats_counter", None) is not None:
            unread_count = profile.unread_chats_counter
        # ------------------------------------------

        text = self.cardinal.l10n(
            "notif_started",
            username=_esc(account.username if account else "?"),
            balance=_esc(balance),
            missed_deals=_esc(missed_count),
            unread_messages=_esc(unread_count),
            modules=_esc(modules),
        )

        # Строка состояния подключения — сразу после заголовка
        conn = "🟢 Online" if self.cardinal.playerok_connected else "🔴 Offline"
        conn_line = f"🔌 Подключение: {conn}"
        head, sep, tail = text.partition("\n")
        text = head + "\n" + conn_line + "\n" + sep + tail

        # Пустые строки между блоками: аккаунт/баланс, сделки/сообщения, модули
        for marker in ("🌙", "🧩"):
            text = text.replace(f"\n{marker}", f"\n\n{marker}")

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=self.cardinal.l10n("btn_home"), callback_data="menu")]
        ])
        await self._send_all(text, reply_markup=markup)

    async def notify_error(self, error_text: str) -> None:
        if self._toggles.errors:
            await self._send_all(self.cardinal.l10n("notif_error", error=_esc(error_text)))

    async def notify_stock_empty(self, item_name: str) -> None:
        if self._toggles.stock_empty:
            await self._send_all(self.cardinal.l10n("notif_stock_empty", item=_esc(item_name)))

    async def notify_restore_ok(self, item_name: str, new_item_id: str) -> None:
        await self._send_all(self.cardinal.l10n("notif_restore_ok", item=_esc(item_name),
                                                item_id=_esc(new_item_id)))

    async def notify_restore_failed(self, item_name: str, error_text: str) -> None:
        await self._send_all(self.cardinal.l10n("notif_restore_fail", item=_esc(item_name),
                                                error=_esc(error_text)))

    async def notify_restore_premium_fallback(self, item_name: str, new_item_id: str,
                                              reason: str) -> None:
        await self._send_all(self.cardinal.l10n(
            "notif_restore_premium_fallback",
            item=_esc(item_name),
            item_id=_esc(new_item_id),
            reason=_esc(reason or "неизвестная причина"),
        ))