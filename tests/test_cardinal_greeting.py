"""Тесты модуля приветствия Cardinal (`cardinal.modules.greeting`): дедуп по SQLite, первичная разметка."""
from types import SimpleNamespace

from cardinal.modules.greeting import GreetingModule
from playerokapi.updater.events import NewMessageEvent

from cardinal_helpers import make_cardinal, make_chat, make_chat_message


def make_module(tmp_path, cardinal=None) -> tuple[GreetingModule, object]:
    cardinal = cardinal or make_cardinal()
    cardinal.settings.modules.greeting = True
    module = GreetingModule(cardinal, db_path=str(tmp_path / "greeting.sqlite3"))
    return module, cardinal


async def test_greets_new_chat_once(tmp_path):
    module, cardinal = make_module(tmp_path)
    cardinal.settings.greeting.text = "Привет, $username!"
    event = NewMessageEvent(None, make_chat("chat-1"), make_chat_message("здравствуйте", username="ivan"))

    await module.on_event(event)
    await module.on_event(event)  # второе сообщение — приветствия уже нет

    assert cardinal.account.sent_messages == [("chat-1", "Привет, ivan!")]


async def test_dedup_survives_restart(tmp_path):
    module, cardinal = make_module(tmp_path)
    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("хай")))
    assert len(cardinal.account.sent_messages) == 1

    # «Перезапуск»: новый экземпляр модуля с той же базой, но чистым счётчиком сообщений.
    module2, cardinal2 = make_module(tmp_path)
    await module2.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("хай снова")))
    assert cardinal2.account.sent_messages == []


async def test_own_messages_do_not_trigger_greeting(tmp_path):
    module, cardinal = make_module(tmp_path)
    own = make_chat_message("я продавец", user_id=cardinal.account.id)
    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), own))
    assert cardinal.account.sent_messages == []
    # Чат не должен быть помечен: настоящий покупатель ещё получит приветствие.
    assert not module.is_greeted("chat-1")


async def test_disabled_module_does_not_greet(tmp_path):
    module, cardinal = make_module(tmp_path)
    cardinal.settings.modules.greeting = False
    await module.on_event(NewMessageEvent(None, make_chat("chat-1"), make_chat_message("хай")))
    assert cardinal.account.sent_messages == []


async def test_on_start_seeds_existing_chats(tmp_path):
    module, cardinal = make_module(tmp_path)

    page = SimpleNamespace(
        chats=[SimpleNamespace(id="old-1"), SimpleNamespace(id="old-2")],
        page_info=SimpleNamespace(has_next_page=False, end_cursor=None),
    )
    cardinal.account.get_chats = lambda count=50, after_cursor=None: page

    await module.on_start()

    # Старые чаты размечены — приветствие им не отправляется.
    await module.on_event(NewMessageEvent(None, make_chat("old-1"), make_chat_message("привет")))
    assert cardinal.account.sent_messages == []
    # Новый чат — приветствуется.
    await module.on_event(NewMessageEvent(None, make_chat("new-1"), make_chat_message("привет")))
    assert len(cardinal.account.sent_messages) == 1


async def test_on_start_skips_seeding_if_db_not_empty(tmp_path):
    module, cardinal = make_module(tmp_path)
    module.mark_greeted("some-chat")

    def boom(**kwargs):
        raise AssertionError("get_chats не должен вызываться при непустой базе")

    cardinal.account.get_chats = boom
    await module.on_start()
