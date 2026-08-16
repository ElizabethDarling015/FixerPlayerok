"""
«Вечный онлайн»: поддерживает статус аккаунта Playerok онлайн периодическими
авторизованными запросами (`Account.get()`).

Runner и так опрашивает профиль раз в `requests_delay` секунд, но этот модуль даёт
независимую гарантию (например, при больших интервалах поллинга) и пишет в лог, если
сайт перестал считать аккаунт онлайном.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from .base import BaseModule


class OnlineModule(BaseModule):
    name = "online"

    async def on_start(self) -> None:
        self.cardinal.spawn(self._keepalive_loop())

    async def _keepalive_loop(self) -> None:
        interval = self.cardinal.settings.online.interval
        while True:
            await asyncio.sleep(interval)
            if not self.enabled:
                continue
            try:
                # Если аккаунт не подключён (offline-режим) — пропускаем итерацию
                if self.cardinal.account is None or not self.cardinal.playerok_connected:
                    await asyncio.sleep(60)
                    continue

                account = await asyncio.to_thread(self.cardinal.account.get)                
                await asyncio.to_thread(self.cardinal.account.get_balance)  # освежить разбивку баланса
                profile = getattr(account, "profile", None)
                if profile is not None and profile.is_online is False:
                    logger.warning("Вечный онлайн: сайт считает аккаунт оффлайн (is_online=False)")
                else:
                    logger.debug("Вечный онлайн: keepalive-запрос выполнен")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Вечный онлайн: keepalive-запрос не удался")
