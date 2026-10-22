"""Настройки → «⬆️ Автоподнятие»: экран модуля, все настройки и выбор лотов — в одном сообщении.

Значения вводятся сообщением: бот удаляет его и показывает результат (или «⚠️ …») в этом же
сообщении. Переключатели (вкл/выкл, режим, ночь, «проверок подряд») — нажатием.
Логика поднятия — `fixer/autoraise.py`.
"""
from __future__ import annotations

import asyncio
import datetime
import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from ...autoraise import _is_active, _is_premium, current_interval, is_night, target_position
from ...settings import _check_hhmm, save_main_settings
from .common import nav_row, paginate, pager_row, remember_panel, safe_edit, show_in_panel, with_error

router = Router(name="autoraise")

SEPARATOR = "━━━━━━━━━━━━━━━━━━━"
LOTS_PER_PAGE = 10
NAME_LIMIT = 34

#: Поля ввода: ключ → (атрибут настроек, тип, мин, макс, множитель для хранения).
FIELDS = {
    "pos": ("position", "int", 1, 500, 1),
    "npos": ("night_position", "int", 1, 500, 1),
    "chk": ("check_interval", "min", 1, 1440, 60),
    "cd": ("cooldown", "min", 0, 10080, 60),
    "int": ("interval", "min", 5, 10080, 60),
    "nint": ("night_interval", "min", 5, 10080, 60),
    "dl": ("day_limit", "rub", 0, 1_000_000, 1),
    "nl": ("night_limit", "rub", 0, 1_000_000, 1),
    "res": ("min_balance_reserve", "rub", 0, 1_000_000, 1),
    "nf": ("night_from", "time", None, None, None),
    "nt": ("night_to", "time", None, None, None),
}

#: Последний загруженный список лотов (tg_user_id → [(id, name, premium, active)]).
_lots_cache: dict[int, list[tuple[str, str, bool, bool]]] = {}


class RaiseInput(StatesGroup):
    value = State()


