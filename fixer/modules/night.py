"""Ночное сообщение: покупателю, оплатившему лот ночью, приходит отдельное сообщение.

Окно (по умолчанию 22:00–09:00) и текст — в `[night]` main.toml, текст меняется и из
Telegram («Глобальные переключатели» → «✏️ Ночное сообщение»). Время — по часовому поясу
продавца (`[digest] timezone`). Сообщение уходит в чат сделки через несколько секунд после
оплаты, чтобы прийти после товара от автовыдачи. На одну сделку — один раз.
"""
from __future__ import annotations

import asyncio
import datetime
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes, ItemDealDirections

from ..sales_stats import seller_tz
from .base import BaseModule

#: Пауза перед отправкой — чтобы сообщение пришло после выдачи товара.
SEND_DELAY = 3.0


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

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(seller_tz(self.fixer.settings))

    def render(self, username: str | None, item: str | None) -> str:
        return Template(self.fixer.settings.night.text).safe_substitute(
            username=username or "", item=item or "",
        )

    async def on_event(self, event) -> None:
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
        self.fixer.spawn(self._send_later(chat_id, text, deal.id))

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
