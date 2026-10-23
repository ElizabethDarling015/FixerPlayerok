"""Чтение файла лога Fixer для раздела «📄 Логи»: разбор записей и фильтры.

Формат строки (см. `logging_setup.py`):
``2026-10-22 14:02:11.123 WARNING  fixer.tg.handlers.chats:512 — текст``.
Строки без такого начала (traceback и многострочные сообщения) относятся к предыдущей записи.
"""
from __future__ import annotations

import datetime
import glob
import os
import re
from dataclasses import dataclass, field

from .logging_setup import LOG_FILE

_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)? +([A-Z]+) +([\w.<>-]+):(\d+) — ?(.*)$"
)

#: Уровни фильтра: код → диапазон уровней [от, до). Каждый уровень — только свои записи
#: («Инфо» — без предупреждений и ошибок), «Все» — всё, включая отладочные (DEBUG).
LEVELS = {"a": (0, 100), "i": (20, 30), "w": (30, 40), "e": (40, 100)}
LEVEL_NO = {"TRACE": 5, "DEBUG": 10, "INFO": 20, "SUCCESS": 25, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
LEVEL_ICON = {"TRACE": "🐞", "DEBUG": "🐞", "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌",
              "CRITICAL": "🔥"}
#: Периоды фильтра: код → минут (0 — всё).
PERIODS = {"15": 15, "60": 60, "1440": 1440, "0": 0}

#: Разделы: код → префиксы имени модуля (первое совпадение по порядку `SECTION_ORDER`).
SECTIONS = {
    "deal": ("fixer.deals_in_work", "fixer.tg.handlers.deal_actions", "fixer.tg.handlers.deals_in_work",
             "fixer.tg.handlers.last_deals"),
    "chat": ("fixer.tg.handlers.chats", "fixer.tg.handlers.replies", "fixer.tg.reactions",
             "fixer.modules.autoresponse", "fixer.modules.night"),
    "ad": ("playerokapi.autodelivery", "playerokapi.delivery_ledger", "fixer.tg.handlers.autodelivery"),
    "raise": ("playerokapi.autoraise", "fixer.autoraise", "fixer.tg.handlers.autoraise"),
    "tg": ("fixer.tg", "aiogram"),
    "api": ("playerokapi",),
}
SECTION_ORDER = ("deal", "chat", "ad", "raise", "tg", "api")


@dataclass
class Entry:
    time: datetime.datetime
    level: str
    name: str
    line: int
    message: str
    extra: list[str] = field(default_factory=list)

    @property
    def level_no(self) -> int:
        return LEVEL_NO.get(self.level, 20)

    @property
    def section(self) -> str | None:
        for code in SECTION_ORDER:
            if self.name.startswith(SECTIONS[code]):
                return code
        return None

    def full_text(self) -> str:
        head = f"{self.time:%Y-%m-%d %H:%M:%S} {self.level:<8} {self.name}:{self.line} — {self.message}"
        return "\n".join([head, *self.extra])


def log_files(log_file: str = LOG_FILE, keep: int = 2) -> list[str]:
    """Текущий файл и предыдущий после ротации (loguru переименовывает старый в fixer.<дата>.log)."""
    base, ext = os.path.splitext(log_file)
    rotated = sorted(glob.glob(f"{base}.*{ext}"), key=os.path.getmtime)
    files = rotated[-(keep - 1):] if keep > 1 else []
    if os.path.isfile(log_file):
        files.append(log_file)
    return files


def parse(text: str) -> list[Entry]:
    entries: list[Entry] = []
    for raw in text.splitlines():
        m = _LINE_RE.match(raw)
        if m:
            try:
                when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                when = None
            if when is not None:
                entries.append(Entry(when, m.group(2), m.group(3), int(m.group(4)), m.group(5)))
                continue
        if entries and raw.strip():
            entries[-1].extra.append(raw)
    return entries


def read_entries(files: list[str] | None = None) -> list[Entry]:
    entries: list[Entry] = []
    for path in files if files is not None else log_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                entries.extend(parse(f.read()))
        except OSError:
            continue
    return entries


def apply_filters(entries: list[Entry], level: str, period: str, section: str,
                  now: datetime.datetime | None = None) -> list[Entry]:
    low, high = LEVELS.get(level, LEVELS["w"])
    minutes = PERIODS.get(period, 60)
    since = (now or datetime.datetime.now()) - datetime.timedelta(minutes=minutes) if minutes else None
    out = []
    for e in entries:
        if not low <= e.level_no < high:
            continue
        if since is not None and e.time < since:
            continue
        if section != "all" and e.section != section:
            continue
        out.append(e)
    return out


def total_size(files: list[str] | None = None) -> int:
    return sum(os.path.getsize(p) for p in (files if files is not None else log_files()) if os.path.isfile(p))
