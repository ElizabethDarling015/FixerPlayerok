"""Раздел «💳 Вывод средств» (главное меню).

Шаги: способ → реквизиты → сумма → подтверждение → заявка на Playerok.

* Способы, комиссии и лимиты берутся с Playerok при каждом открытии раздела (тот же запрос,
  что страница вывода на сайте), так что изменения на сайте видны сразу.
* Поддержаны СБП (телефон, сохранённый на сайте, + банк), карта РФ (привязанная на сайте)
  и USDT TRC20 (адрес). Остальные способы показываются, но выводить ими — на сайте.
* Ничего не отправляется без отдельного нажатия «✅ Вывести» на экране подтверждения.
  Данные заявки при этом сразу стираются — повторное нажатие не создаст вторую заявку.
* Последний способ и банк/карта/адрес запоминаются в `storage/withdrawal.json` — кнопка
  «⚡ Как в прошлый раз» ведёт сразу к вводу суммы. Телефон там не хранится: его отдаёт Playerok.
"""
from __future__ import annotations

import asyncio
import html
import json
import os
import re
from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from ...settings import STORAGE_DIR
from .common import nav_row, safe_edit

router = Router(name="withdrawal")

#: Способы, которые бот умеет выводить сам (остальные — только на сайте).
SUPPORTED = ("SBP", "BANK_CARD_RU", "USDT")
#: Не способы вывода «наружу»: внутренний баланс и замороженные средства.
_HIDDEN = {"LOCAL", "PENDING_INCOME"}
#: Сколько банков СБП показывать кнопками сразу (дальше — поиск по названию).
TOP_BANKS = 8
REMEMBER_FILE = os.path.join(STORAGE_DIR, "withdrawal.json")

_USDT_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


class WithdrawStates(StatesGroup):
    phone = State()
    bank_search = State()
    usdt_address = State()
    amount = State()


# ----------------------------------------------------------------------
# Вспомогательное: формат, маскирование, комиссия, запоминание
# ----------------------------------------------------------------------

def money(value) -> str:
    try:
        return f"{int(value):,}".replace(",", " ") + " ₽"
    except (TypeError, ValueError):
        return f"{value} ₽"


def mask_phone(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 6:
        return phone or "?"
    return f"+{digits[0]} {digits[1:4]} ••• •• {digits[-2:]}"


def mask_card(first_six: str | None, last_four: str | None) -> str:
    first = (first_six or "")[:4] or "••••"
    return f"{first} •••• •••• {last_four or '••••'}"


def mask_address(address: str | None) -> str:
    address = address or ""
    return f"{address[:5]}…{address[-4:]}" if len(address) > 12 else address


def estimate_fee(provider, amount: int) -> int:
    """Оценка комиссии Playerok: процент от суммы, но не меньше минимальной."""
    percent = float(getattr(provider, "fee", 0) or 0)
    fee = round(amount * percent / 100)
    return max(fee, int(getattr(provider, "min_fee_amount", 0) or 0))


def normalize_phone(text: str) -> str | None:
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10 and digits[0] == "9":
        return "+7" + digits
    return None


def load_remembered() -> dict | None:
    try:
        with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and data.get("provider") in SUPPORTED else None
    except Exception:
        return None


def save_remembered(data: dict) -> None:
    """Запоминает способ и банк/карту/адрес (без телефона и без суммы)."""
    keep = {k: data[k] for k in ("provider", "bank_id", "bank_name", "card_id", "card_label", "account")
            if data.get(k) and not (k == "account" and data.get("provider") == "SBP")}
    try:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False)
    except Exception as exc:
        logger.warning("[withdraw] Не удалось запомнить способ вывода: {}", exc)


def destination_label(data: dict) -> str:
    """«СБП · Сбербанк · +7 919 ••• •• 22» / «Карта 2200 •••• •••• 1234» / «USDT TXyz…abcd»."""
    provider = data.get("provider")
    if provider == "SBP":
        return f"СБП · {data.get('bank_name', '?')} · {mask_phone(data.get('account'))}"
    if provider == "BANK_CARD_RU":
        return f"Карта {data.get('card_label', '?')}"
    if provider == "USDT":
        return f"USDT (TRC20) · {mask_address(data.get('account'))}"
    return provider or "?"


