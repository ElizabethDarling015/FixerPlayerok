"""Тесты `StatsStore` (счётчики «что бот сделал сам») и записи из `Cardinal._consume_events`."""
from __future__ import annotations

import asyncio
import datetime
import threading
from types import SimpleNamespace

from cardinal.core import Cardinal
from cardinal.stats_store import (
    ACTION_AUTORESPONSE,
    ACTION_DELIVERY,
    ACTION_GREETING,
    ACTION_RAISE,
    StatsStore,
)
from playerokapi.updater.events import ItemPaidEvent, ItemRaisedEvent

from cardinal_helpers import make_settings


def day_ago(days: int) -> str:
    """ISO-день `days` дней назад (0 — сегодня); дни передаём явно, чтобы не зависеть от даты."""
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat()


# ----------------------------------------------------------------------
# StatsStore
# ----------------------------------------------------------------------

def test_record_totals_and_periods(tmp_path):
    store = StatsStore(str(tmp_path / "stats.sqlite"))
    store.record(ACTION_DELIVERY, day=day_ago(0))
    store.record(ACTION_DELIVERY, day=day_ago(0))
    store.record(ACTION_DELIVERY, day=day_ago(3))
    store.record(ACTION_DELIVERY, day=day_ago(30))
    store.record(ACTION_RAISE, day=day_ago(0))

    assert store.totals(ACTION_DELIVERY) == 4
    assert store.for_period(ACTION_DELIVERY, 1) == 2  # только сегодня
    assert store.for_period(ACTION_DELIVERY, 7) == 3  # сегодня + 3 дня назад
    # Действия не смешиваются между собой.
    assert store.totals(ACTION_RAISE) == 1
    assert store.totals(ACTION_AUTORESPONSE) == 0


def test_record_defaults_to_today(tmp_path):
    store = StatsStore(str(tmp_path / "stats.sqlite"))
    store.record(ACTION_GREETING)
    assert store.for_period(ACTION_GREETING, 1) == 1
    assert store.totals(ACTION_GREETING) == 1


def test_counters_survive_restart(tmp_path):
    store = StatsStore(str(tmp_path / "stats.sqlite"))
    store.record(ACTION_RAISE, day=day_ago(1))
    store.close()

    reopened = StatsStore(str(tmp_path / "stats.sqlite"))
    assert reopened.totals(ACTION_RAISE) == 1
    assert reopened.for_period(ACTION_RAISE, 7) == 1


def test_concurrent_records_from_threads(tmp_path):
    store = StatsStore(str(tmp_path / "stats.sqlite"))
    day = day_ago(0)

    def worker():
        for _ in range(25):
            store.record(ACTION_RAISE, day=day)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert store.totals(ACTION_RAISE) == 8 * 25


# ----------------------------------------------------------------------
# Запись из Cardinal
# ----------------------------------------------------------------------

def make_core(tmp_path, monkeypatch, ledger_state="sent") -> Cardinal:
    # chdir в tmp_path: StatsStore по умолчанию создаёт storage/stats.sqlite в рабочей папке.
    monkeypatch.chdir(tmp_path)
    cardinal = Cardinal(make_settings())
    cardinal.autodelivery_manager = SimpleNamespace(
        ledger=SimpleNamespace(get_state=lambda deal_id: ledger_state))
    return cardinal


def make_raised_event():
    return ItemRaisedEvent(None, SimpleNamespace(item_name="Лот", spent=10))


def make_paid_event(deal_id="deal-1"):
    deal = SimpleNamespace(id=deal_id, item=SimpleNamespace(name="Лот", price=100),
                           user=SimpleNamespace(username="buyer"))
    return ItemPaidEvent(None, SimpleNamespace(id="chat-1"), None, deal)


def test_record_bot_action_counts_raise_and_confirmed_delivery(tmp_path, monkeypatch):
    cardinal = make_core(tmp_path, monkeypatch)
    cardinal._record_bot_action(make_raised_event())
    cardinal._record_bot_action(make_paid_event())
    assert cardinal.stats.totals(ACTION_RAISE) == 1
    assert cardinal.stats.totals(ACTION_DELIVERY) == 1


def test_unconfirmed_delivery_not_counted(tmp_path, monkeypatch):
    """Оплата без «sent» в журнале выдач — бот ничего не выдавал, счётчик не растёт."""
    cardinal = make_core(tmp_path, monkeypatch, ledger_state="seen_paid")
    cardinal._record_bot_action(make_paid_event())
    assert cardinal.stats.totals(ACTION_DELIVERY) == 0


async def test_consume_events_records_and_survives_stats_failure(tmp_path, monkeypatch):
    cardinal = make_core(tmp_path, monkeypatch)
    cardinal.event_queue = asyncio.Queue()

    seen = []

    class Probe:
        name = "probe"

        async def on_event(self, event):
            seen.append(event)

    cardinal.modules = [Probe()]

    await cardinal.event_queue.put(make_raised_event())
    await cardinal.event_queue.put(make_paid_event())
    task = asyncio.get_running_loop().create_task(cardinal._consume_events())
    for _ in range(100):
        if len(seen) >= 2:
            break
        await asyncio.sleep(0.01)

    # Сломанная статистика (закрытая база) не должна ломать раздачу событий модулям.
    cardinal.stats.close()
    await cardinal.event_queue.put(make_raised_event())
    for _ in range(100):
        if len(seen) >= 3:
            break
        await asyncio.sleep(0.01)
    task.cancel()

    assert len(seen) == 3
    reopened = StatsStore()  # тот же storage/stats.sqlite внутри tmp_path (см. chdir)
    assert reopened.totals(ACTION_RAISE) == 1  # третье событие пришлось на закрытую базу
    assert reopened.totals(ACTION_DELIVERY) == 1
