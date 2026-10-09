"""Вывод средств: запрос как у сайта, разбор способов, весь путь в Telegram на моках."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fixer.tg.handlers import withdrawal as wd
from fixer_helpers import make_fixer
from playerokapi import parser
from playerokapi.account import Account


# ----------------------------------------------------------------------
# Библиотека
# ----------------------------------------------------------------------

def test_request_withdrawal_matches_site_request():
    """Поля — ровно как в HAR со страницы вывода (provider/account/value/providerData)."""
    account = Account.__new__(Account)
    account._query = MagicMock(return_value={"requestWithdrawal": {"id": "tx-1", "status": "PENDING", "value": 2000}})
    tx = account.request_withdrawal("SBP", "+79000000000", 2000, sbp_bank_member_id="100000000111")
    name, variables = account._query.call_args.args
    assert name == "requestWithdrawal"
    assert variables == {"input": {"provider": "SBP", "account": "+79000000000", "value": 2000,
                                   "providerData": {"paymentMethodId": None, "sbpBankMemberId": "100000000111"}}}
    assert tx.id == "tx-1"


def test_provider_limits_and_saved_account_parsed():
    raw = {"id": "SBP", "name": "СБП", "fee": 6, "minFeeAmount": 60,
           "limits": {"outgoing": {"min": 500, "max": 79000}}, "account": {"value": "+79000000000"}}
    p = parser.transaction_provider(raw)
    assert (p.min_out, p.max_out, p.saved_account, p.fee, p.min_fee_amount) == (500, 79000, "+79000000000", 6, 60)


# ----------------------------------------------------------------------
# Формат и проверки
# ----------------------------------------------------------------------

def test_masking():
    assert wd.mask_phone("+79191234522") == "+7 919 ••• •• 22"
    assert wd.mask_card("220070", "1234") == "2200 •••• •••• 1234"
    assert wd.mask_address("TXYZabcdefghijkmnopqrstuvwxyz12345") == "TXYZa…2345"


def test_fee_estimate_uses_minimum():
    provider = SimpleNamespace(fee=6, min_fee_amount=60)
    assert wd.estimate_fee(provider, 500) == 60
    assert wd.estimate_fee(provider, 2000) == 120


def test_amount_limits():
    data = {"min_out": 500, "max_out": 79000}
    assert wd._amount_error(data, 400, 5000) == "wd_err_min"
    assert wd._amount_error(data, 80000, 100000) == "wd_err_max"
    assert wd._amount_error(data, 3000, 2000) == "wd_err_balance"
    assert wd._amount_error(data, 2000, 2000) is None


def test_phone_normalization():
    assert wd.normalize_phone("8 (919) 123-45-22") == "+79191234522"
    assert wd.normalize_phone("9191234522") == "+79191234522"
    assert wd.normalize_phone("12345") is None


# ----------------------------------------------------------------------
# Путь в Telegram (FSM на моках)
# ----------------------------------------------------------------------

class FakeState:
    def __init__(self):
        self.state, self.data = None, {}

    async def clear(self):
        self.state, self.data = None, {}

    async def set_state(self, value):
        self.state = value

    async def get_state(self):
        return self.state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)


class FakeMessage:
    def __init__(self, text=None):
        self.text = text
        self.edits, self.sent = [], []

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append((text, reply_markup))

    async def answer(self, text, reply_markup=None, **_):
        self.sent.append((text, reply_markup))


class FakeQuery:
    def __init__(self, data, message=None):
        self.data, self.message, self.answers = data, message or FakeMessage(), []
        self.from_user = SimpleNamespace(id=1)

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(wd, "REMEMBER_FILE", str(tmp_path / "withdrawal.json"))
    monkeypatch.setattr(wd, "STORAGE_DIR", str(tmp_path))
    fixer = make_fixer()
    fixer.account.profile.balance.withdrawable = 3000
    fixer.account.get_balance = lambda: None
    fixer.account.get_withdrawal_providers = lambda: [
        SimpleNamespace(id="LOCAL", name="Баланс", fee=0, min_fee_amount=None, min_out=500, max_out=100000, saved_account=None),
        SimpleNamespace(id="SBP", name="СБП", fee=6, min_fee_amount=60, min_out=500, max_out=79000, saved_account="+79191234522"),
        SimpleNamespace(id="YMONEY", name="ЮMoney", fee=6, min_fee_amount=60, min_out=500, max_out=79000, saved_account=None),
    ]
    fixer.account.get_sbp_banks = lambda: [SimpleNamespace(id="100000000111", name="Сбербанк"),
                                           SimpleNamespace(id="100000000004", name="Т-Банк")]
    calls = []
    fixer.account.request_withdrawal = lambda *a: calls.append(a) or SimpleNamespace(id="tx-9", status=SimpleNamespace(name="PENDING"))
    return fixer, FakeState(), calls


def run(coro):
    return asyncio.run(coro)


def test_full_sbp_flow_requires_confirmation(setup):
    fixer, state, calls = setup
    q = FakeQuery("wd")
    run(wd.cb_main(q, fixer, state))
    text, markup = q.message.edits[-1]
    assert "3 000 ₽" in text and "ЮMoney" in text and "только на сайте" in text
    buttons = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "wd:m:SBP" in buttons and "wd:m:YMONEY" not in buttons and "wd:m:LOCAL" not in buttons

    run(wd.cb_method(FakeQuery("wd:m:SBP", q.message), fixer, state))
    run(wd.cb_bank(FakeQuery("wd:b:100000000111", q.message), fixer, state))
    assert state.state == wd.WithdrawStates.amount
    run(wd.msg_amount(FakeMessage("2000"), fixer, state))
    assert calls == []  # до подтверждения — ничего не отправлено

    run(wd.cb_go(FakeQuery("wd:go", q.message), fixer, state))
    assert calls == [("SBP", "+79191234522", 2000, "100000000111")]
    assert "Заявка на вывод создана" in q.message.edits[-1][0]

    # Повторное нажатие «Вывести» не создаёт вторую заявку.
    again = FakeQuery("wd:go", q.message)
    run(wd.cb_go(again, fixer, state))
    assert len(calls) == 1 and again.answers[0][1] is True


def test_remembered_choice_skips_to_amount(setup):
    fixer, state, calls = setup
    wd.save_remembered({"provider": "SBP", "account": "+79191234522", "bank_id": "100000000111", "bank_name": "Сбербанк"})
    remembered = wd.load_remembered()
    assert "account" not in remembered  # телефон не хранится
    q = FakeQuery("wd:repeat")
    run(wd.cb_repeat(q, fixer, state))
    assert state.state == wd.WithdrawStates.amount
    assert "Сбербанк" in q.message.edits[-1][0]


def test_amount_over_balance_rejected(setup):
    fixer, state, calls = setup
    run(wd.cb_method(FakeQuery("wd:m:SBP"), fixer, state))
    run(wd.cb_bank(FakeQuery("wd:b:100000000111"), fixer, state))
    msg = FakeMessage("5000")
    run(wd.msg_amount(msg, fixer, state))
    assert "Больше, чем доступно" in msg.sent[-1][0]
    assert calls == []


def test_offline_alert(setup):
    fixer, state, calls = setup
    fixer.account = None
    q = FakeQuery("wd")
    run(wd.cb_main(q, fixer, state))
    assert q.answers[0][1] is True and q.message.edits == []
