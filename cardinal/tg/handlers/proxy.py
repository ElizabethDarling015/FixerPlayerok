"""
Прокси для подключения Cardinal к Playerok (REST + WebSocket).

Навигация: Настройки -> 🌐 Прокси.
Один экран: список сохранённых прокси со статусом + для каждого кнопки
[переключить][проверить][удалить], ниже «➕ Добавить прокси» и ряд навигации.
Активным может быть только один прокси одновременно — активация нового снимает
предыдущий. Переключение применяется «на лету», без перезапуска бота: REST сразу
начинает ходить через новый прокси (или напрямую, если прокси выключен), а
WebSocket-подключение принудительно обрывается, чтобы переподключиться уже с
новыми настройками (см. playerokapi/updater/runner.py — он читает account.proxy
заново на каждой попытке соединения).
"""
from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ... import proxy_store
from ...proxy_tools import build_proxy_url, check_proxy, flag_emoji, parse_proxy_text, type_label
from .common import nav_row

logger = logging.getLogger(__name__)
router = Router(name="proxy")


class ProxyInput(StatesGroup):
    waiting_data = State()


# ──────────────────────────────────────────────
# Вспомогательные
# ──────────────────────────────────────────────

async def _show(bot: Bot, chat_id: int, message_id: int, text: str, kb) -> None:
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                     text=text, parse_mode="HTML", reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        logger.warning("Не удалось отредактировать меню прокси: %s", e)
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)


def _geo_str(p: dict) -> str:
    return ", ".join(x for x in (p.get("country_name"), p.get("city")) if x) or "гео не определено"


def _input_formats() -> str:
    return (
        "<code>host:port</code>\n"
        "<code>host:port:user:pass</code>\n"
        "<code>socks5://user:pass@host:port</code>\n"
        "<code>http://host:port</code>"
    )


def _input_text(ptype: str) -> str:
    return (
        f"🌐 <b>Введите данные прокси</b> ({type_label(ptype)})\n\n"
        f"Поддерживаемые форматы:\n{_input_formats()}\n\n"
        f"<i>Сообщение с данными будет удалено.</i>"
    )


def _input_error_text(ptype: str) -> str:
    return (
        "❌ <b>Неверные данные прокси.</b> Проверьте формат и отправьте ещё раз:\n\n"
        f"{_input_formats()}"
    )


def _input_kb() -> object:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="px:menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu"),
    )
    return builder.as_markup()


def _apply_proxy_to_running_account(cardinal, proxy_url: str | None) -> None:
    """
    Применяет прокси к уже работающему аккаунту «на лету»:
    REST подхватывает изменение сразу (Account.request читает self.proxy при каждом
    запросе), WebSocket — после принудительного обрыва текущего соединения (раннер сам
    переподключится по своей обычной retry-логике, уже с новым прокси).
    """
    if cardinal.account is not None:
        cardinal.account.proxy = proxy_url
    runner = getattr(cardinal, "runner", None)
    ws = getattr(runner, "_ws", None) if runner is not None else None
    if ws is not None:
        try:
            ws.close()
        except Exception as e:
            logger.warning("Не удалось закрыть WS для переключения прокси: %s", e)


async def _render_menu(bot: Bot, cardinal, chat_id: int, message_id: int,
                        checking_id: int | None = None) -> None:
    """Единственный экран «Меню прокси»."""
    proxies = await asyncio.to_thread(proxy_store.list_proxies)

    lines = ["🌐 <b>Меню прокси</b>", "",
             "Прокси применяется и к REST, и к WebSocket-подключению к Playerok.", ""]
    if proxies:
        for p in proxies:
            if checking_id == p["id"]:
                status = "⏳ проверка..."
            elif p["is_active"]:
                status = "✅ активен — Cardinal ходит на Playerok через прокси"
            elif p.get("last_ok") == 0:
                status = "❌ не работает"
            elif p.get("last_ok") == 1:
                status = f"📶 работает ({p.get('last_ms')} мс), не активен"
            else:
                status = "⚪ не активен"
            lines.append(
                f"• #{p['id']} {flag_emoji(p.get('country_code'))} {type_label(p['proxy_type'])} "
                f"<code>{html.escape(p['host'])}:{p['port']}</code> — {_geo_str(p)}, {status}"
            )
            if checking_id != p["id"] and p.get("last_ok") == 0 and p.get("last_error"):
                lines.append(f"   ⚠️ <i>{html.escape(str(p['last_error'])[:150])}</i>")
    else:
        lines.append("Список пуст. Добавь первый прокси кнопкой ниже.")

    lines.append("")
    lines.append(
        "<i>Можно запустить бота сразу на конкретном сохранённом прокси флагом "
        "--proxy1 / --proxy2 / ... (номер = порядок добавления в этом списке, "
        "сверху вниз) — без активации через это меню, разово на один запуск.</i>"
    )

    builder = InlineKeyboardBuilder()
    for p in proxies:
        label = (
            f"{flag_emoji(p.get('country_code'))} {type_label(p['proxy_type'])} • "
            f"{p['host']}:{p['port']}" + (" ✅" if p["is_active"] else "")
        )
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"px:toggle:{p['id']}"),
            InlineKeyboardButton(text="🔍", callback_data=f"px:check:{p['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"px:remove:{p['id']}"),
        )
    builder.row(InlineKeyboardButton(text="➕ Добавить прокси", callback_data="px:add"))
    builder.row(*nav_row(cardinal.l10n, "sys"))

    await _show(bot, chat_id, message_id, "\n".join(lines), builder.as_markup())


