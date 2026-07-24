"""
Мини-сериализатор TOML (stdlib читает TOML через `tomllib`, но писать не умеет).

Поддерживает ровно те структуры, которые используют конфиги Cardinal: строки, числа,
булевы значения, списки скаляров, вложенные таблицы (`[section]`, `[section."ключ с пробелами"]`).
Ключи с не-ASCII символами и пробелами корректно экранируются.
"""
from __future__ import annotations

import json


def _format_key(key: str) -> str:
    """Возвращает ключ в TOML-виде: голый, если можно, иначе — в кавычках."""
    if key and all(c.isascii() and (c.isalnum() or c in "-_") for c in key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _format_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        # JSON-строка — валидная TOML basic string (экранирование совпадает).
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    raise TypeError(f"Тип {type(value).__name__} не поддерживается TOML-сериализатором Cardinal")


def dumps_toml(data: dict, _prefix: str = "") -> str:
    """
    Сериализует словарь в TOML-текст.

    Скалярные значения и списки пишутся как `key = value`, вложенные словари — как таблицы
    `[prefix.key]` (рекурсивно). Порядок ключей сохраняется.
    """
    lines: list[str] = []
    tables: list[tuple[str, dict]] = []

    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        elif value is None:
            continue  # None — «не задано», в TOML такого значения нет
        else:
            lines.append(f"{_format_key(key)} = {_format_value(value)}")

    chunks: list[str] = []
    if lines:
        chunks.append("\n".join(lines))

    for key, table in tables:
        path = f"{_prefix}.{_format_key(key)}" if _prefix else _format_key(key)
        body = dumps_toml(table, _prefix=path)
        chunks.append(f"[{path}]" + (f"\n{body}" if body else ""))

    return "\n\n".join(chunks)


def write_toml(path: str, data: dict) -> None:
    """Пишет словарь в TOML-файл (с завершающим переводом строки)."""
    content = dumps_toml(data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content + ("\n" if content else ""))
