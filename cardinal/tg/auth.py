"""
Авторизация в Telegram-панели: доступ только администраторам.

Администраторы — это ID из `configs/main.toml` (`[telegram] admin_ids`) плюс привязанные
по секретному коду (код печатается в консоль Cardinal при старте; привязанные ID хранятся
в `storage/tg_admins.json`, чтобы пережить перезапуск).
"""
from __future__ import annotations

import json
import os
import secrets

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from loguru import logger

ADMINS_FILE = os.path.join("storage", "tg_admins.json")


class TgAdmins:
    """Реестр администраторов панели (конфиг + привязанные кодом)."""

    def __init__(self, config_ids: list[int], storage_file: str = ADMINS_FILE):
        self.config_ids: set[int] = set(config_ids)
        self.storage_file = storage_file
        self.secret_code = secrets.token_hex(4)
        self._bound: set[int] = set()
        if os.path.isfile(storage_file):
            try:
                with open(storage_file, encoding="utf-8") as f:
                    self._bound = {int(x) for x in json.load(f)}
            except Exception:
                logger.exception("Не удалось прочитать {} — список привязанных админов сброшен",
                                 storage_file)

    @property
    def all_ids(self) -> set[int]:
        return self.config_ids | self._bound

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.all_ids

    def bind(self, user_id: int) -> None:
        """Привязывает пользователя как администратора и сохраняет на диск."""
        self._bound.add(user_id)
        os.makedirs(os.path.dirname(self.storage_file) or ".", exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(sorted(self._bound), f)
        logger.success("Telegram-пользователь {} привязан как администратор", user_id)


class AuthMiddleware(BaseMiddleware):
    """
    Пропускает к хендлерам только администраторов.

    Неавторизованному пользователю: сообщение с верным секретным кодом привязывает его как
    админа, любое другое сообщение получает подсказку, callback — alert.
    """

    def __init__(self, cardinal, admins: TgAdmins):
        self.cardinal = cardinal
        self.admins = admins

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is not None and self.admins.is_admin(user.id):
            return await handler(event, data)

        l10n = self.cardinal.l10n
        if isinstance(event, Message):
            text = (event.text or "").strip()
            if user is not None and text and secrets.compare_digest(text, self.admins.secret_code):
                self.admins.bind(user.id)
                await event.answer(l10n("auth_success"))
            else:
                logger.warning("Неавторизованное обращение к TG-боту от {} ({})",
                               user.id if user else "?", user.username if user else "?")
                await event.answer(l10n("unauthorized"))
        elif isinstance(event, CallbackQuery):
            await event.answer(l10n("unauthorized"), show_alert=True)
        return None
