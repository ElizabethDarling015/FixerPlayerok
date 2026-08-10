"""Регрессия: у специализированных событий сделки — собственные EventTypes, карта хуков полная."""
import pytest

from playerokapi.common.enums import EventTypes, Hooks
from playerokapi.updater import events
from playerokapi.updater.runner import _EVENT_HOOK_MAP


@pytest.mark.parametrize("event_cls, expected_type", [
    (events.DealStatusChangedEvent, EventTypes.DEAL_STATUS_CHANGED),
    (events.DealConfirmedEvent, EventTypes.DEAL_CONFIRMED),
    (events.DealConfirmedAutomaticallyEvent, EventTypes.DEAL_CONFIRMED_AUTOMATICALLY),
    (events.DealRolledBackEvent, EventTypes.DEAL_ROLLED_BACK),
    (events.ItemSentEvent, EventTypes.ITEM_SENT),
])
def test_deal_status_events_have_own_types(event_cls, expected_type):
    event = event_cls(runner=None, deal=None, previous_status="PAID", new_status="SENT")
    assert event.type is expected_type


@pytest.mark.parametrize("event_type, expected_hook", [
    (EventTypes.ITEM_PAID, Hooks.ITEM_PAID),
    (EventTypes.ITEM_SENT, Hooks.ITEM_SENT),
    (EventTypes.DEAL_CONFIRMED, Hooks.DEAL_CONFIRMED),
    (EventTypes.DEAL_CONFIRMED_AUTOMATICALLY, Hooks.DEAL_CONFIRMED_AUTOMATICALLY),
    (EventTypes.DEAL_ROLLED_BACK, Hooks.DEAL_ROLLED_BACK),
    (EventTypes.ITEM_RAISED, Hooks.ITEM_RAISED),
    (EventTypes.DEAL_HAS_PROBLEM, Hooks.DEAL_HAS_PROBLEM),
    (EventTypes.DEAL_PROBLEM_RESOLVED, Hooks.DEAL_PROBLEM_RESOLVED),
    (EventTypes.NEW_REVIEW, Hooks.NEW_REVIEW),
])
def test_event_hook_map_is_complete(event_type, expected_hook):
    assert _EVENT_HOOK_MAP.get(event_type) is expected_hook
