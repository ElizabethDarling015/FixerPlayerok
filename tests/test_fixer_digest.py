"""Тесты модуля «Сводка дня»: учёт продаж в SQLite, текст сводки, расписание."""
from types import SimpleNamespace

from fixer.modules.digest import DigestModule
from playerokapi.updater.events import ItemPaidEvent

from fixer_helpers import make_fixer, make_chat


def make_module(tmp_path, fixer=None) -> tuple[DigestModule, object]:
    fixer = fixer or make_fixer()
    module = DigestModule(fixer, db_path=str(tmp_path / "stats.sqlite3"))
    return module, fixer


def make_paid_event(price=100):
    deal = SimpleNamespace(
        id="deal-1",
        item=SimpleNamespace(name="Лот", price=price),
        user=SimpleNamespace(username="buyer"),
    )
    return ItemPaidEvent(None, make_chat(), None, deal)


def test_record_sale_accumulates(tmp_path):
    module, _ = make_module(tmp_path)
    module.record_sale(100)
    module.record_sale(50.5)
    count, revenue = module.get_day_stats()
    assert count == 2
    assert revenue == 150.5


def test_stats_survive_restart(tmp_path):
    module, _ = make_module(tmp_path)
    module.record_sale(100)

    module2 = DigestModule(make_fixer(), db_path=str(tmp_path / "stats.sqlite3"))
    count, revenue = module2.get_day_stats()
    assert (count, revenue) == (1, 100.0)


async def test_item_paid_event_recorded(tmp_path):
    module, _ = make_module(tmp_path)
    await module.on_event(make_paid_event(price=250))
    assert module.get_day_stats() == (1, 250.0)


async def test_sale_without_price_counts_as_zero(tmp_path):
    module, _ = make_module(tmp_path)
    await module.on_event(make_paid_event(price=None))
    assert module.get_day_stats() == (1, 0.0)


def test_build_digest_contents(tmp_path):
    module, fixer = make_module(tmp_path)
    module.record_sale(100)
    module.record_sale(200)
    fixer.autodelivery_manager = SimpleNamespace(
        stock_paths={"Лот А": "a.txt", "Лот Б": "b.txt"},
        get_stock_size=lambda name: 7,
    )
    text = module.build_digest()
    assert "2" in text          # продаж
    assert "300" in text        # выручка
    assert "100" in text        # баланс фейкового аккаунта
    assert "Лот А" in text and "Лот Б" in text and "7" in text


def test_build_digest_without_stocks(tmp_path):
    module, fixer = make_module(tmp_path)
    text = module.build_digest()
    assert fixer.l10n("digest_no_stocks") in text


def test_seconds_until_next_run_in_range(tmp_path):
    module, _ = make_module(tmp_path)
    seconds = module._seconds_until_next_run()
    assert 0 < seconds <= 24 * 60 * 60


def test_timezone_affects_now(tmp_path):
    """`[digest] timezone` задаёт пояс продавца — «день продаж» считается по нему."""
    module, fixer = make_module(tmp_path)
    assert module._now().tzinfo is None  # без настройки — локальное время сервера

    fixer.settings.digest.timezone = "Asia/Yekaterinburg"
    now = module._now()
    assert str(now.tzinfo) == "Asia/Yekaterinburg"
    assert module._today() == now.date().isoformat()


def test_next_run_follows_time_setting(tmp_path):
    """Смена `[digest] time` меняет ближайший срок отправки (без рестарта)."""
    module, fixer = make_module(tmp_path)
    fixer.settings.digest.time = "06:00"
    first = module._next_run_at()
    fixer.settings.digest.time = "18:30"
    second = module._next_run_at()
    assert (first.hour, first.minute) == (6, 0)
    assert (second.hour, second.minute) == (18, 30)
