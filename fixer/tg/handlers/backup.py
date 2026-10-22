"""Настройки → «💾 Бэкап конфигов»: экспорт и импорт одним архивом, всё в одном сообщении.

* «📤 Экспорт» — бот присылает архив отдельным сообщением (с «❌ Закрыть»), экран остаётся.
* «📥 Импорт» — бот ждёт архив; ваше сообщение с файлом (и любое другое) удаляется, итог
  проверки показывается в этом же сообщении. Если архив подходит — текущие настройки
  сохраняются в storage/backups/, архив применяется и бот перезапускается. После
  перезапуска в «FixerPlayerok запущен» первой строкой — «✅ Бэкап … применён».
Состав архива — см. `fixer/backup.py`.
"""
from __future__ import annotations

import asyncio
import html
import io
from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from ... import backup
from .common import nav_row, remember_panel, safe_edit, show_in_panel, with_error

router = Router(name="backup")

SEPARATOR = "━━━━━━━━━━━━━━━━━━━"


class BackupStates(StatesGroup):
    waiting_file = State()


def _kb(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_backup_menu(l10n) -> tuple[str, InlineKeyboardMarkup]:
    text = l10n("bk_title") + "\n" + SEPARATOR + "\n" + l10n("bk_contents") + "\n" + SEPARATOR + "\n" + l10n("bk_warning")
    return text, _kb([
        [InlineKeyboardButton(text=l10n("bk_btn_import"), callback_data="bk:import"),
         InlineKeyboardButton(text=l10n("bk_btn_export"), callback_data="bk:export")],
        nav_row(l10n, "sys"),
    ])


def _waiting_screen(l10n) -> tuple[str, InlineKeyboardMarkup]:
    text = l10n("bk_title") + "\n" + SEPARATOR + "\n" + l10n("bk_send_file")
    return text, _kb([[InlineKeyboardButton(text=l10n("wd_btn_cancel"), callback_data="bk")]])


def _username(fixer) -> str | None:
    account = getattr(fixer, "account", None)
    return getattr(account, "username", None)


@router.callback_query(F.data == "bk")
async def cb_menu(query: CallbackQuery, fixer, state: FSMContext) -> None:
    await state.clear()
    text, markup = build_backup_menu(fixer.l10n)
    await safe_edit(query.message, text, markup)
    with suppress(Exception):
        await query.answer()


@router.callback_query(F.data == "bk:export")
async def cb_export(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    try:
        data = await asyncio.to_thread(backup.build_backup, username=_username(fixer))
    except Exception as exc:
        logger.exception("[backup] Не удалось собрать архив")
        with suppress(Exception):
            await query.answer(l10n("bk_export_failed", error=str(exc)[:150]), show_alert=True)
        return
    await query.message.answer_document(
        BufferedInputFile(data, filename=backup.export_filename(_username(fixer))),
        caption=l10n("bk_export_caption"),
        reply_markup=_kb([[InlineKeyboardButton(text=l10n("btn_close"), callback_data="close")]]),
    )
    logger.info("[backup] Экспорт: архив {} КБ отправлен", len(data) // 1024)
    with suppress(Exception):
        await query.answer()


@router.callback_query(F.data == "bk:import")
async def cb_import(query: CallbackQuery, fixer, state: FSMContext) -> None:
    await state.set_state(BackupStates.waiting_file)
    await remember_panel(state, query.message)
    text, markup = _waiting_screen(fixer.l10n)
    await safe_edit(query.message, text, markup)
    with suppress(Exception):
        await query.answer()


@router.message(BackupStates.waiting_file, F.document)
async def msg_backup_file(message: Message, state: FSMContext, fixer) -> None:
    l10n = fixer.l10n
    text, markup = _waiting_screen(l10n)
    document = message.document
    if (document.file_size or 0) > backup.MAX_ARCHIVE_SIZE:
        await show_in_panel(message, state, with_error(l10n("bk_err", error="архив больше 20 МБ"), text), markup)
        return
    try:
        buffer = io.BytesIO()
        await message.bot.download(document, destination=buffer)
        data = buffer.getvalue()
        plan = backup.read_backup(data)
    except backup.BackupError as exc:
        await show_in_panel(message, state, with_error(l10n("bk_err", error=html.escape(str(exc))), text), markup)
        return
    except Exception as exc:
        logger.exception("[backup] Не удалось принять архив")
        await show_in_panel(message, state, with_error(l10n("bk_err", error=html.escape(str(exc)[:150])), text), markup)
        return

    try:
        safety = await asyncio.to_thread(backup.safety_copy, _username(fixer))
        result = await asyncio.to_thread(backup.apply_backup, plan, fixer.settings)
        backup.write_applied_mark(result)
    except Exception as exc:
        logger.exception("[backup] Не удалось применить архив")
        await show_in_panel(message, state, with_error(l10n("bk_err_apply", error=html.escape(str(exc)[:150])), text),
                            markup)
        return
    logger.success("[backup] Бэкап от {} применён (страховочная копия: {}) — перезапуск",
                   result.get("created_at"), safety)
    await show_in_panel(message, state, l10n("bk_title") + "\n" + SEPARATOR + "\n" + build_report(l10n, result), None)
    await state.clear()
    fixer.request_restart()


@router.message(BackupStates.waiting_file)
async def msg_not_a_file(message: Message, state: FSMContext, fixer) -> None:
    text, markup = _waiting_screen(fixer.l10n)
    await show_in_panel(message, state, with_error(fixer.l10n("bk_err_not_file"), text), markup)


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "?"
    with suppress(Exception):
        import datetime
        return datetime.datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    return iso


def build_report(l10n, result: dict) -> str:
    """Итог импорта (в сообщении перед перезапуском)."""
    lines = [l10n("bk_applied", date=_fmt_date(result.get("created_at")),
                  account=html.escape(result.get("account") or "?"))]
    lines.append(l10n("bk_stocks", count=result.get("stocks", 0)))
    lines.append(l10n("bk_tg_same" if result.get("telegram") == "same" else "bk_tg_changed"))
    lines.append(l10n("bk_restarting"))
    return "\n".join(lines)


def applied_line(l10n, mark: dict) -> str:
    """Первая строка стартового уведомления после импорта."""
    return l10n("bk_started_line", date=_fmt_date(mark.get("created_at")))
