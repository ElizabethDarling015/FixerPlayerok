"""
Послепродажные сообщения (идея из FunPayCardinal): после подтверждения сделки поблагодарить
покупателя и попросить отзыв; на новый отзыв ответить в чате в зависимости от оценки.

Тексты настраиваются в секции `[postsale]` конфига `configs/main.toml` (пустой текст —
соответствующая реакция выключена). Переменные: в благодарности за сделку — `$username` и
`$item_name`, в реакциях на отзыв — `$username` и `$rating`.

Дедупликация — in-memory: `Runner` эмитит смену статуса сделки и новый отзыв по одному разу,
set страхует от пары событий CONFIRMED + CONFIRMED_AUTOMATICALLY по одной и той же сделке.

Самое хрупкое место — поиск чата покупателя для реакции на отзыв: `parser.review` сознательно
не заполняет `review.deal` (защита от циклического парсинга ItemDeal <-> Review), поэтому чат
ищется перебором страниц `Account.get_chats()` по автору отзыва. Не нашли — логируем и молча
пропускаем, бот не падает.
"""
from __future__ import annotations

import asyncio
import contextlib
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes, ItemDealDirections

from ..stats_store import ACTION_POSTSALE
from .base import BaseModule
from .humanize import sleep_before_reply

#: События подтверждения сделки, на которые реагирует модуль.
_CONFIRMED_EVENTS = (EventTypes.DEAL_CONFIRMED, EventTypes.DEAL_CONFIRMED_AUTOMATICALLY)


