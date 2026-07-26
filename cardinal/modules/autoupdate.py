"""
Автопроверка обновлений PlayerokCardinal на GitHub.

Раз в `[updates] check_interval` секунд сверяет установленную версию с веткой на GitHub
(`self_update.check_for_update`). При найденном обновлении либо уведомляет админов в Telegram
(один раз на версию), либо — если включён `[updates] auto_install` — сразу устанавливает его
и перезапускает Cardinal.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from ..self_update import check_for_update, update_from_github
from .base import BaseModule

#: Пауза после старта до первой проверки (даём боту спокойно подняться).
STARTUP_DELAY = 60.0


class AutoUpdateModule(BaseModule):
    name = "autoupdate"

    def __init__(self, cardinal):
        super().__init__(cardinal)
        #: SHA версии, о которой уже уведомляли (чтобы не спамить каждую проверку).
        self._notified_sha = ""
        # Точки подмены для тестов.
        self._check = check_for_update
        self._update = update_from_github

    async def on_start(self) -> None:
        self.cardinal.spawn(self._loop())

    async def _loop(self) -> None:
        await asyncio.sleep(STARTUP_DELAY)
        while True:
            if self.enabled:
                try:
                    await self.check_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Автопроверка обновлений упала")
            await asyncio.sleep(max(60.0, self.cardinal.settings.updates.check_interval))

    async def check_once(self) -> None:
        """Одна проверка: уведомить о новой версии или установить её (auto_install)."""
        check = await asyncio.to_thread(self._check)
        if not check.ok:
            logger.warning("Проверка обновлений не удалась: {}", check.error)
            return
        if not check.available:
            logger.debug("Обновлений нет (версия {})", check.current or "?")
            return

        notifier = self.cardinal.notifier
        if self.cardinal.settings.updates.auto_install:
            logger.info("Найдено обновление {} → {} — устанавливаю (auto_install)",
                        check.current, check.latest)
            result = await asyncio.to_thread(self._update)
            if result.ok and result.changed:
                if notifier is not None:
                    await notifier.notify_update_installed(result.message)
                self.cardinal.request_restart()
            elif not result.ok:
                logger.warning("Автообновление не удалось: {}", result.message)
                if notifier is not None:
                    await notifier.notify_error(f"Автообновление не удалось: {result.message}")
            return

        if check.latest and check.latest == self._notified_sha:
            return  # об этой версии уже сообщали
        self._notified_sha = check.latest
        logger.info("Доступно обновление: {} → {}", check.current, check.latest)
        if notifier is not None:
            await notifier.notify_update_available(check.current, check.latest)
