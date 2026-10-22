"""«💾 Бэкап конфигов»: состав архива, проверка при импорте, применение, экран и FSM."""
from __future__ import annotations

import asyncio
import io
import json
import os
import zipfile
from types import SimpleNamespace as N

import pytest

from fixer import backup
from fixer.settings import load_autodelivery_config, load_main_settings
from fixer.tg.handlers import backup as bk_handlers
from fixer_helpers import make_fixer

MAIN = '''language = "ru"

[playerok]
cookies = "token=abc; __ddg5_=x"

[telegram]
token = "111:AAA"
admin_ids = [42]

[modules]
autoresponse = false
'''


def make_bot_dir(root, *, main=MAIN, stock="KEY-1\nKEY-2\n", abs_stock=False):
    (root / "configs").mkdir()
    (root / "storage" / "stock").mkdir(parents=True)
    (root / "storage" / "logs").mkdir()
    (root / "configs" / "main.toml").write_text(main, encoding="utf-8")
    (root / "configs" / "blacklist.toml").write_text('usernames = ["bad"]\n', encoding="utf-8")
    (root / "configs" / "autoresponse.toml").write_text("", encoding="utf-8")
    stock_path = str(root / "elsewhere" / "go.txt") if abs_stock else "storage/stock/go.txt"
    os.makedirs(os.path.dirname(os.path.join(root, stock_path)), exist_ok=True)
    with open(os.path.join(root, stock_path), "w", encoding="utf-8") as f:
        f.write(stock)
    (root / "configs" / "autodelivery.toml").write_text(
        f'[lots."GoLand навсегда"]\nstock_file = "{stock_path}"\n', encoding="utf-8")
    (root / "storage" / "withdrawal.json").write_text('{"provider": "SBP", "bank_name": "Сбербанк"}', encoding="utf-8")
    (root / "storage" / "autodelivery_ledger.sqlite3").write_bytes(b"ledger")
    (root / "storage" / "logs" / "fixer.log").write_text("log\n", encoding="utf-8")
    (root / "storage" / "proxies.sqlite3").write_bytes(b"px")


@pytest.fixture
def botdir(tmp_path, monkeypatch):
    src = tmp_path / "mac"
    src.mkdir()
    make_bot_dir(src)
    monkeypatch.chdir(src)
    return src


def test_export_contents(botdir):
    data = backup.build_backup(username="Bez Limit")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        manifest = json.loads(z.read("manifest.json"))
        assert z.read("stock/go.txt") == b"KEY-1\nKEY-2\n"
    assert names == {"manifest.json", "configs/main.toml", "configs/blacklist.toml", "configs/autoresponse.toml",
                     "configs/autodelivery.toml", "storage/withdrawal.json", "stock/go.txt"}
    assert manifest["format"] == "fixer-backup" and manifest["account"] == "Bez Limit"
    assert manifest["stocks"] == {"GoLand навсегда": "stock/go.txt"}
    assert backup.export_filename("Bez Limit").startswith("fixer-backup_Bez_Limit_")


def _vm(tmp_path, monkeypatch, **kw):
    vm = tmp_path / "vm"
    vm.mkdir()
    make_bot_dir(vm, **kw)
    monkeypatch.chdir(vm)
    return vm


def test_import_roundtrip_to_other_machine(tmp_path, monkeypatch, botdir):
    data = backup.build_backup(username="BezLimit")
    vm = _vm(tmp_path, monkeypatch, main=MAIN.replace("autoresponse = false", "autoresponse = true"),
             stock="OLD\n")
    current = load_main_settings()
    plan = backup.read_backup(data)
    result = backup.apply_backup(plan, current)
    assert result["telegram"] == "same" and result["stocks"] == 1
    assert load_main_settings().modules.autoresponse is False
    assert (vm / "storage" / "stock" / "go.txt").read_text(encoding="utf-8") == "KEY-1\nKEY-2\n"
    assert "Сбербанк" in (vm / "storage" / "withdrawal.json").read_text(encoding="utf-8")
    # Журнал выдач машины не тронут.
    assert (vm / "storage" / "autodelivery_ledger.sqlite3").read_bytes() == b"ledger"


def test_absolute_stock_path_from_other_machine_moves_into_bot_folder(tmp_path, monkeypatch):
    mac = tmp_path / "mac2"
    mac.mkdir()
    make_bot_dir(mac, abs_stock=True)
    monkeypatch.chdir(mac)
    data = backup.build_backup()
    vm = _vm(tmp_path, monkeypatch)
    backup.apply_backup(backup.read_backup(data), load_main_settings())
    lot = load_autodelivery_config().lots["GoLand навсегда"]
    assert not os.path.isabs(lot.stock_file) and lot.stock_file.startswith("storage")
    assert (vm / lot.stock_file).read_text(encoding="utf-8") == "KEY-1\nKEY-2\n"


def test_telegram_token_change_detected(tmp_path, monkeypatch, botdir):
    data = backup.build_backup()
    _vm(tmp_path, monkeypatch, main=MAIN.replace("111:AAA", "222:BBB"))
    result = backup.apply_backup(backup.read_backup(data), load_main_settings())
    assert result["telegram"] == "changed"
    assert load_main_settings().telegram.token == "111:AAA"


def _manifest(version=1, stocks=None):
    return json.dumps({"format": "fixer-backup", "version": version, "stocks": stocks or {}})


