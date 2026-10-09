"""Модули Fixer: автоответчик, автовосстановление, вечный онлайн, сводка."""
from __future__ import annotations

from .autoresponse import AutoResponseModule
from .autorestore import AutoRestoreModule
from .base import BaseModule
from .digest import DigestModule
from .online import OnlineModule

__all__ = ["BaseModule", "AutoResponseModule", "AutoRestoreModule", "DigestModule",
           "OnlineModule", "build_modules"]


def build_modules(fixer) -> list[BaseModule]:
    """Собирает все модули Fixer (переключатели включения — в `settings.modules`)."""
    return [
        AutoResponseModule(fixer),
        AutoRestoreModule(fixer),
        OnlineModule(fixer),
        DigestModule(fixer),
    ]
