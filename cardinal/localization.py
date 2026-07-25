"""Локализация Cardinal: строка по ключу с подстановкой параметров через `str.format`."""
from __future__ import annotations

from .locales import en, ru

_LOCALES = {"ru": ru.STRINGS, "en": en.STRINGS}


class L10n:
    """
    Переводчик строк интерфейса.

    Использование: `l10n = L10n("ru"); l10n("menu_title", username="...", ...)`.
    Отсутствующий в выбранном языке ключ берётся из русской локали (она эталонная),
    отсутствующий вовсе — возвращается как есть (чтобы интерфейс не падал).
    """

    def __init__(self, language: str = "ru"):
        self.language = language if language in _LOCALES else "ru"
        self._strings = _LOCALES[self.language]

    def __call__(self, key: str, **kwargs) -> str:
        template = self._strings.get(key) or _LOCALES["ru"].get(key) or key
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
