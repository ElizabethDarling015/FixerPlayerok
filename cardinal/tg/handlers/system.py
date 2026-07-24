"""Раздел «Система»: просмотр логов, бэкап, перезагрузка конфигов, выключение Cardinal."""
from __future__ import annotations

import asyncio
import datetime
import html
import io
import os
import zipfile

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...logging_setup import LOG_FILE
from ...settings import CONFIG_DIR, STORAGE_DIR, ConfigError
from .common import nav_row, safe_edit

router = Router(name="system")

#: Сколько последних строк лога показывать и лимит длины сообщения TG.
LOG_TAIL_LINES = 30
MAX_TEXT_LENGTH = 3500

#: Подпапки storage/, не попадающие в бэкап (логи большие и не нужны для восстановления).
BACKUP_EXCLUDE_DIRS = ("logs",)


def build_system_menu(cardinal) -> tuple[str, object]:
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("sys_btn_logs"), callback_data="sys:logs")
    builder.button(text=l10n("sys_btn_backup"), callback_data="sys:backup")
    builder.button(text=l10n("sys_btn_reload"), callback_data="sys:reload")
    builder.button(text=l10n("sys_btn_restart"), callback_data="sys:restart")
    builder.button(text=l10n("sys_btn_shutdown"), callback_data="sys:off")
    builder.adjust(1)
    builder.row(*nav_row(l10n))
    return l10n("sys_title"), builder.as_markup()


def build_backup_zip(config_dir: str = CONFIG_DIR, storage_dir: str = STORAGE_DIR) -> bytes:
    """
    Собирает zip-архив с конфигами и данными (склады, журналы SQLite) для переноса/восстановления.

    Подпапки из `BACKUP_EXCLUDE_DIRS` (логи) не включаются. Возвращает содержимое архива.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for base_dir in (config_dir, storage_dir):
            if not os.path.isdir(base_dir):
                continue
            base_name = os.path.basename(os.path.normpath(base_dir))
            for root, dirs, files in os.walk(base_dir):
                if root == base_dir:
                    dirs[:] = [d for d in dirs if d not in BACKUP_EXCLUDE_DIRS]
                for filename in sorted(files):
                    full_path = os.path.join(root, filename)
                    arcname = os.path.join(base_name, os.path.relpath(full_path, base_dir))
                    archive.write(full_path, arcname)
    return buffer.getvalue()


def read_log_tail(log_file: str = LOG_FILE, lines: int = LOG_TAIL_LINES) -> str:
    """Последние строки файла лога (пустая строка, если файла нет)."""
    if not os.path.isfile(log_file):
        return ""
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        return "".join(f.readlines()[-lines:])


@router.callback_query(F.data == "sys")
async def cb_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "sys:logs")
async def cb_logs(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    tail = read_log_tail()
    if not tail.strip():
        body = l10n("sys_logs_empty")
    else:
        escaped = html.escape(tail)[-MAX_TEXT_LENGTH:]
        body = f"<pre>{escaped}</pre>"
    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(query.message, l10n("sys_logs_title") + "\n" + body, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:backup")
async def cb_backup(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    data = await asyncio.to_thread(build_backup_zip)
    filename = f"cardinal_backup_{datetime.datetime.now():%Y%m%d_%H%M}.zip"
    await query.message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=l10n("sys_backup_caption"),
    )
    await query.answer()


@router.callback_query(F.data == "sys:reload")
async def cb_reload(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    try:
        details = cardinal.reload_configs()
    except ConfigError as exc:
        await query.answer(str(exc)[:190], show_alert=True)
        return
    await query.answer(l10n("sys_reloaded", details=details), show_alert=True)


@router.callback_query(F.data == "sys:restart")
async def cb_restart_confirm(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("sys_btn_restart_yes"), callback_data="sys:restart:yes"))
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(query.message, l10n("sys_restart_confirm"), builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:restart:yes")
async def cb_restart(query: CallbackQuery, cardinal) -> None:
    await safe_edit(query.message, cardinal.l10n("sys_restart_done"))
    await query.answer()
    cardinal.request_restart()


@router.callback_query(F.data == "sys:off")
async def cb_shutdown_confirm(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("sys_btn_shutdown_yes"), callback_data="sys:off:yes"))
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(query.message, l10n("sys_shutdown_confirm"), builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:off:yes")
async def cb_shutdown(query: CallbackQuery, cardinal) -> None:
    await safe_edit(query.message, cardinal.l10n("sys_shutdown_done"))
    await query.answer()
    cardinal.request_shutdown()
