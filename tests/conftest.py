"""Общие помощники для тестов (все тесты — на моках, без сети и реальных cookies)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

# Тесты запускаются из корня репозитория; страхуемся, если пакет не установлен через pip.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeAccount:
    """Минимальный фейковый Account для Runner-тестов (без сети)."""

    user_agent = "UA-test"

    def __init__(self):
        self.id = "user-1"
        self.username = "seller"
        self._runner = None
        self.sent_messages: list[tuple[str, str]] = []

    def _cookie_header(self):
        return "token=test"

    def _note_chat(self, chat):
        pass

    def get(self):
        return self

    def get_chats(self, count=50, after_cursor=None):
        return None

    def get_deals(self, count=50, after_cursor=None):
        return None

    def get_my_reviews(self, count=50, after_cursor=None):
        return None

    def send_message(self, chat_id, text=None, **kwargs):
        self.sent_messages.append((chat_id, text))

    def _resolve_items(self, raw_item):
        if not raw_item:
            return None
        return SimpleNamespace(id=raw_item.get("id"), name=raw_item.get("name"),
                               status=raw_item.get("status"))


def make_deal(deal_id="deal-1", status="PAID", direction=None, item_name="Лот",
              chat_id="chat-1", has_problem=False):
    """Собирает лёгкий объект сделки с атрибутами, которые читает Runner."""
    return SimpleNamespace(
        id=deal_id,
        raw_status=SimpleNamespace(name=status) if status else None,
        has_problem=has_problem,
        direction=direction,
        item=SimpleNamespace(name=item_name),
        chat=SimpleNamespace(id=chat_id),
    )


def make_page(items, has_next_page=False, end_cursor=None, field="deals"):
    """Собирает объект-страницу списка (как ItemDealList/ReviewList/ChatList)."""
    page = SimpleNamespace(
        page_info=SimpleNamespace(has_next_page=has_next_page, end_cursor=end_cursor),
    )
    setattr(page, field, items)
    return page


def drain_events(runner) -> list:
    """Достаёт все события, накопившиеся в очереди Runner."""
    events_list = []
    while not runner._event_queue.empty():
        events_list.append(runner._event_queue.get_nowait())
    return events_list
