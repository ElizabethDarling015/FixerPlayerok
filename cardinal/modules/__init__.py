"""Модули Cardinal: автоответчик, приветствие, автовосстановление, вечный онлайн, сводка."""
from __future__ import annotations

from .autoresponse import AutoResponseModule
from .autorestore import AutoRestoreModule
from .base import BaseModule
from .digest import DigestModule
from .greeting import GreetingModule
from .online import OnlineModule

__all__ = ["BaseModule", "AutoResponseModule", "AutoRestoreModule", "DigestModule", "GreetingModule",
           "OnlineModule", "build_modules"]


def build_modules(cardinal) -> list[BaseModule]:
    """Собирает все модули Cardinal (переключатели включения — в `settings.modules`)."""
    return [
        AutoResponseModule(cardinal),
        GreetingModule(cardinal),
        AutoRestoreModule(cardinal),
        OnlineModule(cardinal),
        DigestModule(cardinal),
    ]
