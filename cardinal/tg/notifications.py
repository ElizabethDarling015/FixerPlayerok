"""
Уведомления Cardinal в Telegram: события `Runner` → сообщения администраторам.

Каждый тип уведомления включается/выключается в `[notifications]` главного конфига
(переключается из TG-панели). На уведомление о новом сообщении Playerok можно ответить
reply'ем — Cardinal перешлёт текст в соответствующий чат Playerok (см. `reply_map` и
`handlers/replies.py`).
"""
from __future__ import annotations

import html

from loguru import logger

from playerokapi.common.enums import EventTypes

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def _esc(value) -> str:
    """HTML-экранирование пользовательского текста для parse_mode=HTML."""
    return html.escape(str(value)) if value is not None else "?"

class Notifier:
    """Отправляет уведомления о событиях всем администраторам панели."""

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
            lines.append(
                f"{i}. <b>{_esc(item_name)}</b>\n"
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
        deal = getattr(event, "deal", None)
        if deal and getattr(deal, "id", None):
            dedup_key = f"{event_type.name}:{deal.id}"
            if dedup_key in self._notified_deal_events:
                logger.debug("Пропущен дубль уведомления: {}", dedup_key)
                return

            # Запоминаем ключ. Ограничиваем размер множества, чтобы не было утечки памяти.
            self._notified_deal_events.add(dedup_key)
            if len(self._notified_deal_events) > 500:
                self._notified_deal_events.clear()
        # ---------------------------------------

        if event_type is EventTypes.NEW_DEAL and self._toggles.new_deal:
            deal = event.deal
            await self._send_all(l10n(
                "notif_new_deal",
                item=_esc(deal.item.name if deal.item else "?"),
                buyer=_esc(deal.user.username if deal.user else "?"),
                status=_esc(deal.raw_status.name if deal.raw_status else "?"),
            ))

        elif event_type is EventTypes.ITEM_PAID and self._toggles.item_paid:
            deal = event.deal
            item_name = deal.item.name if deal and deal.item else "?"
            await self._send_all(l10n(
                "notif_item_paid",
                item=_esc(item_name),
                buyer=_esc(deal.user.username if deal and deal.user else "?"),
            ))
            # Авто-выдача выполняется Runner'ом до того, как событие дошло сюда: если журнал
            # говорит «sent» — товар выдан, шлём отдельное уведомление с остатком склада.
            manager = self.cardinal.autodelivery_manager
            if (self._toggles.delivery and deal is not None and manager is not None
                    and manager.ledger is not None
                    and manager.ledger.get_state(deal.id) == "sent"):
                await self._send_all(l10n(
                    "notif_delivery_ok",
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

            # Для системных уведомлений (где user=None) подставляем имя "Система"
            username = message.user.username if message.user else "Система"
            
            # --- Извлекаем информацию о категории и игре ---
            category_name = None
            game_name = None
            
            # Приоритет 1: напрямую из сообщения
            if message.game and message.game.name:
                game_name = message.game.name
            
            if message.item and message.item.category and message.item.category.name:
                category_name = message.item.category.name
            
            # Приоритет 2: через сделку в сообщении
            if not category_name and message.deal and message.deal.item:
                if message.deal.item.category and message.deal.item.category.name:
                    category_name = message.deal.item.category.name
                if not game_name and message.deal.item.game and message.deal.item.game.name:
                    game_name = message.deal.item.game.name
            
            # Приоритет 3: через сделки чата
            if not category_name and chat.deals:
                for deal in chat.deals:
                    if deal and deal.item:
                        if deal.item.category and deal.item.category.name:
                            category_name = deal.item.category.name
                        if not game_name and deal.item.game and deal.item.game.name:
                            game_name = deal.item.game.name
                        if category_name:
                            break
            
            # Формируем строку раздела
            section_info = ""
            if game_name and category_name:
                section_info = f"{game_name} → {category_name}"
            elif game_name:
                section_info = game_name
            elif category_name:
                section_info = category_name
            else:
                section_info = "Не определено"
            # -----------------------------------------
                
            await self._send_all(
                l10n(
                    "notif_new_message",
                    username=_esc(username),
                    section=_esc(section_info),
                    text=_esc(message.text or ""),
                ),
                remember_chat=event.chat.id,
            )

        elif event_type is EventTypes.NEW_REVIEW and self._toggles.new_review:
            review = event.review
            await self._send_all(l10n(
                "notif_new_review",
                rating=_esc(getattr(review, "rating", "?")),
                author=_esc(review.creator.username if getattr(review, "creator", None) else "?"),
                text=_esc(getattr(review, "text", "") or ""),
            ))

        elif event_type is EventTypes.DEAL_HAS_PROBLEM and self._toggles.deal_problem:
            deal = event.deal
            await self._send_all(l10n(
                "notif_deal_problem",
                item=_esc(deal.item.name if deal.item else "?"),
                deal_id=_esc(deal.id),
            ))

        elif event_type is EventTypes.DEAL_PROBLEM_RESOLVED and self._toggles.deal_problem:
            await self._send_all(l10n("notif_deal_problem_resolved", deal_id=_esc(event.deal.id)))

        elif event_type in (EventTypes.DEAL_CONFIRMED, EventTypes.DEAL_CONFIRMED_AUTOMATICALLY) \
                and self._toggles.deal_confirmed:
            deal = event.deal
            await self._send_all(l10n(
                "notif_deal_confirmed",
                item=_esc(deal.item.name if deal.item else "?"),
            ))

        elif event_type is EventTypes.DEAL_ROLLED_BACK and self._toggles.deal_rolled_back:
            deal = event.deal
            await self._send_all(l10n(
                "notif_deal_rolled_back",
                item=_esc(deal.item.name if deal.item else "?"),
            ))

        elif event_type is EventTypes.ITEM_RAISED and self._toggles.item_raised:
            result = event.result
            await self._send_all(l10n(
                "notif_item_raised",
                item=_esc(getattr(result, "item_name", "?")),
                spent=_esc(getattr(result, "spent", "?")),
            ))

        elif event_type is EventTypes.INSUFFICIENT_BALANCE and self._toggles.insufficient_balance:
            result = event.result
            priority_status = getattr(result, "priority_status", None)
            await self._send_all(l10n(
                "notif_insufficient_balance",
                item=_esc(getattr(result, "item_name", "?")),
                price=_esc(priority_status.price if priority_status else "?"),
                available=_esc(getattr(result, "available", "?")),
            ))

        # Отдельное предупреждение (независимо от остальных переключателей): сделка
        # с покупателем из чёрного списка.
        if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID) and self._toggles.blacklist:
            deal = getattr(event, "deal", None)
            buyer = deal.user.username if deal is not None and deal.user is not None else None
            if self.cardinal.is_blacklisted(buyer):
                await self._send_all(l10n(
                    "notif_blacklist_deal",
                    buyer=_esc(buyer),
                    item=_esc(deal.item.name if deal.item else "?"),
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
                    self._notified_deal_events.add(f"NEW_DEAL:{deal.id}")
                    self._notified_deal_events.add(f"ITEM_PAID:{deal.id}")

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