"""Реакции Telegram, которые ставит Fixer.

Бот может поставить на сообщение только одну реакцию (ограничение Telegram для ботов) и
только из стандартного набора эмодзи, но может её заменить.

На ваши сообщения покупателю (reply на уведомление и режим диалога в «Чатах»):

* 👍 — отправлено;
* 🤷 — не тот чат (reply на сводку/меню, на уведомление площадки, куда писать нельзя) или
  Playerok сам не принял сообщение — во втором случае ещё приходит просьба посмотреть лог;
* 🤬 — нет связи с Playerok (бот офлайн, таймаут, обрыв, защита сайта).

На уведомление «Новая сделка» — когда модуль «Автовосстановление» выставил лот заново:

* ⚡ — восстановлен (в том числе если позже на сайте докупили премиум к бесплатному);
* 🤔 — восстановлен бесплатно (премиум оплатить не получилось);
* 👎 — восстановить не удалось.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import suppress

from aiogram.types import ReactionTypeEmoji
from loguru import logger

from playerokapi.common.exceptions import (
    BotCheckDetectedException,
    NotInitiatedError,
    RequestFailedError,
    RequestSendingError,
)

from ..settings import STORAGE_DIR

SENT = "👍"
WRONG_CHAT = "🤷"
NO_CONNECTION = "🤬"

RESTORED = "⚡"
RESTORED_FREE = "🤔"
RESTORE_FAILED = "👎"

#: Ошибки, означающие «до Playerok не достучались» (а не «Playerok отказал»).
_CONNECTION_ERRORS = (RequestSendingError, BotCheckDetectedException, NotInitiatedError,
                      ConnectionError, TimeoutError, OSError)


def is_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, RequestFailedError):
        # 403/429 — защита сайта и лимиты, 5xx — сервер лежит; прочие 4xx — отказ по существу.
        code = exc.status_code or 0
        return code in (403, 408, 429) or code >= 500
    return isinstance(exc, _CONNECTION_ERRORS)


async def react(bot, chat_id: int, message_id: int, emoji: str) -> bool:
    """Ставит (заменяет) реакцию. False — Telegram не дал (сообщение удалено и т.п.)."""
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id,
                                       reaction=[ReactionTypeEmoji(emoji=emoji)])
        return True
    except Exception as exc:
        logger.debug("Реакция {} на сообщение {} не поставилась: {}", emoji, message_id, exc)
        return False


def is_system_chat(fixer, chat_id: str | None) -> bool:
    """Чат «Уведомления Playerok» — туда писать нельзя."""
    profile = getattr(getattr(fixer, "account", None), "profile", None)
    return bool(chat_id) and chat_id == getattr(profile, "system_chat_id", None)


def is_offline(fixer) -> bool:
    return getattr(fixer, "account", None) is None or not getattr(fixer, "playerok_connected", True)


async def _mark(message, emoji: str, fallback_text: str | None = None) -> None:
    """Реакция на ваше сообщение; если Telegram её не принял — короткий текст вместо неё."""
    if not await react(message.bot, message.chat.id, message.message_id, emoji) and fallback_text:
        with suppress(Exception):
            await message.answer(fallback_text)


async def precheck(message, fixer, chat_id: str | None) -> bool:
    """Можно ли вообще отправлять: чат определён и он не «Уведомления Playerok» (иначе 🤷),
    Playerok подключён (иначе 🤬)."""
    l10n = fixer.l10n
    if not chat_id or is_system_chat(fixer, chat_id):
        await _mark(message, WRONG_CHAT, l10n("reply_unknown"))
        return False
    if is_offline(fixer):
        await _mark(message, NO_CONNECTION, l10n("reply_offline"))
        return False
    return True


async def deliver(message, fixer, chat_id: str, text: str | None = None, image: bytes | None = None,
                  check: bool = True) -> bool:
    """Отправляет ваше сообщение в чат Playerok и отмечает результат реакцией."""
    l10n = fixer.l10n
    if check and not await precheck(message, fixer, chat_id):
        return False
    try:
        if image is not None:
            await asyncio.to_thread(fixer.account.send_message, chat_id, text, image)
        else:
            await asyncio.to_thread(fixer.account.send_message, chat_id, text)
    except Exception as exc:
        logger.exception("Не удалось отправить сообщение в чат Playerok {}", chat_id)
        if is_connection_error(exc):
            await _mark(message, NO_CONNECTION, l10n("reply_offline"))
        else:
            await _mark(message, WRONG_CHAT)
            with suppress(Exception):
                await message.answer(l10n("reply_refused"))
        return False
    await _mark(message, SENT, l10n("reply_sent"))
    return True


DEAL_REACTIONS_FILE = os.path.join(STORAGE_DIR, "deal_reactions.json")
#: Сколько последних сделок помнить (уведомления старше давно не нужны).
DEAL_REACTIONS_LIMIT = 300


class DealReactions:
    """Какие сообщения в TG — уведомления о сделке и какую реакцию на них держать.

    Восстановление лота может закончиться раньше, чем уйдёт уведомление о сделке, поэтому
    реакция запоминается и ставится, как только уведомление появится. Хранится в файле —
    переживает перезапуск (например, проверку премиума через несколько часов)."""

    def __init__(self, path: str | None = None):
        self.path = path or DEAL_REACTIONS_FILE
        self.data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        with suppress(Exception):
            if os.path.isfile(self.path):
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    return raw
        return {}

    def _save(self) -> None:
        # Порядок вставки = возраст: старые сделки отрезаем.
        while len(self.data) > DEAL_REACTIONS_LIMIT:
            self.data.pop(next(iter(self.data)))
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception as exc:
            logger.debug("Не удалось сохранить реакции сделок: {}", exc)

    def _entry(self, deal_id: str) -> dict:
        return self.data.setdefault(deal_id, {"messages": [], "emoji": None})

    async def add_messages(self, bot, deal_id: str | None, messages: list[tuple[int, int]]) -> None:
        """Уведомление о сделке отправлено; если реакция уже ждёт — ставим её."""
        if not deal_id or not messages:
            return
        entry = self._entry(deal_id)
        entry["messages"].extend([list(m) for m in messages])
        self._save()
        if entry["emoji"]:
            for chat_id, message_id in messages:
                await react(bot, chat_id, message_id, entry["emoji"])

    async def set(self, bot, deal_id: str | None, emoji: str) -> None:
        if not deal_id:
            return
        entry = self._entry(deal_id)
        entry["emoji"] = emoji
        self._save()
        for chat_id, message_id in entry["messages"]:
            await react(bot, chat_id, message_id, emoji)

    def get(self, deal_id: str) -> str | None:
        return (self.data.get(deal_id) or {}).get("emoji")