# ──────────────────────────────────────────────
# Экраны
# ──────────────────────────────────────────────

@router.callback_query(F.data == "px:menu")
async def cb_proxy_menu(call: CallbackQuery, state: FSMContext, cardinal, bot: Bot) -> None:
    await state.clear()
    await call.answer()
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data == "px:add")
async def cb_proxy_add(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await call.answer()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 SOCKS5", callback_data="px:type:socks5"),
        InlineKeyboardButton(text="🔗 HTTP/HTTPS", callback_data="px:type:http"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="px:menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu"),
    )
    await _show(bot, call.message.chat.id, call.message.message_id,
                "🌐 <b>Выберите тип прокси</b>", builder.as_markup())


@router.callback_query(F.data.in_({"px:type:socks5", "px:type:http"}))
async def cb_proxy_type(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    ptype = call.data.split(":")[2]
    await state.set_state(ProxyInput.waiting_data)
    await state.update_data(ptype=ptype, bot_msg_id=call.message.message_id)
    await call.answer()
    await _show(bot, call.message.chat.id, call.message.message_id, _input_text(ptype), _input_kb())


@router.message(ProxyInput.waiting_data)
async def step_proxy_data(message: Message, state: FSMContext, cardinal, bot: Bot) -> None:
    data = await state.get_data()
    bot_msg_id = data.get("bot_msg_id")
    ptype = data.get("ptype", "http")

    # Не захламляем чат — удаляем сообщение с данными прокси.
    try:
        await message.delete()
    except Exception as e:
        logger.warning("Не удалось удалить сообщение с данными прокси: %s", e)

    parsed = parse_proxy_text(message.text, ptype)
    if not parsed:
        await _show(bot, message.chat.id, bot_msg_id, _input_error_text(ptype), _input_kb())
        return

    proxy = await asyncio.to_thread(
        proxy_store.add_or_update_proxy,
        parsed["type"], parsed["host"], parsed["port"], parsed["username"], parsed["password"],
    )
    await state.clear()

    # Возвращаемся в то же меню, прокси сразу проверяется.
    await _render_menu(bot, cardinal, message.chat.id, bot_msg_id, checking_id=proxy["id"])
    res = await asyncio.to_thread(check_proxy, build_proxy_url(proxy))
    await asyncio.to_thread(proxy_store.update_check, proxy["id"], res)
    await _render_menu(bot, cardinal, message.chat.id, bot_msg_id)


@router.callback_query(F.data.startswith("px:check:"))
async def cb_proxy_check(call: CallbackQuery, cardinal, bot: Bot) -> None:
    proxy_id = int(call.data.split(":")[2])
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return
    await call.answer("⏳ Проверяю...")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id, checking_id=proxy_id)
    res = await asyncio.to_thread(check_proxy, build_proxy_url(proxy))
    await asyncio.to_thread(proxy_store.update_check, proxy_id, res)
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data.startswith("px:toggle:"))
async def cb_proxy_toggle(call: CallbackQuery, cardinal, bot: Bot) -> None:
    proxy_id = int(call.data.split(":")[2])
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return

    if proxy["is_active"]:
        # Отключаем — возврат к прямому подключению.
        await asyncio.to_thread(proxy_store.set_active, proxy_id, False)
        _apply_proxy_to_running_account(cardinal, None)
        logger.info("Прокси отключён пользователем %s, Cardinal переходит на прямое подключение",
                    call.from_user.id)
        await call.answer("Прокси отключён — переход на прямое подключение")
        await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)
        return

    # Активация: сначала проверка, чтобы мёртвый прокси не оборвал рабочее подключение.
    await call.answer("⏳ Проверяю перед подключением...")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id, checking_id=proxy_id)
    res = await asyncio.to_thread(check_proxy, build_proxy_url(proxy))
    await asyncio.to_thread(proxy_store.update_check, proxy_id, res)

    if res["ok"]:
        await asyncio.to_thread(proxy_store.set_active, proxy_id, True)
        proxy_url = build_proxy_url(proxy)
        _apply_proxy_to_running_account(cardinal, proxy_url)
        logger.info("Cardinal переключён на прокси %s:%s", proxy["host"], proxy["port"])
    else:
        logger.warning("Прокси %s:%s не прошёл проверку, активация отменена: %s",
                        proxy["host"], proxy["port"], res.get("error"))

    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data.startswith("px:remove:"))
async def cb_proxy_remove(call: CallbackQuery, cardinal, bot: Bot) -> None:
    proxy_id = int(call.data.split(":")[2])
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return
    if proxy["is_active"]:
        _apply_proxy_to_running_account(cardinal, None)
    await asyncio.to_thread(proxy_store.remove_proxy, proxy_id)
    await call.answer("🗑 Прокси удалён")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)
