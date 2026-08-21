"""Уведомления Cardinal: отправка сообщений администраторам."""
from __future__ import annotations

import html
import asyncio
import time
import json
import os

from datetime import datetime

from typing import Any

from ..settings import STORAGE_DIR

from loguru import logger

from playerokapi.common.enums import EventTypes, TransactionOperations

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

# Путь к файлу с историей отправленных уведомлений (переживает перезапуск бота)
HISTORY_FILE = os.path.join(STORAGE_DIR, "notification_history.json")


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
    
    # 1. Поле moderator (если Playerok явно пометил сообщение как от модератора)
    if getattr(message, "moderator", None) is not None:
        return True
    
    # 2. По роли пользователя
    user = getattr(message, "user", None)
    if user:
        role = getattr(user, "role", None)
        if role is not None:
            role_name = getattr(role, "name", str(role)).upper()
            if role_name in ("MODERATOR", "CHECKER", "ADMIN", "SUPPORT"):
                return True
    
    # 3. По префиксу в никнейме (модераторы Playerok часто имеют ⚖️, 🔰, 🛠)
    username = getattr(user, "username", "") if user else ""
    if any(prefix in username for prefix in ("⚖️", "🔰", "🛠", "⚠️", "👮")):
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


# ---------------------------------------------------------------------------
# Выплаты: распознавание системного сообщения и форматирование деталей
# ---------------------------------------------------------------------------

#: Маркеры системного сообщения о выводе средств (в нижнем регистре).
PAYOUT_TEXT_MARKERS = (
    "ваша выплата успешно проведена",
    "сумма отправлена на указанные реквизиты",
)

#: По этому маркеру отрезаем «маркетинговый» хвост с просьбой об отзыве.
#: Чтобы оставить текст целиком — поставьте "" .
PAYOUT_TEXT_CUT_MARKER = "спасибо, что вы с нами"


def _is_payout_message(text: str | None) -> bool:
    """True, если сообщение — системное уведомление о выплате."""
    if not text:
        return False
    low = text.lower()
    return any(marker in low for marker in PAYOUT_TEXT_MARKERS)


def _clean_payout_text(text: str) -> str:
    """Убирает хвост «Спасибо, что вы с нами!..» из текста выплаты."""
    if PAYOUT_TEXT_CUT_MARKER:
        pos = text.lower().find(PAYOUT_TEXT_CUT_MARKER)
        if pos != -1:
            text = text[:pos]
    return text.strip()


def _fmt_money(value) -> str:
    """5100 -> '5 100', 1234.5 -> '1 234.5' (разделитель тысяч — пробел)."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    abs_num = abs(num)
    if abs_num == int(abs_num):
        s = f"{int(abs_num):,}".replace(",", " ")
    else:
        s = f"{abs_num:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
    return s


def _fmt_payout_status(status) -> str:
    """Статус выплаты человекочитаемо + эмодзи."""
    if status is None:
        return "—"
    raw = getattr(status, "name", status)
    s = str(raw).upper()
    if any(k in s for k in ("COMPLETED", "SUCCESS", "CONFIRMED", "УСПЕШН")):
        return "✅ Успешно"
    if any(k in s for k in ("PENDING", "PROCESSING", "ОБРАБОТК", "ОЖИДАНИ")):
        return "⏳ В обработке"
    if any(k in s for k in ("FAILED", "CANCEL", "ROLLED", "ОТКЛОН", "ВОЗВРАТ")):
        return "❌ Не удалось"
    return str(raw)


def _fmt_payout_method(method) -> str:
    """Способ вывода: СБП / карта / USDT."""
    if not method:
        return "—"
    m = str(method).upper()
    if "SBP" in m or "SPB" in m or "СБП" in m or "СПБ" in m:
        return "СБП"
    if "CARD" in m:
        return "💳 Карта"
    if "USDT" in m or "CRYPTO" in m:
        return "₮ USDT"
    return str(method)


def _fmt_datetime(iso) -> str:
    """ISO-дата -> '19.08.2026, 11:58' (локальное время)."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%Y, %H:%M")
    except ValueError:
        return str(iso)


