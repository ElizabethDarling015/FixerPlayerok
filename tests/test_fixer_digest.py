"""Сводка дня и статистика: цифры из истории транзакций Playerok (на моках), расписание."""
import asyncio
import datetime
from types import SimpleNamespace

from fixer.modules.digest import DigestModule
from fixer.sales_stats import SalesHistory, fetch_sales, sum_totals, totals_by_day
from fixer.tg.handlers.stats import build_stats_text
from playerokapi import parser

from fixer_helpers import make_fixer

TZ = datetime.timezone(datetime.timedelta(hours=5))  # Екатеринбург


def iso(days_ago: int, hour: int = 12) -> str:
    """ISO-время в UTC для «дней назад» (по екатеринбургскому времени)."""
    local = datetime.datetime.now(TZ).replace(hour=hour, minute=0, second=0, microsecond=0)
    return (local - datetime.timedelta(days=days_ago)).astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def tx(value, fee, status, created):
    return {"id": f"t-{value}-{created}", "operation": "SELL", "direction": "IN",
            "value": value, "fee": fee, "status": status, "createdAt": created}


def page(nodes, has_next=False, cursor=None):
    return parser.transaction_list({"edges": [{"node": n} for n in nodes],
                                    "pageInfo": {"hasNextPage": has_next, "endCursor": cursor}})


class FakeAccount:
    """Две страницы транзакций SELL: сегодня, вчера, неделю назад, 40 дней назад."""

    def __init__(self):
        self.calls = []
        self.pages = {
            None: page([tx(297, 33, "PENDING", iso(0)), tx(297, 33, "ROLLED_BACK", iso(0, 10)),
                        tx(287.1, 31.9, "PROCESSING", iso(1))], has_next=True, cursor="c2"),
            "c2": page([tx(239.2, 59.8, "CONFIRMED", iso(6)), tx(100, 10, "CONFIRMED", iso(40))],
                       has_next=True, cursor="c3"),
            "c3": page([tx(1, 1, "CONFIRMED", iso(50))]),
        }

    def get_transactions(self, count, cursor, flt):
        self.calls.append((cursor, flt))
        return self.pages[cursor]


def test_fetch_sales_stops_at_period_and_filters_sells():
    account = FakeAccount()
    since = datetime.datetime.now(TZ).date() - datetime.timedelta(days=29)
    sales = fetch_sales(account, since, TZ)
    assert [c[1] for c in account.calls] == [{"operation": ["SELL"]}] * 2  # дальше 30 дней не листаем
    assert len(sales) == 4


def test_totals_exclude_refunds_and_split_gross_net():
    today = datetime.datetime.now(TZ).date()
    days = totals_by_day(fetch_sales(FakeAccount(), today - datetime.timedelta(days=29), TZ))
    t = days[today]
    assert (t.count, t.gross, t.net, t.refunds) == (1, 330.0, 297.0, 1)
    week = sum_totals(days, today - datetime.timedelta(days=6))
    assert week.count == 3 and round(week.gross) == 330 + 319 + 299


def test_history_is_cached():
    account = FakeAccount()
    history = SalesHistory(ttl=300, clock=lambda: 0.0)
    since = datetime.datetime.now(TZ).date() - datetime.timedelta(days=29)
    history.get(account, since, TZ)
    calls = len(account.calls)
    history.get(account, since, TZ)
    history.get(account, since + datetime.timedelta(days=23), TZ)  # более короткий период — из того же кэша
    assert len(account.calls) == calls


def make_module(fixer=None):
    fixer = fixer or make_fixer()
    fixer.settings.digest.timezone = "Asia/Yekaterinburg"
    fake = FakeAccount()
    fixer.account.get_transactions = fake.get_transactions
    return DigestModule(fixer), fixer


def test_digest_shows_today_from_playerok_not_zero():
    module, fixer = make_module()
    text = asyncio.run(module.build_digest())
    assert "Продаж: <b>1</b>" in text
    assert "330 ₽" in text and "на руки 297 ₽" in text
    assert "Возвратов: <b>1</b>" in text
    assert "Остатки складов" not in text  # склады авто-выдачи не настроены — блока нет


def test_stats_text():
    module, fixer = make_module()
    days, today = asyncio.run(module.get_days(30))
    text = build_stats_text(fixer.l10n, days, today)
    assert today.strftime("%d.%m") in text and "↩️ 1" in text
    assert "За 7 дней: <b>3</b> шт." in text
    assert "Возвратов за 30 дней: <b>1</b>" in text


def test_timezone_affects_now():
    """`[digest] timezone` задаёт пояс продавца — «день продаж» считается по нему."""
    module, fixer = make_module()
    fixer.settings.digest.timezone = None
    assert module._now().tzinfo is None  # без настройки — локальное время сервера
    fixer.settings.digest.timezone = "Asia/Yekaterinburg"
    assert str(module._now().tzinfo) == "Asia/Yekaterinburg"


def test_seconds_until_next_run_in_range():
    module, _ = make_module()
    assert 0 < module._seconds_until_next_run() <= 24 * 60 * 60


def test_next_run_follows_time_setting():
    """Смена `[digest] time` меняет ближайший срок отправки (без рестарта)."""
    module, fixer = make_module()
    fixer.settings.digest.time = "06:00"
    first = module._next_run_at()
    fixer.settings.digest.time = "18:30"
    second = module._next_run_at()
    assert (first.hour, first.minute) == (6, 0)
    assert (second.hour, second.minute) == (18, 30)
