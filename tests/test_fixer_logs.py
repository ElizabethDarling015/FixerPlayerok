"""«📄 Логи»: разбор файла, фильтры, листание по размеру сообщения, кнопки."""
from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace as N

from fixer import log_reader as lr
from fixer.tg.handlers import logs
from fixer_helpers import make_fixer

NOW = datetime.datetime(2026, 10, 22, 14, 30, 0)

SAMPLE = """2026-10-22 12:00:00.001 INFO     fixer.core:10 — старт
2026-10-22 14:02:11.123 WARNING  fixer.tg.handlers.chats:512 — Playerok не ответил на «Прочитано»
2026-10-22 14:05:40.000 ERROR    fixer.tg.notifications:390 — Не удалось отправить уведомление
Traceback (most recent call last):
  File "x.py", line 1, in <module>
RuntimeError: chat not found
2026-10-22 14:10:00.000 DEBUG    playerokapi.account:77 — запрос items <b>
2026-10-22 14:20:00.000 SUCCESS  playerokapi.autodelivery:200 — выдано
"""


def entries():
    return lr.parse(SAMPLE)


def test_parse_with_traceback_attached_to_entry():
    es = entries()
    assert [e.level for e in es] == ["INFO", "WARNING", "ERROR", "DEBUG", "SUCCESS"]
    assert es[2].extra[-1] == "RuntimeError: chat not found"
    assert [e.section for e in es] == [None, "chat", "tg", "api", "ad"]


def test_filters_level_period_section():
    es = entries()
    assert len(lr.apply_filters(es, "a", "0", "all", NOW)) == 5
    assert [e.level for e in lr.apply_filters(es, "w", "60", "all", NOW)] == ["WARNING", "ERROR"]
    assert [e.level for e in lr.apply_filters(es, "i", "15", "all", NOW)] == ["SUCCESS"]  # 25 ≥ 20, 14:20
    assert [e.level for e in lr.apply_filters(es, "e", "0", "all", NOW)] == ["ERROR"]
    assert [e.level for e in lr.apply_filters(es, "a", "0", "chat", NOW)] == ["WARNING"]


def test_screen_text_and_buttons():
    l10n = make_fixer().l10n
    es = lr.apply_filters(entries(), "a", "0", "all", NOW)
    text, markup = logs.build_logs_screen(l10n, es, "a", "0", "all", 0, 3_500_000)
    assert "\n\n━" not in text
    assert "<code>22.10 14:05:40</code> ❌ <b>notifications</b> Не удалось" in text
    assert "↳ <i>RuntimeError: chat not found</i>" in text
    assert "запрос items &lt;b&gt;" in text  # HTML экранирован
    assert "Показано 5 из 5 · стр. 1/1 · файл 3.3 МБ" in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert rows[0] == ["lg:a:0:all:0", "lg:i:0:all:0", "lg:w:0:all:0", "lg:e:0:all:0"]
    assert markup.inline_keyboard[0][0].text.startswith("• ")
    assert rows[-3] == ["lgf:a:0:all:0", "lgall"] and rows[-1] == ["sys", "menu"]
    assert all(len(cb.encode()) <= 64 for row in rows for cb in row)


def test_paging_fits_message_and_goes_older():
    l10n = make_fixer().l10n
    base = datetime.datetime(2026, 10, 22, 10, 0)
    es = [lr.Entry(base + datetime.timedelta(seconds=i), "WARNING", "fixer.core", 1, f"запись {i} " + "x" * 120)
          for i in range(200)]
    text, markup = logs.build_logs_screen(l10n, es, "w", "0", "all", 0)
    assert len(text) < 4096 and "запись 199" in text and "запись 0 " not in text
    rows = [[b.callback_data for b in row] for row in markup.inline_keyboard]
    assert ["lg:w:0:all:1"] in rows  # только «Старее» на первой странице
    last = len(logs.paginate([logs.render_entry(e, True) for e in es])) - 1
    text, markup = logs.build_logs_screen(l10n, es, "w", "0", "all", last)
    assert "запись 0 " in text
    assert [f"lg:w:0:all:{last - 1}"] in [[b.callback_data for b in row] for row in markup.inline_keyboard]


def test_bad_callback_falls_back_to_default():
    assert logs.parse_callback("lg:zz:60:all:0") == logs.DEFAULT
    assert logs.parse_callback("lg:e:1440:raise:3") == ("e", "1440", "raise", 3)


def test_handler_reads_file(tmp_path, monkeypatch):
    log = tmp_path / "fixer.log"
    log.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(lr, "log_files", lambda *a, **k: [str(log)])
    edits = []

    class Msg:
        async def edit_text(self, text, reply_markup=None, **_):
            edits.append(text)

    async def answer(*a, **k):
        pass

    asyncio.run(logs.cb_logs(N(data="lg:e:0:all:0", message=Msg(), answer=answer), make_fixer()))
    assert "RuntimeError: chat not found" in edits[0] and "Playerok не ответил" not in edits[0]
