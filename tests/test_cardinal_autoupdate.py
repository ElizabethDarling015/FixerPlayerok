"""Тесты модуля автопроверки обновлений (`cardinal.modules.autoupdate`)."""
from __future__ import annotations

from types import SimpleNamespace

from cardinal.modules.autoupdate import AutoUpdateModule
from cardinal.self_update import UpdateCheck, UpdateResult

from cardinal_helpers import make_cardinal


class FakeNotifier:
    def __init__(self, calls):
        self._calls = calls

    async def notify_update_available(self, current, latest):
        self._calls.notified.append((current, latest))

    async def notify_update_installed(self, message):
        self._calls.installed.append(message)

    async def notify_error(self, text):
        self._calls.errors.append(text)


def make_module(auto_install: bool = False):
    cardinal = make_cardinal()
    cardinal.settings.updates.auto_install = auto_install
    calls = SimpleNamespace(notified=[], installed=[], errors=[], restarts=0)
    cardinal.notifier = FakeNotifier(calls)
    cardinal.request_restart = lambda: setattr(calls, "restarts", calls.restarts + 1)
    module = AutoUpdateModule(cardinal)
    return module, cardinal, calls


async def test_update_available_notifies_once_per_version():
    module, _, calls = make_module()
    module._check = lambda: UpdateCheck(True, True, current="aaa111", latest="bbb222")

    await module.check_once()
    await module.check_once()  # повторная проверка той же версии не спамит

    assert calls.notified == [("aaa111", "bbb222")]

    # Новая версия — новое уведомление.
    module._check = lambda: UpdateCheck(True, True, current="aaa111", latest="ccc333")
    await module.check_once()
    assert calls.notified[-1] == ("aaa111", "ccc333")


async def test_no_update_no_notification():
    module, _, calls = make_module()
    module._check = lambda: UpdateCheck(True, False, current="aaa111", latest="aaa111")
    await module.check_once()
    assert calls.notified == [] and calls.restarts == 0


async def test_failed_check_is_silent():
    module, _, calls = make_module()
    module._check = lambda: UpdateCheck(False, False, error="нет сети")
    await module.check_once()
    assert calls.notified == [] and calls.errors == []


async def test_auto_install_updates_and_restarts():
    module, _, calls = make_module(auto_install=True)
    module._check = lambda: UpdateCheck(True, True, current="aaa111", latest="bbb222")
    module._update = lambda: UpdateResult(True, "git", "Обновлено: aaa111 → bbb222.", changed=True)

    await module.check_once()

    assert calls.installed == ["Обновлено: aaa111 → bbb222."]
    assert calls.restarts == 1
    assert calls.notified == []  # при автоустановке отдельное «доступно» не шлём


async def test_auto_install_failure_notifies_error_without_restart():
    module, _, calls = make_module(auto_install=True)
    module._check = lambda: UpdateCheck(True, True, current="aaa111", latest="bbb222")
    module._update = lambda: UpdateResult(False, "git", "git fetch failed")

    await module.check_once()

    assert calls.restarts == 0
    assert calls.errors and "git fetch failed" in calls.errors[0]


async def test_disabled_module_reports_enabled_flag():
    module, cardinal, _ = make_module()
    assert module.enabled  # autoupdate включён по умолчанию
    cardinal.settings.modules.autoupdate = False
    assert not module.enabled