#: Маркеры системного сообщения о скором снятии лота (в нижнем регистре).
ITEM_EXPIRING_MARKERS = (
    "будет снят с продажи через 7 дней",
    "по истечении срока выставления",
    "обновите статус товара",
)


def _is_item_expiring_message(text: str | None) -> bool:
    """True, если сообщение — системное предупреждение о снятии лота."""
    if not text:
        return False
    low = text.lower()
    return any(marker in low for marker in ITEM_EXPIRING_MARKERS)


def _get_section_from_item(item) -> str:
    """Раздел (игра → категория) напрямую из лота."""
    if not item:
        return "Не определено"
    game = getattr(item, "game", None)
    category = getattr(item, "category", None)
    game_name = getattr(game, "name", None) if game else None
    category_name = getattr(category, "name", None) if category else None
    if game_name and category_name:
        return f"{game_name} → {category_name}"
    if game_name:
        return game_name
    if category_name:
        return category_name
    return "Не определено"

def _get_item_image(item) -> str | None:
    """URL первой картинки лота (та самая обложка из списков Playerok)."""
    if not item:
        return None
    for att in getattr(item, "attachments", None) or []:
        url = getattr(att, "url", None)
        if url:
            return url
    att = getattr(item, "attachment", None)  # у ItemProfile — одиночная обложка
    return getattr(att, "url", None) if att else None