def _kb(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in rows if r])


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _minutes(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    if minutes >= 60 and minutes % 60 == 0:
        return f"{minutes // 60} ч"
    return f"{minutes} мин"


def _rub(value: int) -> str:
    return f"{value:,} ₽".replace(",", " ")


def _limit(value: int, l10n) -> str:
    return _rub(value) if value else l10n("up_no_limit")


def _short(name: str) -> str:
    return name if len(name) <= NAME_LIMIT else name[:NAME_LIMIT - 1].rstrip() + "…"


def build_screen(fixer, now: datetime.datetime | None = None) -> tuple[str, InlineKeyboardMarkup]:
    l10n = fixer.l10n
    service = fixer.autoraise
    cfg = fixer.settings.autoraise
    now = now or service.now()
    night = is_night(cfg, now)
    window = service.window()
    spent = service.spent_in(window)
    state = service.state
    enabled = service.enabled

    lines = [l10n("up_title", status=l10n("up_on" if enabled else "up_off"),
                  time=l10n("up_night" if night else ("up_day" if cfg.night_enabled else "up_allday")))]
    if cfg.mode == "position":
        lines.append(l10n("up_mode_position_line", position=target_position(cfg, now)))
        lines.append(l10n("up_position_params", check=_minutes(cfg.check_interval), cooldown=_minutes(cfg.cooldown),
                          streak=cfg.streak))
    else:
        lines.append(l10n("up_mode_interval_line", interval=_minutes(current_interval(cfg, now))))
        nxt = service.next_interval_run()
        if enabled and nxt:
            lines.append(l10n("up_next_run", time=nxt.strftime("%d.%m %H:%M")))
    if cfg.night_enabled:
        night_value = (l10n("up_night_pos", position=cfg.night_position) if cfg.mode == "position"
                       else l10n("up_night_int", interval=_minutes(cfg.night_interval)))
        lines.append(l10n("up_night_line", start=cfg.night_from, end=cfg.night_to, value=night_value,
                          limit=_limit(cfg.night_limit, l10n)))
    lines.append(l10n("up_spent_line", window=l10n("raise_window_" + window.kind), spent=_rub(spent),
                      limit=_limit(window.limit, l10n)))
    if cfg.min_balance_reserve:
        lines.append(l10n("up_reserve_line", reserve=_rub(cfg.min_balance_reserve)))

    lines.append(SEPARATOR)
    if not cfg.items:
        lines.append(l10n("up_no_items"))
    else:
        if cfg.mode == "position":
            checked = state.get("last_check") or 0
            head = l10n("up_positions_head")
            if checked:
                head += " " + l10n("up_checked_at", time=service.local(checked).strftime("%H:%M"))
            lines.append(head)
        else:
            lines.append(l10n("up_items_head"))
        target = target_position(cfg, now)
        for item_id in cfg.items:
            entry = state["positions"].get(item_id, {})
            name = html.escape(_short(entry.get("name") or state["names"].get(item_id) or item_id[:8]))
            lines.append("• " + name + " — " + _item_status(l10n, cfg, entry, target))
    lines.append(SEPARATOR)
    lines.append(l10n("up_hint"))

    rows = [[_btn(l10n("up_btn_on" if enabled else "up_btn_off"), "up:on"),
             _btn(l10n("up_btn_mode_position" if cfg.mode == "position" else "up_btn_mode_interval"), "up:mode")]]
    if cfg.mode == "position":
        rows.append([_btn(l10n("up_btn_pos", value=cfg.position), "up:in:pos"),
                     _btn(l10n("up_btn_chk", value=_minutes(cfg.check_interval)), "up:in:chk")])
        rows.append([_btn(l10n("up_btn_cd", value=_minutes(cfg.cooldown)), "up:in:cd"),
                     _btn(l10n("up_btn_streak", value=cfg.streak), "up:streak")])
    else:
        rows.append([_btn(l10n("up_btn_int", value=_minutes(cfg.interval)), "up:in:int")])
    rows.append([_btn(l10n("up_btn_dl" if cfg.night_enabled else "up_btn_dl_all", value=_limit(cfg.day_limit, l10n)),
                      "up:in:dl"),
                 _btn(l10n("up_btn_res", value=_rub(cfg.min_balance_reserve)), "up:in:res")])
    rows.append([_btn(l10n("up_btn_night_on" if cfg.night_enabled else "up_btn_night_off"), "up:night")])
    if cfg.night_enabled:
        rows.append([_btn(l10n("up_btn_nf", value=cfg.night_from), "up:in:nf"),
                     _btn(l10n("up_btn_nt", value=cfg.night_to), "up:in:nt")])
        night_btn = (_btn(l10n("up_btn_npos", value=cfg.night_position), "up:in:npos") if cfg.mode == "position"
                     else _btn(l10n("up_btn_nint", value=_minutes(cfg.night_interval)), "up:in:nint"))
        rows.append([night_btn, _btn(l10n("up_btn_nl", value=_limit(cfg.night_limit, l10n)), "up:in:nl")])
    rows.append([_btn(l10n("up_btn_lots", count=len(cfg.items)), "up:l:0"), _btn(l10n("ld_btn_refresh"), "up")])
    rows.append(nav_row(l10n, "sys"))
    return "\n".join(lines), _kb(rows)


def _item_status(l10n, cfg, entry: dict, target: int) -> str:
    note = entry.get("note")
    if note in ("not_premium", "not_active", "not_found", "error"):
        return l10n("up_item_" + note)
    if cfg.mode != "position":
        return l10n("up_item_waiting")
    pos = entry.get("pos")
    if pos is None:
        return l10n("up_item_unchecked")
    if pos <= target:
        return l10n("up_item_ok", pos=pos)
    return l10n("up_item_low", pos=pos, streak=entry.get("streak", 0), need=cfg.streak)


def build_lots_screen(l10n, lots: list[tuple[str, str, bool, bool]], marked: list[str], page: int,
                      names: dict | None = None) -> tuple[str, InlineKeyboardMarkup]:
    names = names or {}
    premium = [lot for lot in lots if lot[2] and lot[3]]
    others = len([lot for lot in lots if lot[3] and not lot[2]])
    known = {lot[0] for lot in premium}
    # Отмеченные, которых нет среди активных премиум-лотов, — тоже в списке (чтобы снять отметку).
    lost = [(item_id, names.get(item_id) or item_id[:8], False, False) for item_id in marked if item_id not in known]
    rows_src = premium + lost
    chunk, page, pages, _ = paginate(rows_src, page, LOTS_PER_PAGE)
    text = [l10n("up_lots_title"), SEPARATOR, l10n("up_lots_hint")]
    if not rows_src:
        text.append(l10n("up_lots_empty"))
    if others:
        text.append(l10n("up_lots_regular", count=others))
    rows = []
    for item_id, name, is_premium, _active in chunk:
        on = item_id in marked
        mark = "✅" if on else "▫️"
        warn = "" if is_premium else " ⚠️"
        rows.append([_btn(f"{mark} {_short(name)}{warn}", f"up:t:{item_id}")])
    pager = pager_row("up:l", page, pages)
    if pager:
        rows.append(pager)
    rows.append([_btn(l10n("btn_back"), "up"), *nav_row(l10n)])
    return "\n".join(text), _kb(rows)


def _input_screen(l10n, key: str, fixer) -> tuple[str, InlineKeyboardMarkup]:
    cfg = fixer.settings.autoraise
    attr, kind, lo, hi, mult = FIELDS[key]
    current = getattr(cfg, attr)
    if kind == "min":
        shown = _minutes(current)
    elif kind == "rub":
        shown = _limit(current, l10n) if attr != "min_balance_reserve" else _rub(current)
    else:
        shown = str(current)
    text = (l10n("up_title_short") + "\n" + SEPARATOR + "\n"
            + l10n("up_in_" + key, current=html.escape(shown), lo=lo, hi=hi))
    return text, _kb([[_btn(l10n("wd_btn_cancel"), "up:cancel")]])


def parse_value(key: str, raw: str) -> tuple[object | None, str | None]:
    """Значение для поля или (None, ключ ошибки)."""
    attr, kind, lo, hi, mult = FIELDS[key]
    raw = (raw or "").strip().replace(" ", "").replace("₽", "")
    if kind == "time":
        try:
            return _check_hhmm(raw.replace(".", ":")), None
        except ValueError:
            return None, "up_err_time"
    if not raw.isdigit():
        return None, "up_err_number"
    value = int(raw)
    if not lo <= value <= hi:
        return None, "up_err_range"
    return value * mult, None


async def _answer(query: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(Exception):
        await query.answer(text, show_alert=alert)


async def _show(query: CallbackQuery, fixer) -> None:
    text, markup = build_screen(fixer)
    await safe_edit(query.message, text, markup)


def _save(fixer) -> None:
    save_main_settings(fixer.settings)


@router.callback_query(F.data == "up")
async def cb_screen(query: CallbackQuery, fixer, state: FSMContext) -> None:
    await state.clear()
    await _answer(query)
    await _show(query, fixer)


@router.callback_query(F.data == "up:cancel")
async def cb_cancel(query: CallbackQuery, fixer, state: FSMContext) -> None:
    await cb_screen(query, fixer, state)


@router.callback_query(F.data == "up:on")
async def cb_toggle(query: CallbackQuery, fixer) -> None:
    modules = fixer.settings.modules
    modules.autoraise = not modules.autoraise
    _save(fixer)
    if modules.autoraise and fixer.settings.autoraise.mode == "interval":
        fixer.autoraise.reset_interval_clock()
    logger.info("[autoraise] Автоподнятие {}", "включено" if modules.autoraise else "выключено")
    await _answer(query)
    await _show(query, fixer)


@router.callback_query(F.data == "up:mode")
async def cb_mode(query: CallbackQuery, fixer) -> None:
    cfg = fixer.settings.autoraise
    cfg.mode = "interval" if cfg.mode == "position" else "position"
    _save(fixer)
    if cfg.mode == "interval":
        fixer.autoraise.reset_interval_clock()
    else:
        fixer.autoraise.state["last_check"] = 0  # проверить места сразу
    await _answer(query)
    await _show(query, fixer)


@router.callback_query(F.data == "up:night")
async def cb_night(query: CallbackQuery, fixer) -> None:
    cfg = fixer.settings.autoraise
    cfg.night_enabled = not cfg.night_enabled
    _save(fixer)
    await _answer(query)
    await _show(query, fixer)


@router.callback_query(F.data == "up:streak")
async def cb_streak(query: CallbackQuery, fixer) -> None:
    cfg = fixer.settings.autoraise
    cfg.streak = cfg.streak % 3 + 1
    _save(fixer)
    await _answer(query)
    await _show(query, fixer)


@router.callback_query(F.data.startswith("up:in:"))
async def cb_input(query: CallbackQuery, fixer, state: FSMContext) -> None:
    key = query.data.split(":", 2)[2]
    if key not in FIELDS:
        await _answer(query)
        return
    await state.set_state(RaiseInput.value)
    await state.update_data(field=key)
    await remember_panel(state, query.message)
    await _answer(query)
    text, markup = _input_screen(fixer.l10n, key, fixer)
    await safe_edit(query.message, text, markup)


@router.message(StateFilter(RaiseInput.value))
async def on_input(message: Message, state: FSMContext, fixer) -> None:
    l10n = fixer.l10n
    key = (await state.get_data()).get("field")
    if key not in FIELDS:
        await state.clear()
        return
    value, error = parse_value(key, message.text or "")
    if error:
        attr, _, lo, hi, _ = FIELDS[key]
        text, markup = _input_screen(l10n, key, fixer)
        await show_in_panel(message, state, with_error(l10n(error, lo=lo, hi=hi), text), markup)
        return
    attr = FIELDS[key][0]
    setattr(fixer.settings.autoraise, attr, value)
    _save(fixer)
    if key in ("int", "nint"):
        fixer.autoraise.reset_interval_clock()
    if key in ("pos", "npos", "chk"):
        fixer.autoraise.state["last_check"] = 0  # новое значение — проверим места сразу
    logger.info("[autoraise] {} = {}", attr, value)
    text, markup = build_screen(fixer)
    await show_in_panel(message, state, text, markup)
    await state.clear()


async def _load_lots(fixer) -> list[tuple[str, str, bool, bool]]:
    # Как «🛍 Товары»: постранично по 24 (страница больше — Playerok отвечает 403).
    from ...storefront import ACTIVE_STATUSES, fetch_items
    items = await asyncio.to_thread(fetch_items, fixer.account, ACTIVE_STATUSES)
    lots = []
    for it in items:
        if getattr(it, "id", None):
            lots.append((it.id, it.name or it.id, _is_premium(it), _is_active(it)))
    return lots


@router.callback_query(F.data.regexp(r"^up:l:\d+$"))
async def cb_lots(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    if fixer.account is None or not getattr(fixer, "playerok_connected", False):
        await _answer(query, l10n("up_offline"), alert=True)
        return
    await _answer(query)
    page = int(query.data.rsplit(":", 1)[1])
    try:
        lots = await _load_lots(fixer)
    except Exception as exc:
        logger.warning("[autoraise] Список лотов не загрузился: {}", exc)
        await _answer(query, l10n("up_lots_failed", error=str(exc)[:150]), alert=True)
        return
    _lots_cache[query.from_user.id] = lots
    text, markup = build_lots_screen(l10n, lots, fixer.settings.autoraise.items, page,
                                     fixer.autoraise.state["names"])
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data.startswith("up:t:"))
async def cb_toggle_lot(query: CallbackQuery, fixer) -> None:
    item_id = query.data.split(":", 2)[2]
    lots = _lots_cache.get(query.from_user.id) or []
    lot = next((lot for lot in lots if lot[0] == item_id), None)
    cfg = fixer.settings.autoraise
    on = item_id not in cfg.items
    if on and (lot is None or not (lot[2] and lot[3])):
        await _answer(query, fixer.l10n("up_lot_not_premium"), alert=True)
        return
    fixer.autoraise.set_marked(item_id, lot[1] if lot else None, on)
    if on:
        fixer.autoraise.state["last_check"] = 0
    _save(fixer)
    await _answer(query)
    # Остаёмся на той же странице списка.
    marked_page = 0
    premium = [x for x in lots if x[2] and x[3]]
    ids = [x[0] for x in premium]
    if item_id in ids:
        marked_page = ids.index(item_id) // LOTS_PER_PAGE
    text, markup = build_lots_screen(fixer.l10n, lots, cfg.items, marked_page, fixer.autoraise.state["names"])
    await safe_edit(query.message, text, markup)


__all__ = ["router", "build_screen", "build_lots_screen", "parse_value"]
