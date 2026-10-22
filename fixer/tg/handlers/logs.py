"""Настройки → «📄 Логи»: лог бота прямо в сообщении, с фильтрами, листанием и скачиванием.

Фильтр — уровень (все / инфо+ / предупреждения+ / ошибки, выбранный отмечен «•»), за всё
время, что есть в файле. На экран — столько последних записей, сколько влезает в сообщение;
«◀️ Старее» / «Новее ▶️» листают. «📥 Отфильтрованное» присылает файлом всё, что подходит
под фильтры (без обрезки), «📥 Весь файл» — текущий файл лога.
Всё состояние — в callback-данных кнопок (``lg:<уровень>:<период>:<раздел>:<страница>``; период
и раздел кнопками больше не меняются — в данных остались для совместимости, всегда «0» и «all»).
"""
from __future__ import annotations

import asyncio
import datetime
import html
import os
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from ... import log_reader as lr
from ...logging_setup import LOG_FILE
from .common import nav_row, safe_edit

router = Router(name="logs")

SEPARATOR = "━━━━━━━━━━━━━━━━━━━"
#: Сколько символов записей помещаем в сообщение (лимит Telegram 4096, с запасом на шапку и HTML).
BODY_LIMIT = 3300
MESSAGE_LIMIT = 300
DEFAULT = ("w", "0", "all", 0)

_LEVEL_KEYS = {"a": "lg_lvl_all", "i": "lg_lvl_info", "w": "lg_lvl_warn", "e": "lg_lvl_err"}


def parse_callback(data: str) -> tuple[str, str, str, int]:
    parts = (data or "").split(":")
    if len(parts) != 5:
        return DEFAULT
    _, level, period, section, page = parts
    if level not in lr.LEVELS or period not in lr.PERIODS or (section != "all" and section not in lr.SECTIONS):
        return DEFAULT
    try:
        return level, period, section, max(0, int(page))
    except ValueError:
        return DEFAULT


def _cb(level, period, section, page=0, action="lg") -> str:
    return f"{action}:{level}:{period}:{section}:{page}"


def render_entry(e: lr.Entry, with_date: bool) -> str:
    """`with_date` — показывать дату (для записей не за сегодня)."""
    when = e.time.strftime("%d.%m %H:%M:%S" if with_date else "%H:%M:%S")
    short = e.name.rsplit(".", 1)[-1]
    msg = e.message if len(e.message) <= MESSAGE_LIMIT else e.message[:MESSAGE_LIMIT - 1] + "…"
    text = f"<code>{when}</code> {lr.LEVEL_ICON.get(e.level, '•')} <b>{html.escape(short)}</b> {html.escape(msg)}"
    tail = next((line.strip() for line in reversed(e.extra) if line.strip()), None)
    if tail and tail != e.message:
        tail = tail if len(tail) <= 150 else tail[:149] + "…"
        text += f"\n   ↳ <i>{html.escape(tail)}</i>"
    return text


def paginate(rendered: list[str], budget: int = BODY_LIMIT) -> list[tuple[int, int]]:
    """Страницы с конца (страница 0 — самые свежие): список (начало, конец) по индексам."""
    pages: list[tuple[int, int]] = []
    end = len(rendered)
    while end > 0:
        size, start = 0, end
        while start > 0 and (size + len(rendered[start - 1]) + 1 <= budget or start == end):
            size += len(rendered[start - 1]) + 1
            start -= 1
        pages.append((start, end))
        end = start
    return pages or [(0, 0)]


