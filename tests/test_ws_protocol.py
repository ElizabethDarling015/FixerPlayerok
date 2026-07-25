"""Тесты WS-протокола graphql-transport-ws на фейковом сокете (без сети)."""
import json

from conftest import FakeAccount, drain_events

from playerokapi.updater import events, runner as runner_module
from playerokapi.updater.runner import Runner


class FakeWebSocket:
    """Фейковый сокет: отдаёт заготовленные кадры, запоминает отправленные."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.sent: list[dict] = []
        self.closed = False

    def send(self, data):
        self.sent.append(json.loads(data))

    def recv(self):
        if not self.frames:
            raise ConnectionError("connection closed")
        return self.frames.pop(0)

    def settimeout(self, timeout):
        pass

    def close(self):
        self.closed = True


def chat_updated_frame(chat_id="chat-1", message_id="msg-1", text="привет", deal=None):
    last_message = {"id": message_id, "text": text, "user": {"id": "user-2", "username": "buyer"}}
    if deal is not None:
        last_message["deal"] = deal
    return json.dumps({
        "id": "sub-1",
        "type": "next",
        "payload": {"data": {"chatUpdated": {
            "id": chat_id,
            "unreadMessagesCounter": 1,
            "lastMessage": last_message,
        }}},
    })


def run_ws_session(frames, account=None):
    account = account or FakeAccount()
    runner = Runner(account)
    fake_ws = FakeWebSocket(frames)
    original = runner_module.websocket.create_connection
    runner_module.websocket.create_connection = lambda *args, **kwargs: fake_ws
    try:
        runner._ws_connect_and_listen()
    finally:
        runner_module.websocket.create_connection = original
    return runner, fake_ws


def test_handshake_init_ack_subscribe():
    _, ws = run_ws_session([json.dumps({"type": "connection_ack"})])

    init_frame = ws.sent[0]
    assert init_frame["type"] == "connection_init"
    assert init_frame["payload"]["x-gql-op"] == "ws-subscription"
    assert "x-timezone-offset" in init_frame["payload"]

    subscribe_frames = [f for f in ws.sent if f["type"] == "subscribe"]
    operations = {f["payload"]["operationName"] for f in subscribe_frames}
    assert operations == {"chatUpdated", "chatMarkedAsRead", "itemUpdated", "itemCreated", "chatCreated"}
    by_name = {f["payload"]["operationName"]: f for f in subscribe_frames}
    assert by_name["chatUpdated"]["payload"]["variables"] == {
        "filter": {"userId": "user-1"}, "showForbiddenImage": True,
    }
    assert by_name["chatCreated"]["payload"]["variables"] == {"filter": {"userId": "user-1"}}
    assert by_name["itemUpdated"]["payload"]["variables"] == {
        "filter": {"userId": "user-1"}, "showForbiddenImage": True,
    }
    for frame in subscribe_frames:
        assert frame["id"]  # у каждой подписки свой id
    assert ws.closed


def test_custom_ws_subscriptions_subset():
    account = FakeAccount()
    runner = Runner(account, ws_subscriptions=("chatUpdated",))
    fake_ws = FakeWebSocket([json.dumps({"type": "connection_ack"})])
    original = runner_module.websocket.create_connection
    runner_module.websocket.create_connection = lambda *args, **kwargs: fake_ws
    try:
        runner._ws_connect_and_listen()
    finally:
        runner_module.websocket.create_connection = original
    ops = {f["payload"]["operationName"] for f in fake_ws.sent if f["type"] == "subscribe"}
    assert ops == {"chatUpdated"}


def test_item_updated_and_chat_created_events():
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        json.dumps({
            "type": "next",
            "payload": {"data": {"itemUpdated": {"id": "item-9", "name": "Лот", "status": "APPROVED"}}},
        }),
        json.dumps({
            "type": "next",
            "payload": {"data": {"chatCreated": {"id": "chat-new", "unreadMessagesCounter": 0}}},
        }),
    ])
    emitted = drain_events(runner)
    assert any(isinstance(e, events.ItemUpdatedEvent) for e in emitted)
    assert any(isinstance(e, events.ChatCreatedEvent) for e in emitted)
    assert any(isinstance(e, events.ChatInitializedEvent) for e in emitted)


def test_ping_answered_with_pong_during_handshake_and_after():
    _, ws = run_ws_session([
        json.dumps({"type": "ping"}),             # ping до ack
        json.dumps({"type": "connection_ack"}),
        json.dumps({"type": "ping"}),             # ping после подписки
    ])
    pongs = [f for f in ws.sent if f.get("type") == "pong"]
    assert len(pongs) == 2


def test_next_frame_produces_new_message_event():
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        chat_updated_frame(),
    ])
    emitted = drain_events(runner)
    # Неизвестный чат: ChatInitializedEvent + сообщение из last_message не потеряно.
    assert any(isinstance(e, events.ChatInitializedEvent) for e in emitted)
    assert any(isinstance(e, events.NewMessageEvent) for e in emitted)


def test_duplicate_last_message_not_emitted_twice():
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        chat_updated_frame(message_id="msg-1"),
        chat_updated_frame(message_id="msg-1"),  # тот же last_message.id — дубль
        chat_updated_frame(message_id="msg-2"),
    ])
    emitted = drain_events(runner)
    new_messages = [e for e in emitted if isinstance(e, events.NewMessageEvent)]
    assert [e.message.id for e in new_messages] == ["msg-1", "msg-2"]


def test_item_paid_marker_emits_event():
    deal = {"id": "deal-1", "status": "PAID", "direction": "OUT",
            "item": {"id": "item-1", "name": "Лот"}, "chat": {"id": "chat-1"}}
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        chat_updated_frame(text="{{ITEM_PAID}}", deal=deal),
    ])
    emitted = drain_events(runner)
    paid = [e for e in emitted if isinstance(e, events.ItemPaidEvent)]
    assert len(paid) == 1
    assert paid[0].deal.id == "deal-1"


def test_error_and_complete_frames_ignored():
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        json.dumps({"type": "error", "id": "sub-1", "payload": [{"message": "bad"}]}),
        json.dumps({"type": "complete", "id": "sub-1"}),
    ])
    assert drain_events(runner) == []


def test_chat_marked_as_read_updates_counter_without_events():
    runner, _ = run_ws_session([
        json.dumps({"type": "connection_ack"}),
        json.dumps({
            "type": "next",
            "payload": {"data": {"chatMarkedAsRead": {"id": "chat-1",
                                                        "unreadMessagesCounter": 0}}},
        }),
    ])
    assert drain_events(runner) == []
    assert runner._known_chats.get("chat-1") == 0


def test_no_ack_raises():
    import pytest

    account = FakeAccount()
    runner = Runner(account)
    fake_ws = FakeWebSocket([])  # сервер молчит — ack не приходит
    original = runner_module.websocket.create_connection
    runner_module.websocket.create_connection = lambda *args, **kwargs: fake_ws
    try:
        with pytest.raises(ConnectionError):
            runner._ws_connect_and_listen()
    finally:
        runner_module.websocket.create_connection = original
    assert fake_ws.closed