def _kb(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


async def _answer(query: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(Exception):
        await query.answer(text, show_alert=alert)


# ----------------------------------------------------------------------
# Данные с Playerok
# ----------------------------------------------------------------------

async def _withdrawable(fixer) -> int | None:
    account = fixer.account
    with suppress(Exception):
        await asyncio.to_thread(account.get_balance)
    balance = getattr(getattr(account, "profile", None), "balance", None)
    value = getattr(balance, "withdrawable", None)
    if value is None:
        value = getattr(balance, "available", None)
    return int(value) if value is not None else None


async def _providers(fixer) -> dict:
    providers = await asyncio.to_thread(fixer.account.get_withdrawal_providers)
    return {p.id: p for p in providers if p.id and p.id not in _HIDDEN}


# ----------------------------------------------------------------------
# Экраны
# ----------------------------------------------------------------------

def build_main_screen(l10n, providers: dict, withdrawable, remembered: dict | None):
    lines = [l10n("wd_title"), "", l10n("wd_available", amount=money(withdrawable) if withdrawable is not None else "?"), ""]
    lines.append(l10n("wd_methods_header"))
    for pid, p in providers.items():
        fee = f"{p.fee:g}%" if p.fee is not None else "?"
        min_fee = f", мин. {money(p.min_fee_amount)}" if p.min_fee_amount else ""
        limits = f"{money(p.min_out)} – {money(p.max_out)}" if p.min_out is not None and p.max_out else "—"
        mark = "" if pid in SUPPORTED else " · " + l10n("wd_site_only")
        lines.append(f"• <b>{html.escape(p.name or pid)}</b> — {fee}{min_fee} · {limits}{mark}")
    rows = []
    if remembered and remembered.get("provider") in providers:
        rows.append([_btn(l10n("wd_btn_repeat", label=destination_label(
            {**remembered, "account": providers[remembered["provider"]].saved_account
             if remembered["provider"] == "SBP" else remembered.get("account")})), "wd:repeat")])
    method_buttons = [_btn(providers[pid].name or pid, f"wd:m:{pid}") for pid in SUPPORTED if pid in providers]
    for i in range(0, len(method_buttons), 2):
        rows.append(method_buttons[i:i + 2])
    rows.append(nav_row(l10n))
    return "\n".join(lines), _kb(rows)


def build_banks_screen(l10n, banks, page_title: str):
    rows = [[_btn(b.name, f"wd:b:{b.id}")] for b in banks]
    rows.append([_btn(l10n("wd_btn_bank_search"), "wd:bsearch")])
    rows.append([_btn(l10n("btn_back"), "wd"), *nav_row(l10n)])
    return page_title, _kb(rows)


def build_amount_screen(l10n, data: dict, withdrawable) -> tuple[str, InlineKeyboardMarkup]:
    text = l10n(
        "wd_amount_prompt",
        destination=html.escape(destination_label(data)),
        available=money(withdrawable) if withdrawable is not None else "?",
        min=money(data.get("min_out")) if data.get("min_out") is not None else "—",
        max=money(data.get("max_out")) if data.get("max_out") is not None else "—",
    )
    rows = []
    if withdrawable and _amount_error(data, withdrawable, withdrawable) is None:
        rows.append([_btn(l10n("wd_btn_all", amount=money(withdrawable)), f"wd:all:{int(withdrawable)}")])
    rows.append([_btn(l10n("wd_btn_cancel"), "wd")])
    return text, _kb(rows)


def _amount_error(data: dict, amount: int, withdrawable) -> str | None:
    if amount <= 0:
        return "wd_err_amount"
    if data.get("min_out") is not None and amount < data["min_out"]:
        return "wd_err_min"
    if data.get("max_out") is not None and amount > data["max_out"]:
        return "wd_err_max"
    if withdrawable is not None and amount > withdrawable:
        return "wd_err_balance"
    return None


def build_confirm_screen(l10n, data: dict, amount: int, provider, usdt_rate=None):
    fee = estimate_fee(provider, amount)
    extra = ""
    if data.get("provider") == "USDT" and usdt_rate:
        extra = "\n" + l10n("wd_usdt_estimate", usdt=f"{amount / usdt_rate:.2f}", rate=f"{usdt_rate:g}")
    text = l10n(
        "wd_confirm",
        amount=money(amount),
        destination=html.escape(destination_label(data)),
        fee=money(fee),
        fee_rule=html.escape(f"{getattr(provider, 'fee', 0):g}%" + (
            f", мин. {money(provider.min_fee_amount)}" if getattr(provider, "min_fee_amount", None) else "")),
    ) + extra
    return text, _kb([[_btn(l10n("wd_btn_go"), "wd:go"), _btn(l10n("wd_btn_cancel"), "wd")]])


# ----------------------------------------------------------------------
# Хендлеры
# ----------------------------------------------------------------------

async def _require_online(fixer, query: CallbackQuery) -> bool:
    if fixer.account is not None:
        return True
    await _answer(query, fixer.l10n("wd_offline"), alert=True)
    return False


async def _show_main(query: CallbackQuery, fixer, state: FSMContext) -> None:
    l10n = fixer.l10n
    await state.clear()
    try:
        providers = await _providers(fixer)
    except Exception as exc:
        logger.exception("[withdraw] Не удалось получить способы вывода")
        await safe_edit(query.message, l10n("wd_title") + "\n\n" + l10n("wd_failed", error=html.escape(str(exc)[:200])),
                        _kb([nav_row(l10n)]))
        return
    withdrawable = await _withdrawable(fixer)
    await state.update_data(providers_seen=True)
    text, markup = build_main_screen(l10n, providers, withdrawable, load_remembered())
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "wd")
async def cb_main(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    await _show_main(query, fixer, state)


async def _go_amount(target: Message, fixer, state: FSMContext, data: dict, edit: bool = True) -> None:
    """Сохраняет выбор в FSM и показывает ввод суммы."""
    providers = await _providers(fixer)
    provider = providers.get(data["provider"])
    if provider is None:
        await target.answer(fixer.l10n("wd_err_provider_gone"))
        return
    data = {**data, "min_out": provider.min_out, "max_out": provider.max_out}
    withdrawable = await _withdrawable(fixer)
    await state.set_state(WithdrawStates.amount)
    await state.update_data(order=data)
    text, markup = build_amount_screen(fixer.l10n, data, withdrawable)
    if edit:
        await safe_edit(target, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("wd:m:"))
async def cb_method(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    l10n = fixer.l10n
    pid = query.data.split(":", 2)[2]
    providers = await _providers(fixer)
    provider = providers.get(pid)
    if provider is None or pid not in SUPPORTED:
        await _answer(query, l10n("wd_err_provider_gone"), alert=True)
        return

    if pid == "SBP":
        phone = provider.saved_account
        await state.update_data(order={"provider": "SBP", "account": phone})
        if not phone:
            await state.set_state(WithdrawStates.phone)
            await safe_edit(query.message, l10n("wd_enter_phone"), _kb([[_btn(l10n("wd_btn_cancel"), "wd")]]))
            return
        await _show_banks(query.message, fixer)
    elif pid == "BANK_CARD_RU":
        try:
            cards_page = await asyncio.to_thread(fixer.account.get_verified_cards, 24)
            cards = list(cards_page.cards) if cards_page and getattr(cards_page, "cards", None) else []
        except Exception as exc:
            logger.exception("[withdraw] Не удалось получить привязанные карты")
            await safe_edit(query.message, l10n("wd_failed", error=html.escape(str(exc)[:200])),
                            _kb([[_btn(l10n("btn_back"), "wd")]]))
            return
        if not cards:
            await safe_edit(query.message, l10n("wd_no_cards"), _kb([[_btn(l10n("btn_back"), "wd")]]))
            return
        rows = [[_btn(f"💳 {mask_card(c.card_first_six, c.card_last_four)}", f"wd:c:{c.id}")] for c in cards]
        rows.append([_btn(l10n("btn_back"), "wd")])
        await state.update_data(cards={c.id: mask_card(c.card_first_six, c.card_last_four) for c in cards})
        await safe_edit(query.message, l10n("wd_choose_card"), _kb(rows))
    elif pid == "USDT":
        await state.update_data(order={"provider": "USDT"})
        await state.set_state(WithdrawStates.usdt_address)
        await safe_edit(query.message, l10n("wd_enter_usdt"), _kb([[_btn(l10n("wd_btn_cancel"), "wd")]]))


async def _show_banks(message: Message, fixer, edit: bool = True) -> None:
    l10n = fixer.l10n
    try:
        banks = await asyncio.to_thread(fixer.account.get_sbp_banks)
    except Exception as exc:
        logger.exception("[withdraw] Не удалось получить список банков СБП")
        text, markup = l10n("wd_failed", error=html.escape(str(exc)[:200])), _kb([[_btn(l10n("btn_back"), "wd")]])
    else:
        text, markup = build_banks_screen(l10n, banks[:TOP_BANKS], l10n("wd_choose_bank"))
    if edit:
        await safe_edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(WithdrawStates.phone, F.text)
async def msg_phone(message: Message, fixer, state: FSMContext) -> None:
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer(fixer.l10n("wd_err_phone"))
        return
    data = (await state.get_data()).get("order") or {}
    await state.update_data(order={**data, "provider": "SBP", "account": phone})
    await state.set_state(None)
    await _show_banks(message, fixer, edit=False)


@router.callback_query(F.data == "wd:bsearch")
async def cb_bank_search(query: CallbackQuery, fixer, state: FSMContext) -> None:
    await _answer(query)
    await state.set_state(WithdrawStates.bank_search)
    await safe_edit(query.message, fixer.l10n("wd_enter_bank"), _kb([[_btn(fixer.l10n("wd_btn_cancel"), "wd")]]))


@router.message(WithdrawStates.bank_search, F.text)
async def msg_bank_search(message: Message, fixer, state: FSMContext) -> None:
    l10n = fixer.l10n
    needle = message.text.strip().casefold()
    try:
        banks = await asyncio.to_thread(fixer.account.get_sbp_banks)
    except Exception as exc:
        await message.answer(l10n("wd_failed", error=html.escape(str(exc)[:200])))
        return
    found = [b for b in banks if needle in b.name.casefold()][:TOP_BANKS]
    if not found:
        await message.answer(l10n("wd_err_bank_not_found"))
        return
    await state.set_state(None)
    text, markup = build_banks_screen(l10n, found, l10n("wd_choose_bank"))
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("wd:b:"))
async def cb_bank(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    bank_id = query.data.split(":", 2)[2]
    try:
        banks = await asyncio.to_thread(fixer.account.get_sbp_banks)
    except Exception:
        banks = []
    bank_name = next((b.name for b in banks if b.id == bank_id), bank_id)
    data = (await state.get_data()).get("order") or {}
    if data.get("provider") != "SBP" or not data.get("account"):
        await _show_main(query, fixer, state)
        return
    await _go_amount(query.message, fixer, state, {**data, "bank_id": bank_id, "bank_name": bank_name})


@router.callback_query(F.data.startswith("wd:c:"))
async def cb_card(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    card_id = query.data.split(":", 2)[2]
    label = ((await state.get_data()).get("cards") or {}).get(card_id, "•••• ••••")
    await _go_amount(query.message, fixer, state,
                     {"provider": "BANK_CARD_RU", "account": card_id, "card_id": card_id, "card_label": label})


@router.message(WithdrawStates.usdt_address, F.text)
async def msg_usdt(message: Message, fixer, state: FSMContext) -> None:
    address = message.text.strip()
    if not _USDT_RE.match(address):
        await message.answer(fixer.l10n("wd_err_usdt"))
        return
    await _go_amount(message, fixer, state, {"provider": "USDT", "account": address}, edit=False)


@router.callback_query(F.data == "wd:repeat")
async def cb_repeat(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    remembered = load_remembered()
    if not remembered:
        await _show_main(query, fixer, state)
        return
    data = dict(remembered)
    if data["provider"] == "SBP":
        providers = await _providers(fixer)
        phone = getattr(providers.get("SBP"), "saved_account", None)
        if not phone:
            # Телефон на сайте больше не сохранён — проходим выбор заново.
            await _show_main(query, fixer, state)
            return
        data["account"] = phone
    elif data["provider"] == "BANK_CARD_RU":
        data["account"] = data.get("card_id")
    await _go_amount(query.message, fixer, state, data)


async def _to_confirm(target: Message, fixer, state: FSMContext, amount: int, edit: bool) -> None:
    l10n = fixer.l10n
    data = (await state.get_data()).get("order") or {}
    if not data.get("provider"):
        await target.answer(l10n("wd_err_expired"))
        return
    withdrawable = await _withdrawable(fixer)
    error = _amount_error(data, amount, withdrawable)
    if error:
        await target.answer(l10n(error, min=money(data.get("min_out")), max=money(data.get("max_out")),
                                 available=money(withdrawable)))
        return
    providers = await _providers(fixer)
    provider = providers.get(data["provider"])
    rate = None
    if data["provider"] == "USDT":
        with suppress(Exception):
            rate = await asyncio.to_thread(fixer.account.get_exchange_rate, "USDT_RUB")
    await state.set_state(None)
    await state.update_data(order={**data, "amount": amount})
    text, markup = build_confirm_screen(l10n, data, amount, provider, rate)
    if edit:
        await safe_edit(target, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("wd:all:"))
async def cb_all(query: CallbackQuery, fixer, state: FSMContext) -> None:
    if not await _require_online(fixer, query):
        return
    await _answer(query)
    await _to_confirm(query.message, fixer, state, int(query.data.rsplit(":", 1)[1]), edit=True)


@router.message(WithdrawStates.amount, F.text)
async def msg_amount(message: Message, fixer, state: FSMContext) -> None:
    digits = re.sub(r"[\s₽рруб.]", "", message.text or "", flags=re.IGNORECASE)
    if not digits.isdigit():
        await message.answer(fixer.l10n("wd_err_amount"))
        return
    await _to_confirm(message, fixer, state, int(digits), edit=False)


@router.callback_query(F.data == "wd:go")
async def cb_go(query: CallbackQuery, fixer, state: FSMContext) -> None:
    l10n = fixer.l10n
    if not await _require_online(fixer, query):
        return
    data = (await state.get_data()).get("order") or {}
    # Заявку стираем ДО запроса: второе нажатие «Вывести» не создаст вторую заявку.
    await state.clear()
    if not data.get("amount") or not data.get("account"):
        await _answer(query, l10n("wd_err_expired"), alert=True)
        return
    await _answer(query)
    await safe_edit(query.message, l10n("wd_sending"), None)
    try:
        tx = await asyncio.to_thread(
            fixer.account.request_withdrawal,
            data["provider"], data["account"], data["amount"],
            data.get("bank_id") if data["provider"] == "SBP" else None,
        )
    except Exception as exc:
        logger.exception("[withdraw] Заявка на вывод не создана")
        await safe_edit(query.message, l10n("wd_failed", error=html.escape(str(exc)[:300])),
                        _kb([[_btn(l10n("btn_back"), "wd")], nav_row(l10n)]))
        return
    save_remembered(data)
    status = getattr(getattr(tx, "status", None), "name", None) or "?"
    logger.info("[withdraw] Заявка {} на {} ₽ ({}) создана из Telegram, статус {}",
                getattr(tx, "id", "?"), data["amount"], data["provider"], status)
    await safe_edit(query.message, l10n(
        "wd_done",
        amount=money(data["amount"]),
        destination=html.escape(destination_label(data)),
        status=html.escape(l10n("wd_status_" + status.lower()) if status in ("PENDING", "PROCESSING", "CONFIRMED") else status),
        tx_id=html.escape(getattr(tx, "id", None) or "—"),
    ), _kb([nav_row(l10n)]))