def build_logs_screen(l10n, entries: list[lr.Entry], level: str, period: str, section: str, page: int,
                      size_bytes: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    today = datetime.date.today()
    rendered = [render_entry(e, e.time.date() != today) for e in entries]
    pages = paginate(rendered)
    page = min(page, len(pages) - 1)
    start, end = pages[page]

    head = l10n("lg_title", level=l10n(_LEVEL_KEYS[level]))
    body = "\n".join(rendered[start:end]) if rendered else l10n("lg_empty")
    footer = l10n("lg_footer", shown=end - start, total=len(entries), page=page + 1, pages=len(pages),
                  size=f"{size_bytes / 1024 / 1024:.1f}")
    text = "\n".join([head, SEPARATOR, body, SEPARATOR, footer])

    def mark(on: bool, label: str) -> str:
        return f"• {label}" if on else label

    rows = [
        [InlineKeyboardButton(text=mark(code == level, l10n(key)), callback_data=_cb(code, "0", "all"))
         for code, key in _LEVEL_KEYS.items()],
    ]
    nav = []
    if page < len(pages) - 1:
        nav.append(InlineKeyboardButton(text=l10n("lg_older"), callback_data=_cb(level, period, section, page + 1)))
    if page > 0:
        nav.append(InlineKeyboardButton(text=l10n("lg_newer"), callback_data=_cb(level, period, section, page - 1)))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(text=l10n("lg_dl_filtered"), callback_data=_cb(level, period, section, 0, "lgf")),
        InlineKeyboardButton(text=l10n("lg_dl_all"), callback_data="lgall"),
    ])
    rows.append([InlineKeyboardButton(text=l10n("ld_btn_refresh"), callback_data=_cb(level, period, section, page))])
    rows.append(nav_row(l10n, "sys"))
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def build_default_screen(fixer) -> tuple[str, InlineKeyboardMarkup]:
    """Экран с фильтрами по умолчанию — синхронно (для открытия новым сообщением)."""
    level, period, section, page = DEFAULT
    files = lr.log_files()
    filtered = lr.apply_filters(lr.read_entries(files), level, period, section)
    return build_logs_screen(fixer.l10n, filtered, level, period, section, page, lr.total_size(files))


async def _load(level, period, section):
    files = lr.log_files()
    entries = await asyncio.to_thread(lr.read_entries, files)
    filtered = lr.apply_filters(entries, level, period, section)
    return filtered, lr.total_size(files)


async def _answer(query: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(Exception):
        await query.answer(text, show_alert=alert)


def _close_kb(l10n) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=l10n("btn_close"), callback_data="close")]])


@router.callback_query(F.data == "sys:logs")
@router.callback_query(F.data.startswith("lg:"))
async def cb_logs(query: CallbackQuery, fixer) -> None:
    level, period, section, page = parse_callback(query.data) if query.data.startswith("lg:") else DEFAULT
    await _answer(query)
    filtered, size = await _load(level, period, section)
    text, markup = build_logs_screen(fixer.l10n, filtered, level, period, section, page, size)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data.startswith("lgf:"))
async def cb_download_filtered(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    level, period, section, _ = parse_callback("lg:" + query.data.split(":", 1)[1])
    filtered, _ = await _load(level, period, section)
    if not filtered:
        await _answer(query, l10n("lg_empty"), alert=True)
        return
    content = "\n".join(e.full_text() for e in filtered).encode("utf-8")
    name = f"fixer-log_{level}_{period}_{section}_{datetime.datetime.now():%Y-%m-%d_%H-%M}.txt"
    await query.message.answer_document(BufferedInputFile(content, filename=name), reply_markup=_close_kb(l10n))
    await _answer(query)


@router.callback_query(F.data == "lgall")
async def cb_download_all(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    if not os.path.isfile(LOG_FILE):
        await _answer(query, l10n("lg_empty"), alert=True)
        return
    try:
        await query.message.answer_document(
            FSInputFile(LOG_FILE, filename=f"fixer_{datetime.datetime.now():%Y-%m-%d_%H-%M}.log"),
            reply_markup=_close_kb(l10n))
    except Exception as exc:
        logger.warning("[logs] Файл лога не отправлен: {}", exc)
        await _answer(query, l10n("lg_dl_failed", error=str(exc)[:150]), alert=True)
        return
    await _answer(query)
