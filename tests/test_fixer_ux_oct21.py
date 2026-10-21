"""Вывод средств (последние выводы), «До завтра» (свернуть старое), картинки покупателя."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace as N

import pytest

from fixer.tg.handlers import withdrawal as wd
from fixer.tg.notifications import Notifier, message_image_urls
from fixer_helpers import FakeTgBot, make_fixer
from playerokapi.common.enums import ChatTypes
from playerokapi.updater.events import NewMessageEvent


# ----------------------------------------------------------------------
# Вывод средств
# ----------------------------------------------------------------------

PROVIDERS = {"SBP": N(id="SBP", name="СБП", fee=6, min_fee_amount=60, min_out=500, max_out=79000,
                      saved_account=None)}


def tx(day, value=2000, status="CONFIRMED"):
    return N(provider_id="SBP", provider=None, status=N(name=status), value=value,
             created_at=f"2026-10-{day:02d}T06:58:00.000Z")


def test_history_between_available_and_methods_without_blank_lines():
    from zoneinfo import ZoneInfo
    l10n = make_fixer().l10n
    text, _ = wd.build_main_screen(l10n, PROVIDERS, 4520, None, [tx(21, status="PENDING"), tx(19, 3100)],
                                   ZoneInfo("Asia/Yekaterinburg"))
    lines = text.splitlines()
    assert "" not in lines
    sep = wd.SEPARATOR
    assert lines[:9] == [
        "💳 <b>Вывод средств</b>",
        "💰 Доступно к выводу: <b>4 520 ₽</b>",
        sep,
        "💸 <b>-2 000 ₽</b> · СБП",
        "🕒 21.10.2026, 11:58 · ⏳ В очереди",
        sep,
        "💸 <b>-3 100 ₽</b> · СБП",
        "🕒 19.10.2026, 11:58 · ✅ Проведена",
        sep,
    ]
    assert lines[9].startswith("<b>Способы</b>")


def test_history_cut_to_message_limit_and_methods_kept():
    l10n = make_fixer().l10n
    text, _ = wd.build_main_screen(l10n, PROVIDERS, 100, None, [tx(1)] * 500)
    assert len(text) <= wd.MESSAGE_LIMIT
    assert text.count("💸") > 30 and "<b>СБП</b>" in text


def test_no_history_still_has_separator_before_methods():
    text, _ = wd.build_main_screen(make_fixer().l10n, PROVIDERS, 100, None, [])
    assert text.splitlines()[2] == wd.SEPARATOR and "" not in text.splitlines()


def test_history_request_failure_is_not_fatal():
    fixer = make_fixer()

    def boom(*_):
        raise RuntimeError("403")

    fixer.account.get_transactions = boom
    assert asyncio.run(wd._history(fixer)) == []


def test_history_requests_withdrawals_newest_first():
    fixer = make_fixer()
    asked = []

    def get_transactions(count, cursor, flt):
        asked.append((count, cursor, flt))
        return N(transactions=[tx(10), tx(20)])

    fixer.account.get_transactions = get_transactions
    got = asyncio.run(wd._history(fixer))
    assert asked == [(wd.HISTORY_FETCH, None, {"operation": ["WITHDRAW"]})]
    assert [t.created_at[:10] for t in got] == ["2026-10-20", "2026-10-10"]


# ----------------------------------------------------------------------
# «До завтра»
# ----------------------------------------------------------------------

class OldMessage:
    """Сообщение старше 48 часов: удалить нельзя, изменить можно."""

    def __init__(self):
        self.edits = []

    async def delete(self):
        raise RuntimeError("message can't be deleted for everyone")

    async def edit_text(self, text, reply_markup=None, **_):
        self.edits.append((text, reply_markup))


def test_shutdown_ack_collapses_old_message(tmp_path):
    from fixer.tg.handlers.system import cb_shutdown_ack
    fixer = make_fixer()
    fixer.SHUTDOWN_MSG_FILE = str(tmp_path / "shutdown.json")
    answers = []

    async def answer(text=None, **_):
        answers.append(text)

    query = N(message=OldMessage(), answer=answer)
    asyncio.run(cb_shutdown_ack(query, fixer))
    assert query.message.edits == [("✖️ Меню закрыто.", None)]
    assert answers == [None]  # без ложного «Сообщение удалено»


def test_startup_cleanup_collapses_what_cannot_be_deleted(tmp_path):
    from fixer.core import Fixer
    path = tmp_path / "shutdown.json"
    path.write_text(json.dumps([{"chat_id": 1, "message_id": 5}, {"chat_id": 2, "message_id": 6}]))
    edits, deleted = [], []

    class Bot:
        async def delete_message(self, chat_id, message_id):
            if chat_id == 1:
                raise RuntimeError("message can't be deleted")
            deleted.append(message_id)

        async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None):
            edits.append((chat_id, message_id, text))

    fake = N(bot=Bot(), SHUTDOWN_MSG_FILE=str(path), l10n=make_fixer().l10n)
    asyncio.run(Fixer._cleanup_shutdown_message(fake))
    assert deleted == [6] and edits == [(1, 5, "✖️ Меню закрыто.")]
    assert not path.exists()


def test_startup_cleanup_runs_after_bot_is_created():
    """Раньше уборка вызывалась до создания бота и молча ничего не делала."""
    import inspect

    from fixer.core import Fixer
    src = inspect.getsource(Fixer.run)
    assert src.index("setup_telegram(self)") < src.index("_cleanup_shutdown_message()")


# ----------------------------------------------------------------------
# Картинки покупателя
# ----------------------------------------------------------------------

class MediaBot(FakeTgBot):
    def __init__(self, fail_photos=False):
        super().__init__()
        self.photos, self.albums, self.fail_photos = [], [], fail_photos

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        if self.fail_photos:
            raise RuntimeError("wrong file identifier/HTTP URL specified")
        self.photos.append((photo, caption))
        self._message_id += 1
        return N(chat=N(id=chat_id), message_id=self._message_id)

    async def send_media_group(self, chat_id, media, **kwargs):
        if self.fail_photos:
            raise RuntimeError("failed to get HTTP URL content")
        self.albums.append([(m.media, m.caption) for m in media])
        out = []
        for _ in media:
            self._message_id += 1
            out.append(N(chat=N(id=chat_id), message_id=self._message_id))
        return out


def _setup(bot, history=None):
    fixer = make_fixer()
    fixer.settings.notifications.new_message = True
    me = N(id="me-id", username="seller", raw_role="USER", role=None)
    buyer = N(id="b1", username="B1zzare", raw_role="USER", role=None)
    chat = N(id="chat-9", type=ChatTypes.PM, users=[me, buyer], deals=[])
    if history is not None:
        fixer.account.get_chat_messages = lambda chat_id, count=24: N(messages=history)
    notifier = Notifier(fixer, bot, N(all_ids={1}))
    return notifier, chat, buyer


def img(url, mime="image/png"):
    return N(id=url, url=url, filename=None, mime=mime)


def message(buyer, text="", images=(), file=None, mid="m1"):
    return N(id=mid, text=text, user=buyer, event=None, event_by_user=None, moderator=None, item=None,
             deal=None, images=list(images), file=file, buttons=[])


def test_image_urls_from_images_and_image_file_only():
    m = N(images=[img("https://a/1.png")], file=img("https://a/2.jpg", "image/jpeg"))
    assert message_image_urls(m) == ["https://a/1.png", "https://a/2.jpg"]
    assert message_image_urls(N(images=[], file=img("https://a/doc.pdf", "application/pdf"))) == []


def test_single_photo_comes_with_the_notification():
    bot = MediaBot()
    notifier, chat, buyer = _setup(bot)
    m = message(buyer, file=img("https://cdn/s.png"))
    asyncio.run(notifier.on_event(NewMessageEvent(None, chat, m)))
    (photo, caption), = bot.photos
    assert photo == "https://cdn/s.png"
    assert "Сообщение от B1zzare" in caption and "💬:🖼 <i>Фото</i>" in caption
    assert bot.sent == []
    assert "chat-9" in notifier.reply_map.values()


def test_photo_missing_in_ws_frame_is_taken_from_chat_history():
    bot = MediaBot()
    history = [message(None, mid="m0", text="старое"),
               N(**{**vars(message(None, mid="m1")), "images": [img("https://cdn/x.png")]})]
    notifier, chat, buyer = _setup(bot, history)
    asyncio.run(notifier.on_event(NewMessageEvent(None, chat, message(buyer, mid="m1"))))
    assert [p for p, _ in bot.photos] == ["https://cdn/x.png"]


def test_several_photos_as_album_with_caption_on_first_and_text_kept():
    bot = MediaBot()
    notifier, chat, buyer = _setup(bot)
    m = message(buyer, text="Key is invalid", images=[img("https://cdn/1.png"), img("https://cdn/2.png")])
    asyncio.run(notifier.on_event(NewMessageEvent(None, chat, m)))
    (album,) = bot.albums
    assert [u for u, _ in album] == ["https://cdn/1.png", "https://cdn/2.png"]
    assert "Key is invalid" in album[0][1] and album[1][1] is None
    assert len([v for v in notifier.reply_map.values() if v == "chat-9"]) == 2


def test_photo_not_accepted_by_telegram_falls_back_to_links():
    bot = MediaBot(fail_photos=True)
    notifier, chat, buyer = _setup(bot)
    m = message(buyer, images=[img("https://cdn/1.png")])
    asyncio.run(notifier.on_event(NewMessageEvent(None, chat, m)))
    (_, text), = bot.sent
    assert '<a href="https://cdn/1.png">🖼 1</a>' in text


def test_text_message_without_images_unchanged_and_no_extra_request():
    bot = MediaBot()
    notifier, chat, buyer = _setup(bot)

    def boom(*a, **k):
        raise AssertionError("история не нужна, когда есть текст")

    notifier.fixer.account.get_chat_messages = boom
    asyncio.run(notifier.on_event(NewMessageEvent(None, chat, message(buyer, text="Привет"))))
    (_, text), = bot.sent
    assert "💬:Привет" in text and not bot.photos
