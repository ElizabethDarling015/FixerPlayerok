"""
Прокси для Cardinal: ДВЕ независимые цели — Playerok (Account/REST + Runner/WS) и
Telegram-сессия бота (aiogram). Один и тот же сохранённый прокси можно активировать
для любой из целей независимо (в т.ч. для обеих сразу, или только для одной) — это
осознанно так, потому что IP может быть рабочим для Telegram, но уже забаненным на
Playerok антибот-защитой (DDoS-Guard), и наоборот. См. cardinal/proxy_store.py.

Навигация: Настройки -> 🌐 Прокси.
На каждый сохранённый прокси — статус по обеим целям и две кнопки-переключателя
(🎮 Playerok / ✈️ Telegram), плюс общая проверка (тестирует обе цели за один тап)
и удаление. Переключение применяется «на лету», без перезапуска бота.
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
from ...proxy_tools import (
    build_proxy_url,
    check_proxy_playerok,
    check_proxy_telegram,
    flag_emoji,
    parse_proxy_text,
    type_label,
)
from .common import nav_row

logger = logging.getLogger(__name__)
router = Router(name="proxy")

_TARGET_LABEL = {"playerok": "🎮 Playerok", "telegram": "✈️ Telegram"}


class ProxyInput(StatesGroup):
    waiting_data = State()


# ──────────────────────────────────────────────
# Применение прокси к уже работающему боту (независимо по целям)
# ──────────────────────────────────────────────

def _apply_playerok_proxy(cardinal, proxy_url: str | None) -> None:
    """
    REST подхватывает изменение сразу (Account.request читает self.proxy при каждом
    запросе), WebSocket — после принудительного обрыва текущего соединения (раннер
    сам переподключится по своей обычной retry-логике, уже с новым прокси).
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


def _apply_telegram_proxy(bot: Bot, proxy_url: str | None) -> None:
    try:
        if proxy_url:
            bot.session.proxy = proxy_url
        else:
            bot.session.clear_proxy()
    except Exception as e:
        logger.warning("Не удалось переключить прокси Telegram-сессии: %s", e)


def _apply(cardinal, bot: Bot, target: str, proxy_url: str | None) -> None:
    if target == "playerok":
        _apply_playerok_proxy(cardinal, proxy_url)
    else:
        _apply_telegram_proxy(bot, proxy_url)


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


def _target_status_line(p: dict, target: str, checking: bool) -> str:
    label = _TARGET_LABEL[target]
    if checking:
        return f"  {label}: ⏳ проверка..."
    if p[f"active_{target}"]:
        return f"  {label}: ✅ активен"
    ok = p.get(f"{target}_ok")
    if ok == 0:
        err = p.get(f"{target}_error")
        suffix = f" — {html.escape(str(err)[:120])}" if err else ""
        return f"  {label}: ❌ не работает{suffix}"
    if ok == 1:
        return f"  {label}: 📶 работает ({p.get(f'{target}_ms')} мс), не активен"
    return f"  {label}: ⚪ не проверялся"


