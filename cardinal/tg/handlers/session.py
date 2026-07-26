"""
Замена протухшего токена Playerok из Telegram.

Два пути (оба только для админов — доступ фильтрует `AuthMiddleware`):

- команда `/token <значение>` — новый token (голый JWT `eyJ...`) или полная строка cookies;
- reply на уведомление о протухшей сессии (`Notifier.notify_session_expired` запоминает свои
  сообщения в `Notifier.session_expired_messages` — аналог `reply_map` для ответов в чаты).

Логика: `Account.update_cookies()` → проверочный `Account.get()`. Успех — cookies сохраняются
в `configs/main.toml` (секция `[playerok]`), текущее WS-соединение Runner закрывается (оно само
переподключится уже с новыми cookies). Провал — старые cookies возвращаются на место, конфиг
не трогается. Сам токен в логи не пишется.
"""
from __future__ import annotations

import asyncio
import contextlib
import html

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger

from ...settings import save_main_settings

router = Router(name="session")


async def apply_new_cookies(message: Message, raw_value: str, cardinal) -> None:
    """
    Общая логика замены cookies: обновить, проверить авторизацию, сохранить конфиг.

    При любой ошибке проверки старые cookies возвращаются на место, конфиг не трогается.
    """
    l10n = cardinal.l10n
    account = cardinal.account
    old_cookies = dict(account.cookies)
    try:
        account.update_cookies(raw_value)
        await asyncio.to_thread(account.get)
    except Exception as exc:
        account.cookies = old_cookies
        # Само значение токена в лог не пишем — это секрет.
        logger.warning("Не удалось обновить сессию Playerok из TG: {}", exc)
        await message.answer(l10n("session_update_failed", error=html.escape(str(exc))))
        return

    # Успех: фиксируем новые cookies в настройках и в configs/main.toml.
    cardinal.settings.playerok.cookies = account._cookie_header()
    save_main_settings(cardinal.settings)

    # Закрываем текущее WS-соединение Runner — оно переподключится с новыми cookies.
    runner = getattr(cardinal, "runner", None)
    ws = getattr(runner, "_ws", None)
    if ws is not None:
        with contextlib.suppress(Exception):
            ws.close()

    logger.success("Сессия Playerok обновлена из TG, авторизованы как {}", account.username)
    await message.answer(l10n("session_updated", username=html.escape(str(account.username))))


@router.message(Command("token"))
async def cmd_token(message: Message, command: CommandObject, cardinal) -> None:
    """Команда `/token <значение>` — заменить token/cookies аккаунта Playerok."""
    raw_value = (command.args or "").strip()
    if not raw_value:
        await message.answer(cardinal.l10n("session_token_usage"))
        return
    await apply_new_cookies(message, raw_value, cardinal)


def is_session_reply(message: Message, notifier) -> bool:
    """Фильтр: сообщение — reply на уведомление о протухшей сессии (иначе пропускаем дальше)."""
    reply = message.reply_to_message
    return (reply is not None
            and (message.chat.id, reply.message_id) in notifier.session_expired_messages)


@router.message(F.reply_to_message, F.text, is_session_reply)
async def on_session_reply(message: Message, cardinal) -> None:
    """Reply на уведомление о протухшей сессии — текст ответа считается новым token/cookies."""
    await apply_new_cookies(message, message.text.strip(), cardinal)
