"""
Автоответчик: отвечает заготовленным текстом на команды в чатах Playerok.

Команды хранятся в `configs/autoresponse.toml` (`[commands]`: команда = текст ответа) и
редактируются из TG-панели. Сравнение команд регистронезависимое, срабатывание — если текст
сообщения начинается с команды. В тексте ответа работают переменные `$username`, `$chat_id`,
`$date`, `$time`. Встроенная команда `!команды`/`!commands` выводит список доступных команд.
"""
from __future__ import annotations

import asyncio
import datetime
from string import Template

from loguru import logger

from playerokapi.common.enums import EventTypes

from .base import BaseModule

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
        """Автоответчик больше не реагирует на сообщения покупателей.

        Теперь это личная библиотека шаблонов продавца: команды срабатывают
        только когда продавец пишет ``!!команда`` в живом диалоге
        (см. cardinal/tg/handlers/chats.py).
        """
        return