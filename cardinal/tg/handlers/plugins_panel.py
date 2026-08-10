"""
Раздел «Плагины»: список загруженных плагинов `PluginManager`, включение/выключение,
установка нового плагина `.py`-файлом из Telegram (с предупреждением безопасности),
удаление с подтверждением (выгрузка хендлеров + удаление файла).
"""
from __future__ import annotations

import contextlib
import html
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from .common import PAGE_SIZE, cancel_markup, nav_row, on_off, pager_row, paginate, safe_edit

router = Router(name="plugins")


class InstallPlugin(StatesGroup):
    file = State()


def _plugin_uuids(cardinal) -> list[str]:
    return sorted(cardinal.plugin_manager.plugins)


def build_plugins_menu(cardinal, page: int = 0) -> tuple[str, object]:
    l10n = cardinal.l10n
    manager = cardinal.plugin_manager
    uuids = _plugin_uuids(cardinal)
    page_uuids, page, total_pages, start = paginate(uuids, page)

    if page_uuids:
        lines = [
            l10n("pl_line", state=on_off(l10n, manager.plugins[uid].enabled),
                 name=html.escape(manager.plugins[uid].name),
                 version=html.escape(manager.plugins[uid].version or ""))
            for uid in page_uuids
        ]
        text = l10n("pl_title") + "\n" + "\n".join(lines)
    else:
        text = l10n("pl_title") + "\n" + l10n("pl_no_plugins")

    builder = InlineKeyboardBuilder()
    for offset, uid in enumerate(page_uuids):
        plugin = manager.plugins[uid]
        builder.row(
            InlineKeyboardButton(text=f"{on_off(l10n, plugin.enabled)} {plugin.name[:32]}",
                                 callback_data=f"pl:t:{start + offset}"),
            InlineKeyboardButton(text="🗑", callback_data=f"pl:d:{start + offset}"),
        )
    if pager := pager_row("pl:p", page, total_pages):
        builder.row(*pager)
    builder.row(InlineKeyboardButton(text=l10n("pl_btn_install"), callback_data="pl:install"))
    builder.row(*nav_row(l10n))
    return text, builder.as_markup()


@router.callback_query(F.data == "pl")
async def cb_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_plugins_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("pl:p:"))
async def cb_menu_page(query: CallbackQuery, cardinal) -> None:
    text, markup = build_plugins_menu(cardinal, page=int(query.data.rsplit(":", 1)[1]))
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data.startswith("pl:t:"))
async def cb_toggle(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    manager = cardinal.plugin_manager
    index = int(query.data.rsplit(":", 1)[1])
    uuids = _plugin_uuids(cardinal)
    if not (0 <= index < len(uuids)):
        await query.answer()
        return
    plugin = manager.plugins[uuids[index]]
    if plugin.enabled:
        manager.disable_plugin(plugin.uuid)
        await query.answer(l10n("pl_toggled_off", name=plugin.name))
    else:
        manager.enable_plugin(plugin.uuid)
        await query.answer(l10n("pl_toggled_on", name=plugin.name))
    text, markup = build_plugins_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data.startswith("pl:d:"))
async def cb_delete(query: CallbackQuery, cardinal) -> None:
    """Удаление плагина: первый тап — подтверждение, `...:yes` — выгрузка и удаление файла."""
    l10n = cardinal.l10n
    manager = cardinal.plugin_manager
    parts = query.data.split(":")  # pl:d:<index> или pl:d:<index>:yes
    index, confirmed = int(parts[2]), len(parts) == 4
    uuids = _plugin_uuids(cardinal)
    if not (0 <= index < len(uuids)):
        await query.answer()
        return
    plugin = manager.plugins[uuids[index]]

    if not confirmed:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=l10n("pl_btn_delete_yes"), callback_data=f"pl:d:{index}:yes"))
        builder.row(*nav_row(l10n, "pl"))
        await safe_edit(query.message, l10n("pl_delete_confirm", name=html.escape(plugin.name)),
                        builder.as_markup())
        await query.answer()
        return

    manager.unload_plugin(plugin.uuid)
    with contextlib.suppress(OSError):
        os.remove(plugin.path)
    logger.info("Плагин {} удалён из TG-панели (файл: {})", plugin.name, plugin.path)
    await query.answer(l10n("pl_deleted", name=plugin.name))
    text, markup = build_plugins_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "pl:install")
async def cb_install(query: CallbackQuery, state: FSMContext, cardinal) -> None:
    await state.set_state(InstallPlugin.file)
    await safe_edit(query.message, cardinal.l10n("pl_install_warning"), cancel_markup(cardinal.l10n))
    await query.answer()


@router.message(InstallPlugin.file, F.document)
async def msg_plugin_file(message: Message, state: FSMContext, cardinal) -> None:
    l10n = cardinal.l10n
    document = message.document
    filename = document.file_name or "plugin.py"
    if not filename.endswith(".py"):
        await message.answer(l10n("pl_install_failed", error="ожидается файл .py"))
        return
    await state.clear()

    manager = cardinal.plugin_manager
    os.makedirs(manager.plugins_dir, exist_ok=True)
    path = os.path.join(manager.plugins_dir, os.path.basename(filename))
    file = await message.bot.download(document)
    with open(path, "wb") as f:
        f.write(file.read())

    try:
        plugin_info = manager._load_plugin_file(path)  # noqa: SLF001 — наш собственный менеджер
    except Exception as exc:
        logger.exception("Не удалось загрузить установленный из TG плагин {}", path)
        await message.answer(l10n("pl_install_failed", error=html.escape(str(exc))))
        return
    if plugin_info is None:
        await message.answer(l10n("pl_install_failed", error="файл не похож на плагин"))
        return

    await message.answer(l10n("pl_installed", name=html.escape(plugin_info.name)))
    text, markup = build_plugins_menu(cardinal)
    await message.answer(text, reply_markup=markup)
