"""Модули Fixer: вечный онлайн, сводка, ночное сообщение, витрина."""
from __future__ import annotations

from .base import BaseModule
from .digest import DigestModule
from .night import NightMessageModule
from .online import OnlineModule
from .showcase import ShowcaseModule

__all__ = ["BaseModule", "DigestModule",
           "OnlineModule", "NightMessageModule", "ShowcaseModule", "build_modules"]


def build_modules(fixer) -> list[BaseModule]:
    """Собирает все модули Fixer (переключатели включения — в `settings.modules`)."""
    return [
        OnlineModule(fixer),
        DigestModule(fixer),
        NightMessageModule(fixer),
        ShowcaseModule(fixer),
    ]
