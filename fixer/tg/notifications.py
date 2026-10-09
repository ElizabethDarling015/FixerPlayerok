"""Уведомления Fixer: отправка сообщений администраторам."""
from __future__ import annotations

import html
import asyncio
import time
import json
import os
import re

from datetime import datetime

from typing import Any

from ..settings import STORAGE_DIR

from loguru import logger

from playerokapi.common.enums import EventTypes

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from . import chat_kinds
from .api_cache import TTLCache
from .reactions import DealReactions


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
    "{{ITEM_SENT}}",
}

def _chat_anchor(chat_id: str | None) -> str:
    """Невидимая ссылка с ID чата Playerok в начале уведомления.

    По ней reply на уведомление находит чат и после перезапуска бота, когда
    соответствие «сообщение → чат» в памяти уже потеряно (см. handlers/replies.py)."""
    if not chat_id:
        return ""
    return f'<a href="https://playerok.com/chats/{chat_id}">\u200b</a>'


def _lot_link(item) -> str:
    """Название лота ссылкой на его страницу (или просто названием, если slug неизвестен)."""
    name = getattr(item, "name", None) or "?"
    slug = getattr(item, "slug", None)
    if slug:
        return f'<a href="https://playerok.com/products/{html.escape(slug)}">{html.escape(name)}</a>'
    return html.escape(name)

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
    # Пробуем взять из списка attachments
    for att in getattr(item, "attachments", None) or []:
        url = getattr(att, "url", None)
        if url:
            return url
    # Фолбэк: одиночная обложка (у ItemProfile)
    single_att = getattr(item, "attachment", None)
    return getattr(single_att, "url", None) if single_att else None


# ---------------------------------------------------------------------------
# Извлечение slug лота из ссылок в тексте/кнопках системных сообщений
# ---------------------------------------------------------------------------
_PLAYEROK_URL_RE = re.compile(r"https?://(?:www\.)?playerok\.com/[^\s<>\"')\]]+", re.IGNORECASE)


def _extract_item_slug(text: str | None, buttons=None) -> str | None:
    """Достаёт slug лота (последний сегмент пути) из ссылки в тексте или кнопках сообщения."""
    urls: list[str] = []
    if text:
        urls.extend(_PLAYEROK_URL_RE.findall(text))
    for btn in (buttons or []):
        url = getattr(btn, "url", None)
        if url:
            urls.append(url)

    for url in urls:
        path = url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        slug = path.rsplit("/", 1)[-1]
        if slug and slug.lower() not in {"catalog", "app", "ru", "en", "profile", "chat", "support"}:
            return slug
    return None


def build_payout_details(l10n, amount=None, method=None, status=None, date=None, balance=None) -> str:
    """Строки деталей выплаты; неизвестные поля не выводятся (раньше было «-— ₽» и прочерки)."""
    lines = []
    if amount is not None:
        lines.append(l10n("payout_line_amount", amount=_fmt_money(amount)))
    if method:
        lines.append(l10n("payout_line_method", method=_esc(method)))
    if status:
        lines.append(l10n("payout_line_status", status=_esc(status)))
    if date:
        lines.append(l10n("payout_line_date", date=_esc(date)))
    if balance is not None:
        lines.append(l10n("payout_line_balance", balance=_fmt_money(balance)))
    return "\n".join(lines) + ("\n" if lines else "")


def build_new_deal_text(l10n, *, section, item, buyer, price, chat_id, autodelivery: bool) -> str:
    """Полный текст уведомления «Новая сделка» (значения — уже экранированные строки)."""
    return l10n(
        "notif_new_deal",
        section=section, item=item, buyer=buyer, price=price,
        chat_id=chat_id,
        autodelivery=l10n("notif_new_deal_autodelivery") if autodelivery else "",
    )


def build_started_text(l10n, *, username, balance, missed_deals, unread_messages, modules,
                       connected: bool) -> str:
    """Текст уведомления «FixerPlayerok запущен» (то же самое показывает тест в «Тестах»)."""
    text = l10n(
        "notif_started",
        username=_esc(username),
        balance=_esc(balance),
        missed_deals=_esc(missed_deals),
        unread_messages=_esc(unread_messages),
        modules=_esc(modules),
    )
    # Строка состояния подключения — сразу после заголовка
    conn = "🟢 Online" if connected else "🔴 Offline"
    head, sep, tail = text.partition("\n")
    text = head + "\n" + f"🔌 Подключение: {conn}" + "\n" + sep + tail
    # Пустые строки между блоками: аккаунт/баланс, сделки/сообщения, модули
    for marker in ("🌙", "🧩"):
        text = text.replace(f"\n{marker}", f"\n\n{marker}")
    return text


