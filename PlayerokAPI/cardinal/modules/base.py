"""Базовый класс модуля Cardinal."""
from __future__ import annotations

from typing import TYPE_CHECKING

from playerokapi.updater.events import BaseEvent

if TYPE_CHECKING:
    from ..core import Cardinal


class BaseModule:
    """
    Модуль Cardinal — обработчик событий `Runner` и/или фоновая задача.

    Атрибут `name` должен совпадать с именем поля в `settings.ModulesSettings` —
    по нему определяется, включён ли модуль (переключается из TG-панели на лету).
    """

    name: str = "base"

    def __init__(self, cardinal: "Cardinal"):
        self.cardinal = cardinal

    @property
    def enabled(self) -> bool:
        """Включён ли модуль сейчас (живой переключатель из настроек)."""
        return bool(getattr(self.cardinal.settings.modules, self.name, False))

    async def on_start(self) -> None:
        """Вызывается один раз при старте Cardinal (после авторизации аккаунта)."""

    async def on_event(self, event: BaseEvent) -> None:
        """Вызывается на каждое событие `Runner` (модуль сам проверяет `self.enabled`)."""

    async def on_stop(self) -> None:
        """Вызывается при остановке Cardinal."""
