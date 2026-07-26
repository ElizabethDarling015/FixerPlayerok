"""
Автоответчик: отвечает заготовленным текстом на команды в чатах Playerok.

Команды хранятся в `configs/autoresponse.toml` (`[commands]`: команда = текст ответа) и
редактируются из TG-панели. Сравнение команд регистронезависимое, срабатывание — если текст
сообщения начинается с команды. В тексте ответа работают переменные `$username`, `$chat_id`,
`$date`, `$time`. Встроенная команда `!команды`/`!commands` выводит список доступных команд.
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes

from ..stats_store import ACTION_AUTORESPONSE
from .base import BaseModule
from .humanize import sleep_before_reply

#: Встроенные команды-списки (не настраиваются, всегда доступны при включённом модуле).
BUILTIN_LIST_COMMANDS = ("!команды", "!commands")


class AutoResponseModule(BaseModule):
    name = "autoresponse"

    def format_response(self, template: str, username: str, chat_id: str) -> str:
        """Подставляет переменные `$username`/`$chat_id`/`$date`/`$time` в текст ответа."""
        now = datetime.datetime.now()
        return Template(template).safe_substitute(
            username=username,
            chat_id=chat_id,
            date=now.strftime("%d.%m.%Y"),
            time=now.strftime("%H:%M"),
        )

    def match_command(self, text: str) -> str | None:
        """Возвращает команду из конфига, с которой начинается текст (без учёта регистра)."""
        lowered = text.strip().lower()
        for command in self.cardinal.autoresponse_config.commands:
            if lowered.startswith(command.lower()):
                return command
        for command in BUILTIN_LIST_COMMANDS:
            if lowered.startswith(command):
                return command
        return None

    def build_reply(self, command: str, username: str, chat_id: str) -> str:
        """Строит текст ответа для найденной команды (включая встроенный список команд)."""
        commands = self.cardinal.autoresponse_config.commands
        if command in BUILTIN_LIST_COMMANDS:
            known = "\n".join(sorted(commands)) or "—"
            return self.cardinal.l10n("ar_builtin_commands_response", commands=known)
        return self.format_response(commands[command], username=username, chat_id=chat_id)

    async def on_event(self, event) -> None:
        if not self.enabled or event.type is not EventTypes.NEW_MESSAGE:
            return
        message = event.message
        account = self.cardinal.account
        if not message or not message.text:
            return
        if message.user is None or message.user.id == account.id:
            return  # своё сообщение или системное — не отвечаем
        if self.cardinal.is_blacklisted(message.user.username):
            return  # покупатель в чёрном списке — игнорируем

        command = self.match_command(message.text)
        if command is None:
            return

        username = message.user.username or "?"
        reply = self.build_reply(command, username=username, chat_id=event.chat.id)
        logger.info("Автоответчик: команда {!r} от {} в чате {}", command, username, event.chat.id)
        # «Человеческая» пауза перед ответом — мгновенный ответ выдаёт автоматизацию.
        await sleep_before_reply(getattr(self.cardinal.settings, "humanize", None), reply)
        await asyncio.to_thread(account.send_message, event.chat.id, reply)
        stats = getattr(self.cardinal, "stats", None)
        if stats is not None:
            with contextlib.suppress(Exception):
                stats.record(ACTION_AUTORESPONSE)
