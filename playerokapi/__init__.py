"""
`playerokapi` — неофициальная библиотека для работы с https://playerok.com по авторизации через cookie.

Быстрый старт:

    from playerokapi.account import Account

    account = Account(cookies="token=...; __ddg5_=...").get()
    print(account.username, account.profile.balance.value)

См. README.md в корне репозитория для подробностей и примеры в папке `examples/`.
"""

__version__ = "0.1.0"