def started_keyboard(l10n) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=l10n("btn_home"), callback_data="menu")]
    ])


def close_keyboard(l10n) -> InlineKeyboardMarkup:
    """Одна кнопка «Закрыть» — удаляет уведомление (поддержка, администрация, площадка)."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=l10n("btn_close"), callback_data="close")
    ]])


def new_deal_keyboard(l10n, deal_id: str | None):
    """Кнопки под «Новой сделкой»: подтвердить выдачу (если есть ID сделки) и свернуть."""
    row = []
    if deal_id:
        row.append(InlineKeyboardButton(text=l10n("deal_btn_confirm"), callback_data=f"dl:ok:{deal_id}"))
    row.append(InlineKeyboardButton(text=l10n("deal_btn_collapse"), callback_data="dl:min"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


class Notifier:
    """Отправляет уведомления о событиям всем администраторам."""

    def __init__(self, fixer, bot, admins):
        self.fixer = fixer
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
        # Кэш ответов Playerok (только в памяти, см. api_cache.py): сделка/лот почти не
        # меняются — час; чат (в нём могут появиться новые сделки) — 10 минут и сброс
        # при новой сделке в этом чате.
        self._deal_cache = TTLCache(ttl=3600)
        self._item_cache = TTLCache(ttl=3600)
        self._chat_cache = TTLCache(ttl=600)
        self._my_items_cache = TTLCache(ttl=600, maxsize=1)
        #: Реакции на уведомления «Новая сделка» (⚡/🤔/👎 от автовосстановления).
        self.deal_reactions = DealReactions()

    @property
    def _toggles(self):
        return self.fixer.settings.notifications

    async def _send_all(self, text: str, remember_chat: str | None = None, reply_markup=None,
                        photo_url: str | None = None) -> list[tuple[int, int]]:
        """
        Шлёт уведомление всем админам; при `remember_chat` запоминает для ответа reply'ем.
        Возвращает отправленные сообщения: [(tg_chat_id, message_id), …].

        Если задан `photo_url` — отправляет фото лота с текстом в подписи
        (лимит подписи TG — 1024). При любой ошибке — обычный текст.
        """
        if remember_chat and remember_chat not in text:
            text = _chat_anchor(remember_chat) + text
        use_photo = bool(photo_url) and len(text) <= 1024
        delivered: list[tuple[int, int]] = []
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
                    sent = await self.bot.send_message(
                        admin_id, text, reply_markup=reply_markup,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                    )
                except Exception:
                    logger.exception("Не удалось отправить уведомление админу {}", admin_id)
                    continue
            # Сохраняем для возможных ответов reply'ем
            if remember_chat is not None:
                self.reply_map[(sent.chat.id, sent.message_id)] = remember_chat
            # Сохраняем ID для последующей очистки истории
            self._sent_messages.setdefault(sent.chat.id, []).append((sent.message_id, time.time()))
            self._save_history()
            delivered.append((sent.chat.id, sent.message_id))
        return delivered
            
    async def send_text(self, text: str, reply_markup=None) -> None:
        """Отправляет произвольный текст всем админам (используется модулями, например сводкой)."""
        await self._send_all(text, reply_markup=reply_markup)

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

    # ------------------------------------------------------------------
    # Чат сделки: чтобы на уведомление «Новая сделка» можно было ответить reply'ем
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Запросы к Playerok через кэш (см. api_cache.py)
    # ------------------------------------------------------------------

    async def _get_deal(self, deal_id):
        cached = self._deal_cache.get(deal_id)
        if cached is not None:
            return cached
        account = self.fixer.account
        if account is None or not deal_id:
            return None
        deal = await asyncio.to_thread(account.get_deal, deal_id)
        self._deal_cache.set(deal_id, deal)
        return deal

    async def _get_chat(self, chat_id):
        cached = self._chat_cache.get(chat_id)
        if cached is not None:
            return cached
        account = self.fixer.account
        if account is None or not chat_id:
            return None
        chat = await asyncio.to_thread(account.get_chat, chat_id)
        self._chat_cache.set(chat_id, chat)
        return chat

    async def _get_item(self, item_id=None, slug=None):
        key = ("id", item_id) if item_id else ("slug", slug)
        cached = self._item_cache.get(key)
        if cached is not None:
            return cached
        account = self.fixer.account
        if account is None or not (item_id or slug):
            return None
        if item_id:
            item = await asyncio.to_thread(account.get_item, item_id)
        else:
            item = await asyncio.to_thread(account.get_item, slug=slug)
        self._item_cache.set(key, item)
        return item

    async def _get_my_items(self):
        cached = self._my_items_cache.get("page")
        if cached is not None:
            return cached
        account = self.fixer.account
        if account is None:
            return None
        page = await asyncio.to_thread(account.get_my_items, None, 100)
        self._my_items_cache.set("page", page)
        return page

    async def _full_deal(self, deal):
        """Полная сделка (с чатом и разделом) — один запрос на сделку благодаря кэшу.

        Сразу после оплаты Playerok иногда отдаёт сделку без чата/раздела — тогда одна
        повторная попытка через секунду, а неполный ответ в кэше не задерживается."""
        deal_id = getattr(deal, "id", None)
        if self.fixer.account is None or not deal_id:
            return None
        cached = self._deal_cache.get(deal_id)
        if cached is not None:
            return cached
        full = None
        for attempt in range(2):
            try:
                full = await self._get_deal(deal_id)
            except Exception as exc:
                logger.warning("[deal] get_deal({}) упал (попытка {}): {}", deal_id, attempt + 1, exc)
                full = None
            chat_id = getattr(getattr(full, "chat", None), "id", None)
            if full is not None and chat_id and _get_section_from_deal(full) != "Не определено":
                return full
            self._deal_cache.invalidate(deal_id)
            if attempt == 0:
                await asyncio.sleep(1)
        # Неполную сделку тоже запоминаем — иначе раздел и чат для одного уведомления
        # запрашивались бы по кругу.
        self._deal_cache.set(deal_id, full)
        return full

    async def _resolve_deal_chat_id(self, deal) -> str | None:
        """ID чата Playerok сделки: из события, иначе из полной сделки (через кэш)."""
        chat_id = getattr(getattr(deal, "chat", None), "id", None)
        if chat_id:
            return chat_id
        full = await self._full_deal(deal)
        return getattr(getattr(full, "chat", None), "id", None)

    async def _resolve_section_via_deal_api(self, deal) -> str:
        """Раздел (игра → категория) сделки: в WS-кадре его нет, берём из полной сделки (через кэш)."""
        section = _get_section_from_deal(deal)
        if section != "Не определено":
            return section
        return _get_section_from_deal(await self._full_deal(deal))

    # ------------------------------------------------------------------
    # Выплаты: сумма для уведомления
    # ------------------------------------------------------------------

    async def _fetch_latest_payout(self) -> dict:
        """Последняя выплата (сумма/способ/статус/дата) — тем же запросом, что страница кошелька
        на сайте: транзакции с `operation = WITHDRAW`. Берётся самая свежая проведённая
        (сообщение «выплата успешно проведена» приходит именно о ней), иначе просто самая свежая."""
        result: dict = {"amount": None, "method": None, "status": None, "date": None}
        account = self.fixer.account
        if account is None:
            return result
        try:
            page = await asyncio.to_thread(
                account.get_transactions, 5, None, {"operation": ["WITHDRAW"]}
            )
            txs = list(page.transactions) if page and page.transactions else []
        except Exception as exc:
            logger.warning("Не удалось получить выплаты (transactions/WITHDRAW): {}", exc)
            return result
        if not txs:
            logger.warning("Выплата не найдена: список транзакций WITHDRAW пуст")
            return result
        txs.sort(key=lambda t: str(getattr(t, "created_at", "") or ""), reverse=True)
        confirmed = [t for t in txs if getattr(getattr(t, "status", None), "name", None) == "CONFIRMED"]
        tx = confirmed[0] if confirmed else txs[0]
        provider = getattr(tx, "provider", None)
        result["amount"] = getattr(tx, "value", None)
        result["method"] = getattr(provider, "name", None) or getattr(tx, "provider_id", None)
        result["status"] = getattr(tx, "status", None)
        result["date"] = getattr(tx, "created_at", None)
        return result

    async def _notify_payout(self, message, chat) -> None:
        """Уведомление о выплате: сумма/способ/статус/дата — только те, что удалось получить."""
        l10n = self.fixer.l10n
        info = await self._fetch_latest_payout()
        text = _esc(_clean_payout_text(message.text or "")) or "…"
        remember = chat.id if chat is not None else None

        balance = None
        account = self.fixer.account
        if account and account.profile and account.profile.balance:
            bal = account.profile.balance
            balance = bal.available if bal.available is not None else bal.value

        details = build_payout_details(
            l10n,
            amount=info["amount"],
            method=_fmt_payout_method(info["method"]) if info["method"] is not None else None,
            status=_fmt_payout_status(info["status"]) if info["status"] is not None else None,
            date=_fmt_datetime(info["date"]) if info["date"] else None,
            balance=balance,
        )
        await self._send_all(
            l10n("notif_payout", details=details, text=text),
            remember_chat=remember,
            reply_markup=close_keyboard(l10n),
        )

    # ------------------------------------------------------------------
    # Снятие лота через 7 дней: какой товар имеется в виду
    # ------------------------------------------------------------------

    async def _resolve_expiring_item(self, message, chat):
        item = getattr(message, "item", None)
        if item and getattr(item, "name", None):
            return item

        slug = _extract_item_slug(getattr(message, "text", None), getattr(message, "buttons", None))
        if slug:
            account = self.fixer.account
            if account is not None:
                try:
                    linked = await self._get_item(slug=slug)
                    if linked and getattr(linked, "name", None):
                        logger.debug("Лот из ссылки: slug={} → {}", slug, linked.name)
                        return linked
                except Exception as exc:
                    logger.debug("Не удалось достать лот по ссылке (slug={}): {}", slug, exc)

        account = self.fixer.account
        if account is not None and chat is not None and getattr(chat, "id", None):
            try:
                full_chat = await self._get_chat(chat.id)
                last = getattr(full_chat, "last_message", None) if full_chat else None
                item = getattr(last, "item", None) if last else None
                if item and getattr(item, "name", None):
                    return item
            except Exception as exc:
                logger.debug("Не удалось достать лот из чата {}: {}", chat.id, exc)
        return None

    async def _find_my_item_by_name(self, name: str | None):
        """Ищет свой лот по точному названию (у ItemProfile есть ID и обложка)."""
        account = self.fixer.account
        if account is None or not name:
            return None
        try:
            page = await self._get_my_items()
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
        account = self.fixer.account
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
            full_item = await self._get_item(item_id)
            return _get_item_image(full_item)
        except Exception as exc:
            logger.debug("Не удалось получить обложку лота {}: {}", item_id, exc)
            return None

    async def _notify_item_expiring(self, message, chat) -> None:
        """Уведомление о скором снятии лота — с названием, разделом и ценой."""
        l10n = self.fixer.l10n
        item = await self._resolve_expiring_item(message, chat)
        text = _esc((message.text or "").strip()) or "…"
        remember = chat.id if chat is not None else None

        if item is None:
            await self._send_all(
                l10n("notif_item_expiring_plain", text=text), remember_chat=remember,
                reply_markup=close_keyboard(l10n),
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
            photo_url=photo,
            reply_markup=close_keyboard(l10n),
        )
    # ------------------------------------------------------------------
    # События Runner
    # ------------------------------------------------------------------

    async def notify_missed_deals(self, missed_deals: list) -> None:
        """
        Уведомляет админов о сделках, которые произошли, пока бот был выключен.
        Вызывается при старте Fixer — только информирует, автовыдачу не запускает.
        """
        if not missed_deals:
            return
        l10n = self.fixer.l10n
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

    # ------------------------------------------------------------------
    # Новая сделка
    # ------------------------------------------------------------------

    def _autodelivery_active(self, item_name: str | None) -> bool:
        """Авто-выдача ботом реально включена для этого лота (модуль включён и склад настроен)."""
        if not item_name or not self.fixer.settings.modules.autodelivery:
            return False
        return item_name in self.fixer.autodelivery_config.lots

    async def _notify_new_deal(self, deal) -> None:
        l10n = self.fixer.l10n
        photo = await self._resolve_item_image(getattr(deal, "item", None))
        section = await self._resolve_section_via_deal_api(deal)
        deal_chat_id = await self._resolve_deal_chat_id(deal)

        item_name = deal.item.name if deal and deal.item else None
        buyer = deal.user.username if deal and deal.user else "?"
        price = deal.item.price if deal and deal.item and getattr(deal.item, "price", None) is not None else "?"
        raw_status = getattr(getattr(deal, "raw_status", None), "name", None)

        text = build_new_deal_text(
            l10n,
            section=_esc(section),
            item=_esc(item_name or "?"),
            buyer=_esc(buyer),
            price=_esc(price),
            chat_id=_esc(deal_chat_id or "—"),
            autodelivery=self._autodelivery_active(item_name),
        )
        # Кнопки — пока сделка оплачена и ждёт выдачи; «Свернуть» есть всегда.
        deal_id = getattr(deal, "id", None) if raw_status == "PAID" else None
        sent = await self._send_all(text, photo_url=photo, remember_chat=deal_chat_id,
                                    reply_markup=new_deal_keyboard(l10n, deal_id))
        # Если лот уже успели восстановить — реакция (⚡/🤔/👎) встанет сразу.
        await self.deal_reactions.add_messages(self.bot, getattr(deal, "id", None), sent)

    async def react_deal(self, deal_id: str | None, emoji: str) -> None:
        """Ставит/заменяет реакцию на уведомлениях «Новая сделка» по этой сделке."""
        await self.deal_reactions.set(self.bot, deal_id, emoji)

    # ------------------------------------------------------------------
    # Новое сообщение: покупатель / поддержка / уведомления площадки
    # ------------------------------------------------------------------

    async def _chat_context(self, chat, message=None) -> tuple:
        """(ник покупателя, лот) для чата.

        Сначала — то, что пришло в самом событии; если чего-то не хватает — один запрос
        полного чата (через кэш, т.е. для следующих сообщений этого чата — без запросов)."""
        own_id = getattr(self.fixer.account, "id", None)
        buyer = chat_kinds.counterpart(chat, own_id)
        item = None
        if message is not None:
            item = getattr(message, "item", None) or getattr(getattr(message, "deal", None), "item", None)
        for deal in getattr(chat, "deals", None) or []:
            if item is None and getattr(deal, "item", None) is not None:
                item = deal.item
            if buyer is None and getattr(deal, "user", None) is not None and deal.user.id != own_id:
                buyer = deal.user

        chat_id = getattr(chat, "id", None)
        if (buyer is None or item is None or not getattr(item, "name", None)) and chat_id:
            try:
                full = await self._get_chat(chat_id)
            except Exception as exc:
                logger.debug("Не удалось получить чат {}: {}", chat_id, exc)
                full = None
            if full is not None:
                buyer = buyer or chat_kinds.counterpart(full, own_id)
                for deal in getattr(full, "deals", None) or []:
                    if (item is None or not getattr(item, "name", None)) and getattr(deal, "item", None):
                        item = deal.item
                    if buyer is None and getattr(deal, "user", None) is not None and deal.user.id != own_id:
                        buyer = deal.user
        return (getattr(buyer, "username", None) if buyer is not None else None), item

    @staticmethod
    def _message_text(message) -> str:
        if message.text:
            return _esc(message.text)
        if getattr(message, "images", None) or getattr(message, "file", None):
            return "🖼 <i>Фото</i>"
        return "…"

    async def _notify_new_message(self, event) -> None:
        l10n = self.fixer.l10n
        message = event.message
        chat = event.chat
        account = self.fixer.account
        if message is None:
            return
        own_id = getattr(account, "id", None)
        chat_id = getattr(chat, "id", None)

        # Свои исходящие и служебные маркеры ({{ITEM_PAID}}, {{ITEM_SENT}}…) — не уведомляем.
        if message.user is not None and message.user.id == own_id:
            return
        if _is_system_marker_message(message.text):
            logger.debug("Пропущено системное сообщение с маркером: {}", message.text)
            return

        kind = chat_kinds.chat_kind(chat, account)

        # «Смотрим чат…» / «Чат завершён» — действия сотрудника, без текста.
        action = chat_kinds.staff_event(message)
        if action:
            staff = chat_kinds.staff_display_name(message)
            if kind == chat_kinds.PM:
                buyer, _ = await self._chat_context(chat, message)
                place = l10n("notif_place_deal_chat", buyer=_esc(buyer or "?"))
            else:
                place = _esc(chat_kinds.SUPPORT_TITLE)
            key = "notif_staff_started" if action == "CHAT_STARTED" else "notif_staff_finished"
            await self._send_all(l10n(key, staff=_esc(staff), place=place), remember_chat=chat_id,
                                 reply_markup=close_keyboard(l10n))
            return

        # Выплата и «лот скоро снимут» — свои шаблоны.
        if _is_payout_message(message.text):
            await self._notify_payout(message, chat)
            return
        if _is_item_expiring_message(message.text):
            await self._notify_item_expiring(message, chat)
            return

        text = self._message_text(message)

        # Автоответ бота в чате поддержки («Как проходит сделка?» и т.п.) — как сообщение поддержки.
        if kind == chat_kinds.SUPPORT and message.user is None:
            await self._send_all(l10n("notif_support_message", staff=_esc(chat_kinds.SUPPORT_BOT), text=text),
                                 remember_chat=chat_id, reply_markup=close_keyboard(l10n))
            return

        # Уведомления площадки (чат NOTIFICATIONS, у сообщений нет автора).
        if kind == chat_kinds.SYSTEM or (message.user is None and kind != chat_kinds.PM):
            item = getattr(message, "item", None)
            lot = l10n("notif_system_lot", lot=_lot_link(item)) if item is not None else ""
            await self._send_all(l10n("notif_system_message", text=text, lot=lot), remember_chat=chat_id,
                                 reply_markup=close_keyboard(l10n))
            return

        # Сотрудник Playerok: в отдельном чате поддержки или внутри чата сделки.
        if kind == chat_kinds.SUPPORT or chat_kinds.is_staff_message(message):
            staff = chat_kinds.staff_display_name(message)
            if kind == chat_kinds.PM:
                buyer, item = await self._chat_context(chat, message)
                await self._send_all(l10n(
                    "notif_support_in_deal_chat",
                    staff=_esc(staff),
                    buyer=_esc(buyer or "?"),
                    item=_esc(getattr(item, "name", None) or "?"),
                    text=text,
                ), remember_chat=chat_id, reply_markup=close_keyboard(l10n))
            else:
                await self._send_all(l10n("notif_support_message", staff=_esc(staff), text=text),
                                     remember_chat=chat_id, reply_markup=close_keyboard(l10n))
            return

        # Обычное сообщение покупателя (без фото лота).
        username = message.user.username if message.user and message.user.username else "?"
        _, item = await self._chat_context(chat, message)
        await self._send_all(l10n(
            "notif_new_message",
            username=_esc(username),
            item=_esc(getattr(item, "name", None) or "?"),
            text=text,
        ), remember_chat=chat_id)

    async def on_event(self, event) -> None:
        l10n = self.fixer.l10n
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

        # NEW_DEAL и ITEM_PAID — одно уведомление: сделка без оплаты на Playerok не возникает,
        # второе из пары событий отсекается дедупликацией выше.
        if event_type in (EventTypes.NEW_DEAL, EventTypes.ITEM_PAID):
            deal = event.deal
            deal_chat_id = getattr(getattr(deal, "chat", None), "id", None)
            if deal_chat_id:
                # В чате появилась новая сделка — данные чата в кэше устарели.
                self._chat_cache.invalidate(deal_chat_id)
            if self._toggles.new_deal:
                await self._notify_new_deal(deal)

            # Уведомление «Товар выдан» — только для выдачи самим ботом (модуль авто-выдачи):
            # журнал выдач говорит «sent». Выдачу силами сайта (данные в карточке товара)
            # отдельно не дублируем.
            if event_type is EventTypes.ITEM_PAID and deal is not None:
                manager = self.fixer.autodelivery_manager
                if (self._toggles.delivery and manager is not None
                        and manager.ledger is not None
                        and manager.ledger.get_state(deal.id) == "sent"):
                    item_name = deal.item.name if deal.item else "?"
                    section = await self._resolve_section_via_deal_api(deal)
                    await self._send_all(l10n(
                        "notif_delivery_ok",
                        section=_esc(section),
                        item=_esc(item_name),
                        stock=manager.get_stock_size(item_name),
                    ))

        elif event_type is EventTypes.NEW_MESSAGE and self._toggles.new_message:
            await self._notify_new_message(event)

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
            account = self.fixer.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal and deal.item else "?"

            # Если раздел или имя лота не определились — пробуем через API
            if section == "Не определено" or item_name == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                # Пробуем получить имя лота
                try:
                    full_deal = await self._get_deal(deal.id)
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
            account = self.fixer.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"
            price = deal.item.price if deal.item and getattr(deal.item, "price", None) is not None else "?"
            buyer = deal.user.username if deal and deal.user else "?"
            deal_chat_id = await self._resolve_deal_chat_id(deal)

            # Если раздел, имя лота или покупатель не определились — пробуем через API
            if section == "Не определено" or item_name == "?" or buyer == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                try:
                    full_deal = await self._get_deal(deal.id)
                    if full_deal:
                        if getattr(full_deal, "item", None):
                            item_name = getattr(full_deal.item, "name", item_name)
                            price = getattr(full_deal.item, "price", price) or price
                        if getattr(full_deal, "user", None):
                            buyer = getattr(full_deal.user, "username", None) or buyer
                except Exception:
                    pass

            # Обложка лота для уведомления (None, если достать не удалось)
            photo = await self._resolve_item_image(deal.item if deal else None)

            await self._send_all(l10n(
                "notif_deal_confirmed",
                section=_esc(section),
                item=_esc(item_name),
                buyer=_esc(buyer),
                price=_esc(price),
                chat_id=_esc(deal_chat_id or "—"),
            ), photo_url=photo)

        elif event_type is EventTypes.DEAL_ROLLED_BACK and self._toggles.deal_rolled_back:
            deal = event.deal
            account = self.fixer.account
            section = _get_section_from_deal(deal)
            item_name = deal.item.name if deal.item else "?"

            # Если раздел или имя лота не определились — пробуем через API
            if section == "Не определено" or item_name == "?":
                api_section = await self._resolve_section_via_deal_api(deal)
                if api_section != "Не определено":
                    section = api_section
                try:
                    full_deal = await self._get_deal(deal.id)
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
            buyer_id = getattr(deal.user, "id", None) if deal is not None and deal.user is not None else None
            if self.fixer.is_blacklisted(buyer, buyer_id):
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
        """Уведомление о старте Fixer (аккаунт, баланс, модули + пропущенные сделки)."""
        account = self.fixer.account
        profile = getattr(account, "profile", None)
        balance = profile.balance.format_balance(detailed=True) if profile is not None and profile.balance is not None else "?"
        modules_settings = self.fixer.settings.modules
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

        text = build_started_text(
            self.fixer.l10n,
            username=account.username if account else "?",
            balance=balance,
            missed_deals=missed_count,
            unread_messages=unread_count,
            modules=modules,
            connected=self.fixer.playerok_connected,
        )
        await self._send_all(text, reply_markup=started_keyboard(self.fixer.l10n))

    async def notify_error(self, error_text: str) -> None:
        if self._toggles.errors:
            await self._send_all(self.fixer.l10n("notif_error", error=_esc(error_text)))

    async def notify_stock_empty(self, item_name: str) -> None:
        if self._toggles.stock_empty:
            await self._send_all(self.fixer.l10n("notif_stock_empty", item=_esc(item_name)))

    async def notify_restore_ok(self, item_name: str, new_item_id: str) -> None:
        await self._send_all(self.fixer.l10n("notif_restore_ok", item=_esc(item_name),
                                                item_id=_esc(new_item_id)))

    async def notify_restore_failed(self, item_name: str, error_text: str) -> None:
        await self._send_all(self.fixer.l10n("notif_restore_fail", item=_esc(item_name),
                                                error=_esc(error_text)))

    async def notify_restore_premium_fallback(self, item_name: str, new_item_id: str,
                                              reason: str) -> None:
        await self._send_all(self.fixer.l10n(
            "notif_restore_premium_fallback",
            item=_esc(item_name),
            item_id=_esc(new_item_id),
            reason=_esc(reason or "неизвестная причина"),
        ))