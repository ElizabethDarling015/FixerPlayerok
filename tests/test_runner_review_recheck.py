"""Тесты отложенного «дочита» отзывов в Runner: Playerok отдаёт свежий отзыв раньше, чем
достраивает связи с ним (сделку/чат/автора), поэтому неполный отзыв не превращается в
`NewReviewEvent` сразу, а перепроверяется на следующих циклах поллинга."""
from types import SimpleNamespace

import pytest

from conftest import FakeAccount, drain_events, make_page

from playerokapi.updater import events
from playerokapi.updater import runner as runner_module
from playerokapi.updater.runner import Runner


class FakeClock:
    """Подмена модуля `time` в runner: монотонные часы, которые двигает сам тест."""

    def __init__(self):
        self.value = 1000.0

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(runner_module, "time", fake)
    return fake


def make_review(review_id="rev-1", creator=None, deal=None):
    """Отзыв в том виде, в каком его отдаёт `parser.review` (deal всегда None)."""
    return SimpleNamespace(id=review_id, rating=5, creator=creator, deal=deal)


def full_review(review_id="rev-1", buyer="ivan"):
    """Полный отзыв: известен автор — по нему обработчик найдёт чат покупателя."""
    return make_review(review_id, creator=SimpleNamespace(id="buyer-1", username=buyer))


def empty_review(review_id="rev-1"):
    """Неполный отзыв: ни сделки с чатом, ни автора — писать покупателю некуда."""
    return make_review(review_id)


def set_reviews(account, reviews):
    account.get_my_reviews = lambda count=50, after_cursor=None: make_page(reviews, field="reviews")


def make_runner(account, reviews=()):
    """Runner с уже сделанным первым снимком отзывов (`reviews` — отзывы на момент старта)."""
    runner = Runner(account)
    set_reviews(account, list(reviews))
    runner._poll_reviews()
    drain_events(runner)
    return runner


def review_events(runner):
    return [e for e in drain_events(runner) if isinstance(e, events.NewReviewEvent)]


# ----------------------------------------------------------------------
# Первый снимок и полные отзывы — прежнее поведение
# ----------------------------------------------------------------------

def test_first_snapshot_emits_nothing_and_schedules_nothing(clock):
    account = FakeAccount()
    runner = Runner(account)
    # В первом снимке есть и полный, и неполный отзыв — событий быть не должно ни по одному,
    # и в очередь дочита старый неполный отзыв тоже попасть не должен.
    set_reviews(account, [full_review("rev-old"), empty_review("rev-empty")])
    runner._poll_reviews()

    assert drain_events(runner) == []
    assert runner._pending_reviews == {}
    assert runner._known_reviews == {"rev-old", "rev-empty"}


def test_complete_review_emitted_immediately(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [full_review("rev-1")])
    runner._poll_reviews()

    emitted = review_events(runner)
    assert len(emitted) == 1
    assert emitted[0].review.id == "rev-1"
    assert runner._pending_reviews == {}


def test_review_with_deal_chat_is_complete(clock):
    """Чат сделки — тоже полноценный путь до покупателя (на случай, если deal всё-таки заполнен)."""
    account = FakeAccount()
    runner = make_runner(account)

    review = make_review("rev-1", deal=SimpleNamespace(id="deal-1", chat=SimpleNamespace(id="chat-1")))
    set_reviews(account, [review])
    runner._poll_reviews()

    assert len(review_events(runner)) == 1


# ----------------------------------------------------------------------
# Неполный отзыв: откладывание и успешный дочит
# ----------------------------------------------------------------------