def _zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


@pytest.mark.parametrize("make, error", [
    (lambda: b"not a zip", "zip"),
    (lambda: _zip({"configs/main.toml": MAIN}), "описи"),
    (lambda: _zip({"manifest.json": json.dumps({"format": "other"})}), "не бэкап Fixer"),
    (lambda: _zip({"manifest.json": _manifest(), "configs/main.toml": "language = 'xx'\n"}), "main.toml"),
    (lambda: _zip({"manifest.json": _manifest(), "configs/main.toml": MAIN, "../evil.py": "x"}), "лишние"),
    (lambda: _zip({"manifest.json": _manifest(version=99), "configs/main.toml": MAIN}), "новой версией"),
    (lambda: _zip({"manifest.json": _manifest(stocks={"x": "../../etc/passwd"}), "configs/main.toml": MAIN}),
     "имя склада"),
])
def test_bad_archives_rejected_before_writing(botdir, make, error):
    before = (botdir / "configs" / "main.toml").read_text(encoding="utf-8")
    with pytest.raises(backup.BackupError, match=error):
        backup.read_backup(make())
    assert (botdir / "configs" / "main.toml").read_text(encoding="utf-8") == before


def test_safety_copies_keep_last_five(botdir):
    import datetime
    for i in range(7):
        backup.safety_copy("me", now=datetime.datetime(2026, 10, 22, 10, i))
    copies = sorted(os.listdir(botdir / "storage" / "backups"))
    assert len(copies) == 5 and copies[0].endswith("10-02.zip")


def test_applied_mark_read_once(botdir):
    backup.write_applied_mark({"created_at": "2026-10-22T18:30:00"})
    assert backup.pop_applied_mark()["created_at"] == "2026-10-22T18:30:00"
    assert backup.pop_applied_mark() is None


# ----------------------------------------------------------------------
# Экран и импорт через Telegram
# ----------------------------------------------------------------------

def test_menu_rows():
    text, markup = bk_handlers.build_backup_menu(make_fixer().l10n)
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows == [["bk:import", "bk:export"], ["sys", "menu"]]
    assert "\n\n━" not in text and "склады" in text


class FakeState:
    def __init__(self):
        self.state, self.data = None, {}

    async def clear(self):
        self.state, self.data = None, {}

    async def set_state(self, value):
        self.state = value

    async def get_state(self):
        return self.state

    async def update_data(self, **kw):
        self.data.update(kw)

    async def get_data(self):
        return dict(self.data)


class Bot:
    def __init__(self, payload=b""):
        self.payload, self.edits = payload, []

    async def download(self, document, destination):
        destination.write(self.payload)

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **_):
        self.edits.append(text)


class UserMessage:
    def __init__(self, bot, document=None):
        self.bot, self.document, self.deleted = bot, document, False
        self.chat = N(id=1)

    async def delete(self):
        self.deleted = True


def _run_import(fixer, payload):
    bot = Bot(payload)
    state = FakeState()
    asyncio.run(state.update_data(panel=[1, 10]))
    asyncio.run(state.set_state(bk_handlers.BackupStates.waiting_file))
    msg = UserMessage(bot, N(file_size=len(payload)))
    asyncio.run(bk_handlers.msg_backup_file(msg, state, fixer))
    return msg, bot, state


def test_import_via_telegram_applies_and_restarts(tmp_path, monkeypatch, botdir):
    data = backup.build_backup(username="BezLimit")
    _vm(tmp_path, monkeypatch, main=MAIN.replace("autoresponse = false", "autoresponse = true"))
    fixer = make_fixer(load_main_settings())
    restarts = []
    fixer.request_restart = lambda: restarts.append(1)
    msg, bot, state = _run_import(fixer, data)
    assert msg.deleted and restarts == [1] and state.state is None
    assert "✅ Бэкап от" in bot.edits[-1] and "без изменений" in bot.edits[-1]
    assert load_main_settings().modules.autoresponse is False
    assert os.listdir("storage/backups")  # страховочная копия есть
    assert backup.pop_applied_mark()["account"] == "BezLimit"


def test_bad_file_via_telegram_keeps_waiting(botdir):
    fixer = make_fixer(load_main_settings())
    fixer.request_restart = lambda: pytest.fail("перезапуск не нужен")
    msg, bot, state = _run_import(fixer, b"garbage")
    assert msg.deleted and "Архив не принят: это не zip-архив" in bot.edits[-1]
    assert state.state == bk_handlers.BackupStates.waiting_file


def test_text_instead_of_file_is_deleted(botdir):
    bot = Bot()
    state = FakeState()
    asyncio.run(state.update_data(panel=[1, 10]))
    msg = UserMessage(bot)
    asyncio.run(bk_handlers.msg_not_a_file(msg, state, make_fixer()))
    assert msg.deleted and "Нужен файл" in bot.edits[-1]


def test_started_notification_shows_applied_line(botdir):
    from fixer.tg.notifications import Notifier
    from fixer_helpers import FakeTgBot
    backup.write_applied_mark({"created_at": "2026-10-22T18:30:00"})
    fixer = make_fixer()
    bot = FakeTgBot()
    asyncio.run(Notifier(fixer, bot, N(all_ids={1})).notify_started())
    assert bot.sent[0][1].startswith("✅ Бэкап от 22.10.2026 18:30 применён\n\n")
