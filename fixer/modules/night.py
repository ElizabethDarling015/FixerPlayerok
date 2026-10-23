"""Ночные сообщения покупателю (один тумблер «🌙 Ночное сообщение»).

* После оплаты лота ночью — `[night] text` в чат сделки, через несколько секунд (чтобы прийти
  после товара от автовыдачи). На одну сделку — один раз.
* Когда покупатель пишет ночью (по старой или новой сделке) — `[night] reply_text`, «я сплю».
  На один чат — не чаще раза в `REPLY_COOLDOWN` (сообщение после оплаты тоже считается).

Окно (по умолчанию 22:00–09:00) — в `[night]` main.toml, тексты меняются из Telegram
(«Глобальные переключатели» → «✏️ Текст»). Время — по часовому поясу продавца
(`[digest] timezone`). Поддержка, уведомления Playerok и сотрудники в чате сделки — без ответа.
"""
from __future__ import annotations

import asyncio
import datetime
import time
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes, ItemDealDirections

from ..sales_stats import seller_tz
from ..tg import chat_kinds
from .base import BaseModule

#: Пауза перед отправкой — чтобы сообщение пришло после выдачи товара.
SEND_DELAY = 3.0
#: Ответ «я сплю» в один чат — не чаще, чем раз в столько секунд.
REPLY_COOLDOWN = 60 * 60
#: Пауза перед ответом «я сплю».
REPLY_DELAY = 2.0


def _parse_hhmm(value: str) -> datetime.time:
    hours, minutes = (int(part) for part in value.split(":"))
    return datetime.time(hours, minutes)


def is_night(now: datetime.time, start: str, end: str) -> bool:
    """Попадает ли время в окно [start, end); окно может переходить через полночь."""
    begin, finish = _parse_hhmm(start), _parse_hhmm(end)
    if begin == finish:
        return False
    if begin < finish:
        return begin <= now < finish
    return now >= begin or now < finish


class NightMessageModule(BaseModule):
    name = "night"

    def __init__(self, fixer):
        super().__init__(fixer)
        self._sent_deals: set[str] = set()
        self.delay = SEND_DELAY
        self.reply_delay = REPLY_DELAY
        #: Чат Playerok → когда ему в последний раз ушло ночное сообщение (любое из двух).
        self._last_sent: dict[str, float] = {}

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(seller_tz(self.fixer.settings))

    def render(self, username: str | None, item: str | None) -> str:
        return Template(self.fixer.settings.night.text).safe_substitute(
            username=username or "", item=item or "",
        )

    async def on_event(self, event) -> None:
        if event.type is EventTypes.NEW_MESSAGE:
            await self._on_message(event)
            return
        if event.type is not EventTypes.ITEM_PAID:
            return
        deal = getattr(event, "deal", None)
        if deal is None or not getattr(deal, "id", None) or deal.id in self._sent_deals:
            return
        if deal.direction is not None and deal.direction is not ItemDealDirections.OUT:
            return  # только свои продажи
        night = self.fixer.settings.night
        now = self._now()
        if not is_night(now.time(), night.start, night.end):
            return
        # Дальше — ночная оплата: каждое решение пишем в лог, чтобы было видно, почему не ушло.
        if not self.enabled:
            logger.info("[night] Сделка {} оплачена ночью ({:%H:%M}), но ночное сообщение выключено", deal.id, now)
            return
        chat = getattr(event, "chat", None)
        chat_id = getattr(chat, "id", None) or getattr(getattr(deal, "chat", None), "id", None)
        if not chat_id:
            try:
                full = await asyncio.to_thread(self.fixer.account.get_deal, deal.id)
                chat_id = getattr(getattr(full, "chat", None), "id", None)
            except Exception as exc:
                logger.warning("[night] Чат сделки {} не загрузился: {}", deal.id, exc)
        if not chat_id:
            logger.warning("[night] Сделка {} оплачена ночью, но чат сделки не найден — сообщение не отправлено",
                           deal.id)
            return
        logger.info("[night] Сделка {} оплачена ночью ({:%H:%M}) — ночное сообщение через {:g} с",
                    deal.id, now, self.delay)
        self._sent_deals.add(deal.id)
        username = getattr(getattr(deal, "user", None), "username", None)
        item = getattr(getattr(deal, "item", None), "name", None)
        text = self.render(username, item)
        self._last_sent[chat_id] = time.time()
        self.fixer.spawn(self._send_later(chat_id, text, deal.id))

    # ------------------------------------------------------------------
    # Покупатель пишет ночью → «я сплю» (не чаще раза в час на чат)
    # ------------------------------------------------------------------

    def render_reply(self, username: str | None) -> str:
        return Template(self.fixer.settings.night.reply_text).safe_substitute(username=username or "", item="")

    async def _on_message(self, event) -> None:
        message = getattr(event, "message", None)
        chat = getattr(event, "chat", None)
        chat_id = getattr(chat, "id", None)
        if message is None or not chat_id:
            return
        author = getattr(message, "user", None)
        account = self.fixer.account
        if author is None or getattr(author, "id", None) == getattr(account, "id", None):
            return  # свои сообщения и системные события
        text = getattr(message, "text", None) or ""
        if text.startswith("{{") and text.endswith("}}"):
            return  # служебные маркеры Playerok ({{ITEM_PAID}} и т.п.)
        if chat_kinds.chat_kind(chat, account) != chat_kinds.PM:
            return  # поддержка и уведомления Playerok
        if chat_kinds.is_staff_message(message) or chat_kinds.staff_event(message):
            return  # сотрудник Playerok в чате сделки
        night = self.fixer.settings.night
        now = self._now()
        if not self.enabled or not is_night(now.time(), night.start, night.end):
            return
        last = self._last_sent.get(chat_id, 0)
        if time.time() - last < REPLY_COOLDOWN:
            logger.debug("[night] Покупатель {} пишет ночью — «я сплю» уже был в этот час", chat_id)
            return
        self._last_sent[chat_id] = time.time()
        username = getattr(author, "username", None)
        logger.info("[night] Покупатель {} пишет ночью ({:%H:%M}) — отвечаю «я сплю»", username or chat_id, now)
        self.fixer.spawn(self._reply_later(chat_id, self.render_reply(username)))

    async def _reply_later(self, chat_id: str, text: str) -> None:
        await asyncio.sleep(self.reply_delay)
        account = self.fixer.account
        if account is None:
            return
        try:
            await asyncio.to_thread(account.send_message, chat_id, text)
            logger.info("[night] Ответ «я сплю» отправлен в чат {}", chat_id)
        except Exception:
            logger.exception("[night] Не удалось отправить ответ «я сплю» в чат {}", chat_id)

    async def _send_later(self, chat_id: str, text: str, deal_id: str) -> None:
        await asyncio.sleep(self.delay)
        account = self.fixer.account
        if account is None:
            return
        try:
            await asyncio.to_thread(account.send_message, chat_id, text)
            logger.info("[night] Ночное сообщение отправлено в чат {} (сделка {})", chat_id, deal_id)
        except Exception:
            logger.exception("[night] Не удалось отправить ночное сообщение в чат {}", chat_id)