def test_incomplete_review_is_not_emitted_immediately(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()

    assert drain_events(runner) == []
    assert list(runner._pending_reviews) == ["rev-1"]
    assert runner._pending_reviews["rev-1"]["attempts"] == 0
    # Первая перепроверка — не раньше, чем через _REVIEW_RECHECK_DELAY.
    assert runner._pending_reviews["rev-1"]["next_at"] == pytest.approx(
        clock.value + runner_module._REVIEW_RECHECK_DELAY)


def test_pending_review_not_rechecked_before_delay(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    # Отзыв уже стал полным, но время перепроверки ещё не пришло — событие не отправляется.
    set_reviews(account, [full_review("rev-1")])
    clock.advance(runner_module._REVIEW_RECHECK_DELAY / 2)
    runner._poll_reviews()

    assert drain_events(runner) == []
    assert runner._pending_reviews["rev-1"]["attempts"] == 0


def test_recheck_emits_event_once_when_review_becomes_complete(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    # Прошло 30 секунд, Playerok достроил связи — отзыв дочитан.
    set_reviews(account, [full_review("rev-1")])
    clock.advance(runner_module._REVIEW_RECHECK_DELAY)
    runner._poll_reviews()

    emitted = review_events(runner)
    assert len(emitted) == 1
    assert emitted[0].review.creator.username == "ivan"
    assert runner._pending_reviews == {}

    # Дальнейшие циклы то же событие не повторяют.
    for _ in range(3):
        clock.advance(runner_module._REVIEW_RECHECK_DELAY)
        runner._poll_reviews()
    assert drain_events(runner) == []


def test_recheck_waits_across_several_cycles(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    # Три созревших перепроверки подряд — отзыв всё ещё неполный, событий нет.
    for expected_attempts in (1, 2, 3):
        clock.advance(runner_module._REVIEW_RECHECK_DELAY)
        runner._poll_reviews()
        assert drain_events(runner) == []
        assert runner._pending_reviews["rev-1"]["attempts"] == expected_attempts

    set_reviews(account, [full_review("rev-1")])
    clock.advance(runner_module._REVIEW_RECHECK_DELAY)
    runner._poll_reviews()
    assert len(review_events(runner)) == 1


# ----------------------------------------------------------------------
# Исчерпание попыток
# ----------------------------------------------------------------------

def test_attempts_exhausted_emits_incomplete_event_with_warning(clock, caplog):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    caplog.set_level("WARNING", logger="playerokapi.runner")
    for _ in range(runner_module._REVIEW_RECHECK_ATTEMPTS):
        clock.advance(runner_module._REVIEW_RECHECK_DELAY)
        runner._poll_reviews()

    emitted = review_events(runner)
    assert len(emitted) == 1
    assert emitted[0].review.id == "rev-1"
    assert emitted[0].review.creator is None  # событие ушло неполным — лучше, чем потерять отзыв
    assert runner._pending_reviews == {}
    assert any("не дочитался" in record.getMessage() for record in caplog.records)

    # Больше событий по этому отзыву не будет.
    clock.advance(runner_module._REVIEW_RECHECK_DELAY)
    runner._poll_reviews()
    assert drain_events(runner) == []


def test_review_disappeared_from_list_is_emitted_after_attempts(clock):
    """Отзыв пропал из выдачи — попытки всё равно тратятся, событие уходит по сохранённой копии."""
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    set_reviews(account, [])
    for _ in range(runner_module._REVIEW_RECHECK_ATTEMPTS):
        clock.advance(runner_module._REVIEW_RECHECK_DELAY)
        runner._poll_reviews()

    emitted = review_events(runner)
    assert len(emitted) == 1
    assert emitted[0].review.id == "rev-1"


# ----------------------------------------------------------------------
# Устойчивость: сбой опроса не тратит попытки и не считается успехом цикла
# ----------------------------------------------------------------------

def test_failed_poll_does_not_spend_attempts(clock):
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1")])
    runner._poll_reviews()
    drain_events(runner)

    def failing(count=50, after_cursor=None):
        raise RuntimeError("network down")

    account.get_my_reviews = failing
    clock.advance(runner_module._REVIEW_RECHECK_DELAY)
    runner._poll_reviews()

    assert runner._pending_reviews["rev-1"]["attempts"] == 0
    assert drain_events(runner) == []
    # Сбойный запрос помечает цикл неуспешным — вахдог сессии не должен считать опрос удачным.
    assert runner._poll_cycle_failed is True

    # После восстановления сети дочит продолжается с той же попытки.
    set_reviews(account, [full_review("rev-1")])
    runner._poll_reviews()
    assert len(review_events(runner)) == 1


def test_pending_reviews_are_independent(clock):
    """Два неполных отзыва дочитываются независимо друг от друга."""
    account = FakeAccount()
    runner = make_runner(account)

    set_reviews(account, [empty_review("rev-1"), empty_review("rev-2")])
    runner._poll_reviews()
    drain_events(runner)
    assert set(runner._pending_reviews) == {"rev-1", "rev-2"}

    set_reviews(account, [full_review("rev-1"), empty_review("rev-2")])
    clock.advance(runner_module._REVIEW_RECHECK_DELAY)
    runner._poll_reviews()

    emitted = review_events(runner)
    assert [e.review.id for e in emitted] == ["rev-1"]
    assert set(runner._pending_reviews) == {"rev-2"}