class Notifier:
    """Отправляет уведомления о событиям всем администраторам."""

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
        # Хранилище отправленных сообщений для последующего удаления
        # Загружается из файла, чтобы пережить перезапуск бота
        # {chat_id: [(message_id, timestamp), ...]}
        self._sent_messages: dict[int, list[tuple[int, float]]] = self._load_history()

    @property
    def _toggles(self):
        return self.cardinal.settings.notifications

    async def _send_all(self, text: str, remember_chat: str | None = None, reply_markup=None,
                        photo_url: str | None = None) -> None:
        """
        Шлёт уведомление всем админам; при `remember_chat` запоминает для ответа reply'ем.

        Если задан `photo_url` — отправляет фото лота с текстом в подписи
        (лимит подписи TG — 1024). При любой ошибке — обычный текст.
        """
        use_photo = bool(photo_url) and len(text) <= 1024
        for admin_id in self.admins.all_ids:
            sent = None
            if use_photo:
                try:
                    sent = await self.bot.send_photo(
                        admin_id, photo_url, caption=text, reply_markup=reply_markup
                    )
                except Exception as exc:
                    logger.debug("Фото не ушло админу {}: {} — шлю текстом", admin_id, exc)
            if sent is None:
                try:
                    sent = await self.bot.send_message(admin_id, text, reply_markup=reply_markup)
                except Exception:
                    logger.exception("Не удалось отправить уведомление админу {}", admin_id)
                    continue
            # Сохраняем для возможных ответов reply'ем
            if remember_chat is not None:
                self.reply_map[(sent.chat.id, sent.message_id)] = remember_chat
            # Сохраняем ID для последующей очистки истории
            self._sent_messages.setdefault(sent.chat.id, []).append((sent.message_id, time.time()))
            self._save_history()
            
    async def send_text(self, text: str) -> None:
        """Отправляет произвольный текст всем админам (используется модулями, например сводкой)."""
        await self._send_all(text)

    # ------------------------------------------------------------------
    # Очистка истории уведомлений в Telegram (логи не трогаются)
    # ------------------------------------------------------------------

    def _cleanup_old_entries(self, max_age_seconds: int = 7 * 24 * 3600) -> None:
        """Удаляет из хранилища записи старше max_age_seconds (по умолчанию 7 дней)."""
        cutoff = time.time() - max_age_seconds
        for chat_id in list(self._sent_messages.keys()):
            self._sent_messages[chat_id] = [
                (mid, ts) for mid, ts in self._sent_messages[chat_id] if ts >= cutoff
            ]
            if not self._sent_messages[chat_id]:
                del self._sent_messages[chat_id]

    def _load_history(self) -> dict[int, list[tuple[int, float]]]:
        """Загружает историю отправленных уведомлений из файла."""
        try:
            if os.path.isfile(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {int(k): [tuple(x) for x in v] for k, v in data.items()}
        except Exception as exc:
            logger.debug("Не удалось загрузить историю уведомлений: {}", exc)
        return {}

    def _save_history(self) -> None:
        """Сохраняет историю отправленных уведомлений в файл."""
        try:
            os.makedirs(STORAGE_DIR, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({str(k): [list(x) for x in v] for k, v in self._sent_messages.items()}, f)
        except Exception as exc:
            logger.debug("Не удалось сохранить историю уведомлений: {}", exc)

    async def clear_notifications(self, since_timestamp: float | None = None) -> dict:
        """
        Удаляет уведомления из Telegram.

        :param since_timestamp: Удалять только сообщения отправленные после этого времени.
                                Если None — удаляются все накопленные сообщения.
        :return: dict с количеством удалённых/ошибок.
        """
        self._cleanup_old_entries()
        
        removed = 0
        failed = 0
        skipped = 0
        
        for chat_id, messages in list(self._sent_messages.items()):
            to_delete = []
            remaining = []
            
            for message_id, timestamp in messages:
                if since_timestamp is None or timestamp >= since_timestamp:
                    to_delete.append(message_id)
                else:
                    remaining.append((message_id, timestamp))
            
            if not to_delete:
                continue
            
            # Telegram позволяет удалять до 100 сообщений за раз через delete_messages
            for i in range(0, len(to_delete), 100):
                batch = to_delete[i:i + 100]
                try:
                    # delete_messages (plural) — удаляет пакетом, быстрее чем по одному
                    await self.bot.delete_messages(chat_id, batch)
                    removed += len(batch)
                except Exception:
                    # Если batch-метод не сработал (старый aiogram), пробуем по одному
                    for mid in batch:
                        try:
                            await self.bot.delete_message(chat_id, mid)
                            removed += 1
                        except Exception:
                            failed += 1
                            skipped += 1
            
            # Оставляем только те, что не удалялись
            if remaining:
                self._sent_messages[chat_id] = remaining
            else:
                self._sent_messages.pop(chat_id, None)
        
        # Сохраняем обновлённую историю в файл
        self._save_history()
        
        logger.info("Очистка уведомлений: удалено={}, ошибок={}", removed, failed)
        return {"removed": removed, "failed": failed}

    async def _resolve_section_via_chat_api(self, chat) -> str:
        """
        Для чатов, где WS не прислал привязку к лоту, делаем доп. запрос API,
        чтобы получить полную информацию о чате и его сделках.
        """
        account = self.cardinal.account
        if account is None or chat is None or not getattr(chat, "id", None):
            return "Не определено"
        try:
            full_chat = await asyncio.to_thread(account.get_chat, chat.id)
        except Exception as exc:
            logger.debug("Не удалось получить чат {}: {}", chat.id, exc)
            return "Не определено"
        if not full_chat:
            return "Не определено"
        
        # Берём раздел из сделок чата
        deals = getattr(full_chat, "deals", []) or []
        for deal in deals:
            section = _get_section_from_deal(deal)
            if section != "Не определено":
                return section
        return "Не определено"

    async def _resolve_section_via_deal_api(self, deal) -> str:
        """
        Для событий сделок без полного item, делаем доп. запросы API.
        """
        account = self.cardinal.account
        if account is None or deal is None:
            return "Не определено"

        # --- Стратегия 1: через чат сделки ---
        deal_chat = getattr(deal, "chat", None)
        if deal_chat and getattr(deal_chat, "id", None):
            try:
                full_chat = await asyncio.to_thread(account.get_chat, deal_chat.id)
                if full_chat:
                    chat_deals = getattr(full_chat, "deals", []) or []
                    for d in chat_deals:
                        if d and getattr(d, "id", None) == deal.id:
                            section = _get_section_from_deal(d)
                            if section != "Не определено":
                                return section
                    for d in chat_deals:
                        section = _get_section_from_deal(d)
                        if section != "Не определено":
                            return section
            except Exception as exc:
                logger.debug("Стратегия 1 (чат) не удалась: {}", exc)

        # --- Стратегия 2: через лот сделки (упрощённая) ---
        deal_item = getattr(deal, "item", None)
        if deal_item and getattr(deal_item, "id", None):
            try:
                full_item = await asyncio.to_thread(account.get_item, deal_item.id)
                if full_item:
                    game = getattr(full_item, "game", None)
                    category = getattr(full_item, "category", None)
                    game_name = getattr(game, "name", None) if game else None
                    category_name = getattr(category, "name", None) if category else None
                    
                    if game_name and category_name:
                        return f"{game_name} → {category_name}"
                    elif game_name:
                        return game_name
                    elif category_name:
                        return category_name
            except Exception as exc:
                logger.debug("Стратегия 2 (item) не удалась: {}", exc)

        # --- Стратегия 3: через список всех сделок ---
        try:
            page = await asyncio.to_thread(account.get_deals, count=50)
            if page and getattr(page, "deals", None):
                for d in page.deals:
                    if d and getattr(d, "id", None) == getattr(deal, "id", None):
                        section = _get_section_from_deal(d)
                        if section != "Не определено":
                            return section
        except Exception as exc:
            logger.debug("Стратегия 3 (get_deals) не удалась: {}", exc)

        return "Не определено"

    # ------------------------------------------------------------------
    # Выплаты: сумма для уведомления
    # ------------------------------------------------------------------

    async def _fetch_latest_payout(self) -> dict:
        """
        Достаёт последнюю выплату из API Playerok (сумма/способ/статус/дата).

        Основной источник — запрос `payouts`; если пусто/ошибка — фолбэк
        по транзакциям вывода (`transactions`, operation=WITHDRAW).
        """
        result: dict = {"amount": None, "method": None, "status": None, "date": None}
        account = self.cardinal.account
        if account is None:
            return result

        try:
            page = await asyncio.to_thread(account.get_payouts, 5)
            payouts = list(page.payouts) if page and page.payouts else []
        except Exception as exc:
            logger.debug("Не удалось получить payouts: {}", exc)
            payouts = []

        if payouts:
            latest = max(payouts, key=lambda p: str(p.created_at or p.completed_at or ""))
            result["amount"] = latest.value
            result["method"] = latest.payment_gateway or latest.provider_id
            result["status"] = latest.status
            result["date"] = latest.completed_at or latest.created_at
            return result

        try:
            tx_page = await asyncio.to_thread(account.get_transactions, 10)
            txs = list(tx_page.transactions) if tx_page and tx_page.transactions else []
        except Exception as exc:
            logger.debug("Не удалось получить transactions: {}", exc)
            return result

        for tx in txs:
            if tx.operation is TransactionOperations.WITHDRAW:
                result["amount"] = tx.value
                result["method"] = tx.provider.name if tx.provider else tx.provider_id
                result["status"] = tx.status.name if tx.status else None
                result["date"] = tx.created_at
                break
        return result

    async def _notify_payout(self, message, chat) -> None:
        """Красивое уведомление о выплате с суммой (reply сохраняется)."""
        l10n = self.cardinal.l10n
        info = await self._fetch_latest_payout()
        text = _esc(_clean_payout_text(message.text or "")) or "…"
        remember = chat.id if chat is not None else None

        if info["amount"] is None:
            # API недоступно — новый вид, но без суммы
            await self._send_all(l10n("notif_payout_plain", text=text), remember_chat=remember)
            return

        await self._send_all(
            l10n(
                "notif_payout",
                amount=_fmt_money(info["amount"]),
                method=_esc(_fmt_payout_method(info["method"])),
                status=_esc(_fmt_payout_status(info["status"])),
                date=_esc(_fmt_datetime(info["date"])),
                text=text,
            ),
            remember_chat=remember,
        )

    # ------------------------------------------------------------------
    # Снятие лота через 7 дней: какой товар имеется в виду
    # ------------------------------------------------------------------

    async def _resolve_expiring_item(self, message, chat):
        """
        Ищет лот, о котором говорит системное сообщение.

        1) `message.item` из WS-кадра; 2) API: `get_chat` → `last_message.item`
        (системное сообщение в чате уведомлений привязано к лоту).
        """
        item = getattr(message, "item", None)
        if item and getattr(item, "name", None):
            return item

        account = self.cardinal.account
        if account is not None and chat is not None and getattr(chat, "id", None):
            try:
                full_chat = await asyncio.to_thread(account.get_chat, chat.id)
                last = getattr(full_chat, "last_message", None) if full_chat else None
                item = getattr(last, "item", None) if last else None
                if item and getattr(item, "name", None):
                    return item
            except Exception as exc:
                logger.debug("Не удалось достать лот из чата {}: {}", chat.id, exc)
        return None

    async def _find_my_item_by_name(self, name: str | None):
        """Ищет свой лот по точному названию (у ItemProfile есть ID и обложка)."""
        account = self.cardinal.account
        if account is None or not name:
            return None
        try:
            page = await asyncio.to_thread(account.get_my_items, None, 100)
            for it in (page.items if page and page.items else []):
                if (it.name or "") == name:
                    return it
        except Exception as exc:
            logger.debug("Не удалось найти лот по названию: {}", exc)
        return None

    async def _resolve_item_image(self, item) -> str | None:
        """Обложка лота: из полезной нагрузки события, иначе API (по ID или по имени)."""
        url = _get_item_image(item)
        if url:
            return url
        account = self.cardinal.account
        if account is None or item is None:
            return None

        item_id = getattr(item, "id", None)
        if not item_id:
            # В WS-кадре часто нет ID лота — ищем среди своих лотов по имени
            found = await self._find_my_item_by_name(getattr(item, "name", None))
            if found is not None:
                url = _get_item_image(found)
                if url:
                    return url
                item_id = getattr(found, "id", None)
        if not item_id:
            return None
        try:
            full_item = await asyncio.to_thread(account.get_item, item_id)
            return _get_item_image(full_item)
        except Exception as exc:
            logger.debug("Не удалось получить обложку лота {}: {}", item_id, exc)
            return None

    async def _resolve_message_item(self, message, chat):
        """Лот, к которому относится сообщение: message.item → сделки чата."""
        item = getattr(message, "item", None)
        if item and (getattr(item, "id", None) or getattr(item, "name", None)):
            return item
        account = self.cardinal.account
        if account is not None and chat is not None and getattr(chat, "id", None):
            try:
                full_chat = await asyncio.to_thread(account.get_chat, chat.id)
                for d in (getattr(full_chat, "deals", []) or []):
                    di = getattr(d, "item", None)
                    if di and (getattr(di, "id", None) or getattr(di, "name", None)):
                        return di
            except Exception as exc:
                logger.debug("Не удалось достать лот из чата {}: {}", chat.id, exc)
        return None

    async def _resolve_item_context(self, item) -> tuple:
        """
        Возвращает (раздел, URL обложки) для лота из события.

        Если в полезной нагрузке данных нет — дотягивает по ID
        или через поиск своего лота по названию.
        """
        section = _get_section_from_item(item)
        photo = _get_item_image(item)
        if section != "Не определено" and photo:
            return section, photo

        account = self.cardinal.account
        if account is None or item is None:
            return section, photo

        item_id = getattr(item, "id", None)
        name = getattr(item, "name", None)

        # Нет ID — ищем среди своих лотов по названию
        if not item_id and name:
            found = await self._find_my_item_by_name(name)
            if found is not None:
                item_id = getattr(found, "id", None)
                if photo is None:
                    photo = _get_item_image(found)

        # Полный лот по ID: раздел + обложка
        if item_id:
            try:
                full_item = await asyncio.to_thread(account.get_item, item_id)
                if full_item is not None:
                    if section == "Не определено":
                        section = _get_section_from_item(full_item)
                    if photo is None:
                        photo = _get_item_image(full_item)
            except Exception as exc:
                logger.debug("Не удалось получить полный лот {}: {}", item_id, exc)

        return section, photo

    async def _notify_item_expiring(self, message, chat) -> None:
        """Уведомление о скором снятии лота — с названием, разделом и ценой."""
        l10n = self.cardinal.l10n
        item = await self._resolve_expiring_item(message, chat)
        text = _esc((message.text or "").strip()) or "…"
        remember = chat.id if chat is not None else None

        if item is None:
            await self._send_all(
                l10n("notif_item_expiring_plain", text=text), remember_chat=remember
            )
            return
        photo = await self._resolve_item_image(item)

        price = getattr(item, "price", None)
        await self._send_all(
            l10n(
                "notif_item_expiring",
                item=_esc(getattr(item, "name", "?") or "?"),
                section=_esc(_get_section_from_item(item)),
                price=f"{_fmt_money(price)} ₽" if price is not None else "—",
                text=text,
            ),
            remember_chat=remember,
        )
    # ------------------------------------------------------------------
    # События Runner
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
        if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID):
            deal = event.deal
            # Обложка лота для уведомлений (None, если достать не удалось)
            photo = await self._resolve_item_image(getattr(deal, "item", None))

            # Проверяем переключатели: достаточно одного включённого
            if self._toggles.new_deal or self._toggles.item_paid:
                section = _get_section_from_deal(deal)
                item_name = deal.item.name if deal and deal.item else "?"
                buyer = deal.user.username if deal and deal.user else "?"
                status = deal.raw_status.name if deal and deal.raw_status else "?"
                price = deal.item.price if deal and deal.item and getattr(deal.item, "price", None) is not None else "?"

                # Если раздел не определился — пробуем через API
                if section == "Не определено":
                    section = await self._resolve_section_via_deal_api(deal)

                await self._send_all(l10n(
                    "notif_new_deal",
                    section=_esc(section),
                    item=_esc(item_name),
                    buyer=_esc(buyer),
                    status=_esc(status),
                    price=_esc(price),
                ), photo_url=photo)

            # Авто-выдача выполняется Runner'ом до того, как событие дошло сюда: если журнал
            # говорит «sent» — товар выдан, шлём отдельное уведомление с остатком склада.
            if event_type is EventTypes.ITEM_PAID:
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
                    ), photo_url=photo)

        elif event_type is EventTypes.NEW_MESSAGE and self._toggles.new_message:
            message = event.message
            chat = event.chat
            account = self.cardinal.account
            if message is None:
                return

            # Игнорируем собственные исходящие сообщения
            if message.user is not None and message.user.id == account.id:
                return

            # Фильтрация системных маркеров
            if _is_system_marker_message(message.text):
                logger.debug("Пропущено системное сообщение с маркером: {}", message.text)
                return

            # Системное уведомление о выводе средств — отдельный шаблон с суммой
            if _is_payout_message(message.text):
                await self._notify_payout(message, chat)
                return

            # Системное предупреждение о снятии лота — отдельный шаблон с лотом
            if _is_item_expiring_message(message.text):
                await self._notify_item_expiring(message, chat)
                return

            username = message.user.username if message.user else "Система"
            is_support = _is_support_message(message)

            if is_support:
                # Получаем контекст поддержки
                support_ctx = _get_support_context(message, chat)

                # Если раздел не определился из контекста — пробуем через API
                if support_ctx["section"] == "Не определено":
                    api_section = await self._resolve_section_via_chat_api(chat)
                    if api_section != "Не определено":
                        support_ctx["section"] = api_section

                if support_ctx["is_deal_chat"] or (support_ctx["section"] not in ("Не определено", "🛠 Служба поддержки")):
                    buyer = support_ctx["buyer"] or "?"
                    item_name = support_ctx["item_name"] or "?"
                    section = support_ctx["section"]

                    # Если всё ещё нет buyer/item — пробуем через API
                    if (buyer == "?" or item_name == "?") and chat:
                        try:
                            full_chat = await asyncio.to_thread(account.get_chat, chat.id)
                            if full_chat:
                                for deal in (getattr(full_chat, "deals", []) or []):
                                    if deal and getattr(deal, "user", None):
                                        buyer = getattr(deal.user, "username", buyer)
                                    if deal and getattr(deal, "item", None):
                                        item_name = getattr(deal.item, "name", item_name)
                                    if buyer != "?" and item_name != "?":
                                        break
                        except Exception:
                            pass

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

                # Если раздел не определился — пробуем через API
                if section == "Не определено":
                    section = await self._resolve_section_via_chat_api(chat)

                # Лот из сообщения/чата + раздел и обложка (поиск по названию)
                photo = None
                item = await self._resolve_message_item(message, chat)
                if item is not None:
                    item_section, photo = await self._resolve_item_context(item)
                    if section == "Не определено":
                        section = item_section

                text = message.text or ""

                await self._send_all(
                    l10n(
                        "notif_new_message",
                        username=_esc(username),
                        section=_esc(section),
                        text=_esc(text),
                    ),
                    remember_chat=event.chat.id,
                    photo_url=photo,
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
            account = self.cardinal.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal and deal.item else "?"

            # Если раздел или имя лота не определились — пробуем через API
            if section == "Не определено" or item_name == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                # Пробуем получить имя лота
                try:
                    full_deal = await asyncio.to_thread(account.get_deal, deal.id)
                    if full_deal and getattr(full_deal, "item", None):
                        item_name = getattr(full_deal.item, "name", item_name)
                except Exception:
                    pass

            await self._send_all(l10n(
                "notif_deal_problem",
                section=_esc(section),
                item=_esc(item_name),
                deal_id=_esc(deal.id),
            ))

        elif event_type is EventTypes.DEAL_PROBLEM_RESOLVED and self._toggles.deal_problem:
            deal = event.deal
            section = _get_section_from_deal(deal)

            # Если раздел не определился — пробуем через API
            if section == "Не определено":
                section = await self._resolve_section_via_deal_api(deal)

            await self._send_all(l10n(
                "notif_deal_problem_resolved",
                section=_esc(section),
                deal_id=_esc(deal.id),
            ))

        elif event_type in (EventTypes.DEAL_CONFIRMED, EventTypes.DEAL_CONFIRMED_AUTOMATICALLY) \
                and self._toggles.deal_confirmed:
            deal = event.deal
            account = self.cardinal.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"
            price = deal.item.price if deal.item and getattr(deal.item, "price", None) is not None else "?"

            # Если раздел или имя лота не определились — пробуем через API
            if section == "Не определено" or item_name == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                try:
                    full_deal = await asyncio.to_thread(account.get_deal, deal.id)
                    if full_deal and getattr(full_deal, "item", None):
                        item_name = getattr(full_deal.item, "name", item_name)
                        price = getattr(full_deal.item, "price", price) or price
                except Exception:
                    pass

            # Обложка лота для уведомления (None, если достать не удалось)
            photo = await self._resolve_item_image(deal.item if deal else None)

            await self._send_all(l10n(
                "notif_deal_confirmed",
                section=_esc(section),
                item=_esc(item_name),
                price=_esc(price),
            ), photo_url=photo)

        elif event_type is EventTypes.DEAL_ROLLED_BACK and self._toggles.deal_rolled_back:
            deal = event.deal
            account = self.cardinal.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"

            # Если раздел или имя лота не определились — пробуем через API
            if section == "Не определено" or item_name == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                try:
                    full_deal = await asyncio.to_thread(account.get_deal, deal.id)
                    if full_deal and getattr(full_deal, "item", None):
                        item_name = getattr(full_deal.item, "name", item_name)
                except Exception:
                    pass

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

                # Если раздел не определился — пробуем через API
                if section == "Не определено":
                    section = await self._resolve_section_via_deal_api(deal)

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