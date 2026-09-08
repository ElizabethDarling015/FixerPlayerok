"""
Сессия aiogram с возможностью менять прокси на лету (перенесено из Shinoa).

aiogram 3.x умеет устанавливать прокси через `bot.session.proxy = url`
(старое соединение закрывается, следующее создаётся уже через прокси),
но не умеет сбрасывать прокси обратно в `None` — для возврата к прямому
подключению добавлен `clear_proxy()`.

Используется, чтобы Telegram-сессия бота могла ходить через тот же прокси,
что и `Account`/`Runner` (Playerok) — актуально, когда единственный путь
наружу вообще (например, VPN/sing-box) временно отключён и нужно поднять
и Telegram, и Playerok через один и тот же внешний прокси.
"""
from __future__ import annotations

import ssl

import certifi
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import TCPConnector


class ProxySwitchableSession(AiohttpSession):
    def clear_proxy(self) -> None:
        """Возврат к прямому подключению без прокси."""
        self._connector_type = TCPConnector
        self._connector_init = {
            "ssl": ssl.create_default_context(cafile=certifi.where()),
            "limit": 100,
            "ttl_dns_cache": 3600,
        }
        self._proxy = None
        self._should_reset_connector = True
