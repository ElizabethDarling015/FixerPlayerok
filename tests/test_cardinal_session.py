"""Тесты замены токена Playerok из TG (`cardinal/tg/handlers/session.py`) и уведомления о сессии."""
import tomllib
from types import SimpleNamespace

from playerokapi.account import Account
from playerokapi.common.exceptions import UnauthorizedError

from cardinal.tg.handlers.session import cmd_token, is_session_reply, on_session_reply
from cardinal.tg.notifications import Notifier

from cardinal_helpers import FakeTgBot, make_cardinal


class FakeTgMessage:
    """Минимальный фейк aiogram-сообщения: записывает ответы `answer()`."""

    def __init__(self, text="", chat_id=1, reply_to_message_id=None):
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)
        self.reply_to_message = (SimpleNamespace(message_id=reply_to_message_id)
                                 if reply_to_message_id is not None else None)
        self.answers: list[str] = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeWs:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def make_session_cardinal(tmp_path, monkeypatch):
    """Cardinal-фейк с настоящим Account (без сети) и конфигом в tmp_path."""
    monkeypatch.chdir(tmp_path)
    cardinal = make_cardinal()
    account = Account(cookies="token=old-token; __ddg5_=guard")
    cardinal.account = account
    cardinal.runner = SimpleNamespace(_ws=FakeWs())
    return cardinal, account


async def test_token_command_success_saves_config(tmp_path, monkeypatch):
    cardinal, account = make_session_cardinal(tmp_path, monkeypatch)
    account.username = "seller"
    account.get = lambda: account  # проверка авторизации успешна

    message = FakeTgMessage()
    await cmd_token(message, SimpleNamespace(args="eyJ-new-token"), cardinal)

    assert account.cookies == {"token": "eyJ-new-token"}
    assert cardinal.settings.playerok.cookies == "token=eyJ-new-token"
    # Cookies сохранены в configs/main.toml (секция [playerok]).
    with open(tmp_path / "configs" / "main.toml", "rb") as f:
        saved = tomllib.load(f)
    assert saved["playerok"]["cookies"] == "token=eyJ-new-token"
    # Текущее WS-соединение Runner закрыто — оно переподключится с новыми cookies.
    assert cardinal.runner._ws.closed
    assert message.answers and "seller" in message.answers[-1]


async def test_token_command_failure_restores_old_cookies(tmp_path, monkeypatch):
    cardinal, account = make_session_cardinal(tmp_path, monkeypatch)
    old_settings_cookies = cardinal.settings.playerok.cookies

    def failing_get():
        raise UnauthorizedError("HTTP 401")

    account.get = failing_get

    message = FakeTgMessage()
    await cmd_token(message, SimpleNamespace(args="eyJ-bad-token"), cardinal)

    # Старые cookies возвращены, конфиг не создан, настройки не тронуты.
    assert account.cookies == {"token": "old-token", "__ddg5_": "guard"}
    assert cardinal.settings.playerok.cookies == old_settings_cookies
    assert not (tmp_path / "configs").exists()
    assert not cardinal.runner._ws.closed
    assert message.answers and "❌" in message.answers[-1]


async def test_token_command_without_args_shows_usage(tmp_path, monkeypatch):
    cardinal, account = make_session_cardinal(tmp_path, monkeypatch)
    message = FakeTgMessage()
    await cmd_token(message, SimpleNamespace(args=None), cardinal)
    assert message.answers == [cardinal.l10n("session_token_usage")]
    assert account.cookies == {"token": "old-token", "__ddg5_": "guard"}


async def test_reply_on_session_notification_applies_token(tmp_path, monkeypatch):
    cardinal, account = make_session_cardinal(tmp_path, monkeypatch)
    account.username = "seller"
    account.get = lambda: account

    message = FakeTgMessage(text="token=new-token; __ddg5_=fresh", chat_id=7, reply_to_message_id=42)
    await on_session_reply(message, cardinal)

    assert account.cookies == {"token": "new-token", "__ddg5_": "fresh"}
    assert cardinal.settings.playerok.cookies == "token=new-token; __ddg5_=fresh"


def test_is_session_reply_filter():
    notifier = SimpleNamespace(session_expired_messages={(7, 42)})
    assert is_session_reply(FakeTgMessage(chat_id=7, reply_to_message_id=42), notifier)
    # Reply на другое сообщение или не-reply — пропускаются дальше (к роутеру replies).
    assert not is_session_reply(FakeTgMessage(chat_id=7, reply_to_message_id=41), notifier)
    assert not is_session_reply(FakeTgMessage(chat_id=8, reply_to_message_id=42), notifier)
    assert not is_session_reply(FakeTgMessage(chat_id=7), notifier)


async def test_notify_session_expired_remembers_messages():
    cardinal = make_cardinal()
    bot = FakeTgBot()
    notifier = Notifier(cardinal, bot, SimpleNamespace(all_ids={7}))

    await notifier.notify_session_expired("HTTP 401")

    assert len(bot.sent) == 1
    assert "HTTP 401" in bot.sent[0][1]
    # Сообщение запомнено — reply на него распознается хендлером сессии.
    assert notifier.session_expired_messages == {(7, 1)}