class PostsaleModule(BaseModule):
    name = "postsale"

    #: Предохранитель перебора чатов при поиске автора отзыва: 20 страниц × 50 = 1000 чатов.
    CHAT_SEARCH_MAX_PAGES = 20

    def __init__(self, cardinal):
        super().__init__(cardinal)
        self._thanked_deals: set[str] = set()
        self._reacted_reviews: set[str] = set()

    # ------------------------------------------------------------------
    # Реакция 1: сделка подтверждена — благодарность + просьба оставить отзыв
    # ------------------------------------------------------------------

    def format_confirmed_text(self, username: str, item_name: str) -> str:
        """Подставляет `$username`/`$item_name` в текст благодарности за сделку."""
        return Template(self.cardinal.settings.postsale.confirmed_text).safe_substitute(
            username=username, item_name=item_name,
        )

    async def _handle_deal_confirmed(self, event) -> None:
        if not self.cardinal.settings.postsale.confirmed_text.strip():
            return  # пустой текст — благодарность выключена
        deal = event.deal
        if deal is None or not getattr(deal, "id", None):
            return
        # Благодарим только за продажи: direction=IN — наша собственная покупка.
        direction = getattr(deal, "direction", None)
        if direction is not None and direction != ItemDealDirections.OUT:
            return
        buyer = getattr(deal, "user", None)
        username = getattr(buyer, "username", None)
        if self.cardinal.is_blacklisted(username):
            return  # покупатель в чёрном списке — не благодарим
        chat = getattr(deal, "chat", None)
        chat_id = getattr(chat, "id", None)
        if not chat_id:
            logger.warning("Послепродажка: у сделки {} нет чата — благодарность пропущена", deal.id)
            return
        if deal.id in self._thanked_deals:
            return  # уже благодарили (второе событие CONFIRMED/CONFIRMED_AUTOMATICALLY)
        self._thanked_deals.add(deal.id)

        item = getattr(deal, "item", None)
        text = self.format_confirmed_text(
            username=username or "?",
            item_name=getattr(item, "name", None) or "?",
        )
        logger.info("Послепродажка: благодарим {} за сделку {} (чат {})", username, deal.id, chat_id)
        # «Человеческая» пауза перед ответом — мгновенный ответ выдаёт автоматизацию.
        await sleep_before_reply(getattr(self.cardinal.settings, "humanize", None), text)
        await asyncio.to_thread(self.cardinal.account.send_message, chat_id, text)
        self._record_stats()

    # ------------------------------------------------------------------
    # Реакция 2: новый отзыв — благодарность либо «расскажите, что не так»
    # ------------------------------------------------------------------

    def pick_review_text(self, rating: int | None) -> str:
        """Выбирает шаблон реакции по оценке: >= 4 (или без оценки) — благодарность, <= 3 — «решим проблему»."""
        settings = self.cardinal.settings.postsale
        if rating is not None and rating <= 3:
            return settings.review_bad_text
        return settings.review_good_text

    def format_review_text(self, template: str, username: str, rating) -> str:
        """Подставляет `$username`/`$rating` в текст реакции на отзыв."""
        return Template(template).safe_substitute(username=username, rating=rating)

    def _find_review_chat_id(self, review) -> str | None:
        """
        Ищет ID чата с автором отзыва (синхронно, вызывается через `asyncio.to_thread`).

        Сначала пробует `review.deal.chat.id` (на случай, если отзыв пришёл вместе со сделкой),
        затем перебирает страницы `Account.get_chats()` и ищет автора среди участников чатов —
        `parser.review` при сборке из testimonials не заполняет `deal`, так что обычно работает
        именно перебор. Не нашли — `None`.
        """
        deal = getattr(review, "deal", None)
        chat_id = getattr(getattr(deal, "chat", None), "id", None)
        if chat_id:
            return chat_id

        creator = getattr(review, "creator", None)
        creator_id = getattr(creator, "id", None)
        creator_name = (getattr(creator, "username", None) or "").casefold()
        if not creator_id and not creator_name:
            return None

        account = self.cardinal.account
        after_cursor = None
        for _ in range(self.CHAT_SEARCH_MAX_PAGES):
            try:
                page = account.get_chats(count=50, after_cursor=after_cursor)
            except Exception:
                logger.exception("Послепродажка: не удалось получить список чатов для поиска автора отзыва")
                return None
            if not page:
                return None
            for chat in page.chats:
                for user in getattr(chat, "users", None) or []:
                    if creator_id and getattr(user, "id", None) == creator_id:
                        return chat.id
                    username = getattr(user, "username", None)
                    if creator_name and username and username.casefold() == creator_name:
                        return chat.id
            if not page.page_info or not page.page_info.has_next_page:
                return None
            next_cursor = page.page_info.end_cursor
            if not next_cursor or next_cursor == after_cursor:
                return None
            after_cursor = next_cursor
        return None

    async def _handle_new_review(self, event) -> None:
        review = event.review
        if review is None or not getattr(review, "id", None):
            return
        rating = getattr(review, "rating", None)
        template = self.pick_review_text(rating)
        if not template.strip():
            return  # пустой текст — реакция на такие отзывы выключена
        creator = getattr(review, "creator", None)
        username = getattr(creator, "username", None)
        if self.cardinal.is_blacklisted(username):
            return  # автор отзыва в чёрном списке — не отвечаем
        if review.id in self._reacted_reviews:
            return  # на этот отзыв уже отвечали
        self._reacted_reviews.add(review.id)

        chat_id = await asyncio.to_thread(self._find_review_chat_id, review)
        if not chat_id:
            logger.warning("Послепродажка: не найден чат с автором отзыва {} ({}) — реакция пропущена",
                           review.id, username or "?")
            return

        text = self.format_review_text(template, username=username or "?",
                                       rating=rating if rating is not None else "?")
        logger.info("Послепродажка: отвечаем на отзыв {} ({}★) от {} в чате {}",
                    review.id, rating, username, chat_id)
        # «Человеческая» пауза перед ответом — мгновенный ответ выдаёт автоматизацию.
        await sleep_before_reply(getattr(self.cardinal.settings, "humanize", None), text)
        await asyncio.to_thread(self.cardinal.account.send_message, chat_id, text)
        self._record_stats()

    # ------------------------------------------------------------------
    # Общее
    # ------------------------------------------------------------------

    def _record_stats(self) -> None:
        stats = getattr(self.cardinal, "stats", None)
        if stats is not None:
            with contextlib.suppress(Exception):
                stats.record(ACTION_POSTSALE)

    async def on_event(self, event) -> None:
        if not self.enabled:
            return
        if event.type in _CONFIRMED_EVENTS:
            await self._handle_deal_confirmed(event)
        elif event.type is EventTypes.NEW_REVIEW:
            await self._handle_new_review(event)
