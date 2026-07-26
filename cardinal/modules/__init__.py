"""Модули Cardinal: автоответчик, приветствие, послепродажка, автовосстановление, вечный онлайн, сводка, обновления."""
from __future__ import annotations

from .autoresponse import AutoResponseModule
from .autorestore import AutoRestoreModule
from .autoupdate import AutoUpdateModule
from .base import BaseModule
from .digest import DigestModule
from .greeting import GreetingModule
from .online import OnlineModule
from .postsale import PostsaleModule

__all__ = ["BaseModule", "AutoResponseModule", "AutoRestoreModule", "AutoUpdateModule",
           "DigestModule", "GreetingModule", "OnlineModule", "PostsaleModule", "build_modules"]


def build_modules(cardinal) -> list[BaseModule]:
    """Собирает все модули Cardinal (переключатели включения — в `settings.modules`)."""
    return [
        AutoResponseModule(cardinal),
        GreetingModule(cardinal),
        PostsaleModule(cardinal),
        AutoRestoreModule(cardinal),
        OnlineModule(cardinal),
        DigestModule(cardinal),
        AutoUpdateModule(cardinal),
    ]