async def _render_menu(bot: Bot, cardinal, chat_id: int, message_id: int,
                        checking_id: int | None = None) -> None:
    """Единственный экран «Меню прокси»."""
    proxies = await asyncio.to_thread(proxy_store.list_proxies)

    lines = [
        "🌐 <b>Меню прокси</b>", "",
        "Playerok и Telegram — независимые цели: один прокси можно включить "
        "для любой из них по отдельности (или для обеих сразу).", "",
    ]
    if proxies:
        for p in proxies:
            checking = checking_id == p["id"]
            lines.append(
                f"• #{p['id']} {flag_emoji(p.get('country_code'))} {type_label(p['proxy_type'])} "
                f"<code>{html.escape(p['host'])}:{p['port']}</code> — {_geo_str(p)}"
            )
            lines.append(_target_status_line(p, "playerok", checking))
            lines.append(_target_status_line(p, "telegram", checking))
    else:
        lines.append("Список пуст. Добавь первый прокси кнопкой ниже.")

    lines.append("")
    lines.append(
        "<i>Флаг --proxy1 / --proxy2 / ... при запуске (номер = порядок добавления, "
        "сверху вниз) разово подключает Telegram-сессию через этот прокси на один "
        "запуск — удобно, когда обычный путь наружу (VPN) недоступен. На Playerok "
        "флаг не влияет.</i>"
    )

    builder = InlineKeyboardBuilder()
    for p in proxies:
        short = f"{flag_emoji(p.get('country_code'))} {type_label(p['proxy_type'])} #{p['id']}"
        pk_label = "🎮 Playerok " + ("✅" if p["active_playerok"] else "⚪")
        tg_label = "✈️ Telegram " + ("✅" if p["active_telegram"] else "⚪")
        builder.row(
            InlineKeyboardButton(text=pk_label, callback_data=f"px:toggle:playerok:{p['id']}"),
            InlineKeyboardButton(text=tg_label, callback_data=f"px:toggle:telegram:{p['id']}"),
        )
        builder.row(
            InlineKeyboardButton(text=f"🔍 Проверить {short}", callback_data=f"px:check:{p['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"px:remove:{p['id']}"),
        )
    builder.row(InlineKeyboardButton(text="➕ Добавить прокси", callback_data="px:add"))
    builder.row(*nav_row(cardinal.l10n, "sys"))

    await _show(bot, chat_id, message_id, "\n".join(lines), builder.as_markup())


async def _check_both(proxy: dict) -> tuple[dict, dict]:
    """
    Гоняет обе проверки ПОСЛЕДОВАТЕЛЬНО (не параллельно), возвращает (res_playerok, res_telegram).
    Параллельный запуск через asyncio.gather тут не используется намеренно: два
    одновременных запроса через один и тот же (иногда и так не быстрый — например,
    датацентровый или зажатый через VPN) канал конкурируют за латентность и повышают
    шанс ложного таймаута одной из проверок, хотя сам прокси при последовательном
    обращении отвечает нормально.
    """
    url = build_proxy_url(proxy)
    res_pk = await asyncio.to_thread(check_proxy_playerok, url)
    res_tg = await asyncio.to_thread(check_proxy_telegram, url)
    return res_pk, res_tg


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

    # Возвращаемся в то же меню, прокси сразу проверяется по обеим целям.
    await _render_menu(bot, cardinal, message.chat.id, bot_msg_id, checking_id=proxy["id"])
    res_pk, res_tg = await _check_both(proxy)
    await asyncio.to_thread(proxy_store.update_check, proxy["id"], "playerok", res_pk)
    await asyncio.to_thread(proxy_store.update_check, proxy["id"], "telegram", res_tg)
    await _render_menu(bot, cardinal, message.chat.id, bot_msg_id)


@router.callback_query(F.data.startswith("px:check:"))
async def cb_proxy_check(call: CallbackQuery, cardinal, bot: Bot) -> None:
    proxy_id = int(call.data.split(":")[2])
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return
    await call.answer("⏳ Проверяю Playerok и Telegram...")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id, checking_id=proxy_id)
    res_pk, res_tg = await _check_both(proxy)
    await asyncio.to_thread(proxy_store.update_check, proxy_id, "playerok", res_pk)
    await asyncio.to_thread(proxy_store.update_check, proxy_id, "telegram", res_tg)
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data.startswith("px:toggle:"))
async def cb_proxy_toggle(call: CallbackQuery, cardinal, bot: Bot) -> None:
    _, _, target, proxy_id_str = call.data.split(":")
    proxy_id = int(proxy_id_str)
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return

    if proxy[f"active_{target}"]:
        # Отключаем эту цель — возврат к прямому подключению именно для неё.
        await asyncio.to_thread(proxy_store.set_active, proxy_id, target, False)
        _apply(cardinal, bot, target, None)
        logger.info("Прокси отключён для %s (id=%s), переход на прямое подключение", target, proxy_id)
        await call.answer(f"{_TARGET_LABEL[target]}: прокси отключён")
        await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)
        return

    # Активация: сначала проверка ИМЕННО этой цели, чтобы мёртвый/забаненный прокси
    # не оборвал рабочее подключение (напоминание: Playerok и Telegram банятся независимо).
    await call.answer(f"⏳ Проверяю {_TARGET_LABEL[target]}...")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id, checking_id=proxy_id)
    check_fn = check_proxy_playerok if target == "playerok" else check_proxy_telegram
    res = await asyncio.to_thread(check_fn, build_proxy_url(proxy))
    await asyncio.to_thread(proxy_store.update_check, proxy_id, target, res)

    if res["ok"]:
        await asyncio.to_thread(proxy_store.set_active, proxy_id, target, True)
        _apply(cardinal, bot, target, build_proxy_url(proxy))
        logger.info("%s переключён на прокси %s:%s", target, proxy["host"], proxy["port"])
    else:
        logger.warning("Прокси %s:%s не прошёл проверку для %s, активация отменена: %s",
                        proxy["host"], proxy["port"], target, res.get("error"))

    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data.startswith("px:remove:"))
async def cb_proxy_remove(call: CallbackQuery, cardinal, bot: Bot) -> None:
    proxy_id = int(call.data.split(":")[2])
    proxy = await asyncio.to_thread(proxy_store.get_proxy, proxy_id)
    if not proxy:
        await call.answer("❌ Прокси не найден", show_alert=True)
        return
    if proxy["active_playerok"]:
        _apply_playerok_proxy(cardinal, None)
    if proxy["active_telegram"]:
        _apply_telegram_proxy(bot, None)
    await asyncio.to_thread(proxy_store.remove_proxy, proxy_id)
    await call.answer("🗑 Прокси удалён")
    await _render_menu(bot, cardinal, call.message.chat.id, call.message.message_id)
