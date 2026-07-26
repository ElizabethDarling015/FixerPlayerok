"""Тесты `Account.update_cookies`: полная строка cookies, голый JWT, словарь."""
from playerokapi.account import Account


def make_account():
    return Account(cookies="token=old-token; __ddg5_=guard")


def test_init_parses_cookies_string():
    account = make_account()
    assert account.cookies == {"token": "old-token", "__ddg5_": "guard"}


def test_init_accepts_bare_jwt():
    # Голое значение токена (как в мастере настройки) оборачивается в token=<...>.
    account = Account(cookies="eyJ-bare-token")
    assert account.cookies == {"token": "eyJ-bare-token"}


def test_update_cookies_full_string():
    account = make_account()
    account.update_cookies("token=new-token; __ddg5_=new-guard")
    assert account.cookies == {"token": "new-token", "__ddg5_": "new-guard"}
    assert "token=new-token" in account._cookie_header()


def test_update_cookies_bare_jwt():
    account = make_account()
    account.update_cookies("  eyJ-new-token  ")
    assert account.cookies == {"token": "eyJ-new-token"}


def test_update_cookies_dict():
    account = make_account()
    account.update_cookies({"token": "dict-token"})
    assert account.cookies == {"token": "dict-token"}
