"""Тесты авторизации TG-панели Cardinal (`cardinal.tg.auth`): реестр админов и middleware."""
import datetime

from aiogram.types import Chat as TgChat
from aiogram.types import Message as TgMessage
from aiogram.types import User as TgUser

from cardinal.tg.auth import AuthMiddleware, TgAdmins

from cardinal_helpers import make_cardinal


class FakeAiogramBot:
    """Фейк, которому aiogram-шорткаты (`message.answer(...)`) отдают методы на выполнение."""

    def __init__(self):
        self.calls = []

    async def __call__(self, method, *args, **kwargs):
        self.calls.append(method)
        return method


def make_tg_message(user_id: int, text: str, bot: FakeAiogramBot) -> TgMessage:
    message = TgMessage(
        message_id=1,
        date=datetime.datetime.now(datetime.timezone.utc),
        chat=TgChat(id=user_id, type="private"),
        from_user=TgUser(id=user_id, is_bot=False, first_name="U"),
        text=text,
    )
    return message.as_(bot)


# ----------------------------------------------------------------------
# TgAdmins
# ----------------------------------------------------------------------

def test_admins_from_config(tmp_path):
    admins = TgAdmins([10, 20], storage_file=str(tmp_path / "admins.json"))
    assert admins.is_admin(10) and admins.is_admin(20)
    assert not admins.is_admin(30)


def test_bind_persists_across_restart(tmp_path):
    storage = str(tmp_path / "admins.json")
    admins = TgAdmins([], storage_file=storage)
    admins.bind(555)
    assert admins.is_admin(555)

    reloaded = TgAdmins([], storage_file=storage)
    assert reloaded.is_admin(555)


def test_secret_code_is_random(tmp_path):
    a = TgAdmins([], storage_file=str(tmp_path / "a.json"))
    b = TgAdmins([], storage_file=str(tmp_path / "b.json"))
    assert a.secret_code != b.secret_code


# ----------------------------------------------------------------------
# AuthMiddleware
# ----------------------------------------------------------------------

async def test_admin_passes_through(tmp_path):
    cardinal = make_cardinal()
    admins = TgAdmins([10], storage_file=str(tmp_path / "admins.json"))
    middleware = AuthMiddleware(cardinal, admins)
    bot = FakeAiogramBot()

    handled = []

    async def handler(event, data):
        handled.append(event)
        return "ok"

    message = make_tg_message(10, "/menu", bot)
    result = await middleware(handler, message, {"event_from_user": message.from_user})
    assert result == "ok" and len(handled) == 1
    assert bot.calls == []  # никаких «вы не авторизованы»


async def test_stranger_is_rejected(tmp_path):
    cardinal = make_cardinal()
    admins = TgAdmins([10], storage_file=str(tmp_path / "admins.json"))
    middleware = AuthMiddleware(cardinal, admins)
    bot = FakeAiogramBot()

    async def handler(event, data):
        raise AssertionError("хендлер не должен вызываться для чужака")

    message = make_tg_message(99, "/menu", bot)
    result = await middleware(handler, message, {"event_from_user": message.from_user})
    assert result is None
    assert len(bot.calls) == 1  # отправлена подсказка про код


async def test_stranger_binds_with_secret_code(tmp_path):
    cardinal = make_cardinal()
    admins = TgAdmins([], storage_file=str(tmp_path / "admins.json"))
    middleware = AuthMiddleware(cardinal, admins)
    bot = FakeAiogramBot()

    async def handler(event, data):
        return "ok"

    message = make_tg_message(77, admins.secret_code, bot)
    await middleware(handler, message, {"event_from_user": message.from_user})

    assert admins.is_admin(77)
    # Следующее сообщение уже проходит к хендлерам.
    message2 = make_tg_message(77, "/menu", bot)
    result = await middleware(handler, message2, {"event_from_user": message2.from_user})
    assert result == "ok"
