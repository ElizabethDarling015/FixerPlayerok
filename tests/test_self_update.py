"""Тесты self-update Cardinal с GitHub (git / archive), без сети."""
from __future__ import annotations

import io
import tarfile
from pathlib import Path
from types import SimpleNamespace

import cardinal.self_update as self_update


def test_sync_from_extracted_overwrites_code_keeps_protected(tmp_path: Path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    (src / "cardinal").mkdir(parents=True)
    (src / "playerokapi").mkdir()
    (src / "plugins").mkdir()
    (src / "cardinal" / "core.py").write_text("NEW", encoding="utf-8")
    (src / "requirements.txt").write_text("aiogram\n", encoding="utf-8")
    (src / "plugins" / "example_plugin.py").write_text("example", encoding="utf-8")
    (src / "plugins" / "user_plugin.py").write_text("should-not-copy", encoding="utf-8")

    (dest / "cardinal").mkdir(parents=True)
    (dest / "cardinal" / "core.py").write_text("OLD", encoding="utf-8")
    (dest / "configs").mkdir()
    (dest / "configs" / "main.toml").write_text("keep", encoding="utf-8")
    (dest / "storage").mkdir()
    (dest / "plugins").mkdir()
    (dest / "plugins" / "mine.py").write_text("mine", encoding="utf-8")

    touched = self_update._sync_from_extracted(src, dest)

    assert "cardinal/" in touched
    assert (dest / "cardinal" / "core.py").read_text(encoding="utf-8") == "NEW"
    assert (dest / "requirements.txt").read_text(encoding="utf-8") == "aiogram\n"
    assert (dest / "configs" / "main.toml").read_text(encoding="utf-8") == "keep"
    assert (dest / "plugins" / "mine.py").read_text(encoding="utf-8") == "mine"
    assert (dest / "plugins" / "example_plugin.py").read_text(encoding="utf-8") == "example"
    assert not (dest / "plugins" / "user_plugin.py").exists()


def test_update_via_git_already_latest(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    def fake_run(cmd, cwd, timeout=120):
        calls.append(cmd)
        if cmd[:2] == ["git", "remote"]:
            return SimpleNamespace(returncode=0, stdout="https://github.com/scwee/PlayerokCardinal.git\n", stderr="")
        if cmd[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-parse", "HEAD"] or cmd == ["git", "rev-parse", "origin/main"]:
            return SimpleNamespace(returncode=0, stdout="abc123deadbeef\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(self_update, "_run", fake_run)
    result = self_update._update_via_git(tmp_path, "scwee/PlayerokCardinal", "main")
    assert result.ok and not result.changed
    assert "последняя" in result.message.lower() or "Уже" in result.message
    assert not any(cmd[:3] == ["git", "reset", "--hard"] for cmd in calls)


def test_update_via_git_applies_reset(monkeypatch, tmp_path: Path):
    def fake_run(cmd, cwd, timeout=120):
        if cmd[:2] == ["git", "remote"]:
            return SimpleNamespace(returncode=0, stdout="https://github.com/x/y.git\n", stderr="")
        if cmd[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout="oldsha000\n", stderr="")
        if cmd == ["git", "rev-parse", "origin/main"]:
            return SimpleNamespace(returncode=0, stdout="newsha111\n", stderr="")
        if cmd[:3] == ["git", "reset", "--hard"]:
            return SimpleNamespace(returncode=0, stdout="HEAD is now at newsha111\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="bad")

    monkeypatch.setattr(self_update, "_run", fake_run)
    result = self_update._update_via_git(tmp_path, "scwee/PlayerokCardinal", "main")
    assert result.ok and result.changed
    assert "oldsha0" in result.message and "newsha1" in result.message


def test_update_via_archive(monkeypatch, tmp_path: Path):
    dest = tmp_path / "install"
    dest.mkdir()
    (dest / "cardinal").mkdir()
    (dest / "cardinal" / "old.py").write_text("old", encoding="utf-8")

    def fake_download(url: str, path: Path) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            payload = b"print('new')\n"
            info = tarfile.TarInfo(name="PlayerokCardinal-main/cardinal/core.py")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
            req = b"aiogram>=3\n"
            info2 = tarfile.TarInfo(name="PlayerokCardinal-main/requirements.txt")
            info2.size = len(req)
            tar.addfile(info2, io.BytesIO(req))
        path.write_bytes(buf.getvalue())

    monkeypatch.setattr(self_update, "_download_archive", fake_download)
    result = self_update._update_via_archive(dest, "scwee/PlayerokCardinal", "main")
    assert result.ok and result.changed and result.method == "archive"
    assert (dest / "cardinal" / "core.py").read_text(encoding="utf-8") == "print('new')\n"
    assert not (dest / "cardinal" / "old.py").exists()


def test_update_from_github_routes_to_archive(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(self_update, "_is_git_checkout", lambda root: False)

    called = {}

    def fake_archive(root, repo, branch):
        called["ok"] = True
        return self_update.UpdateResult(True, "archive", "ok", changed=True)

    monkeypatch.setattr(self_update, "_update_via_archive", fake_archive)
    monkeypatch.setattr(self_update, "_update_dependencies", lambda root: "pip ok")
    result = self_update.update_from_github(tmp_path, update_deps=True)
    assert called.get("ok") and result.ok and "pip ok" in result.detail


def test_check_for_update_git_detects_new_version(monkeypatch, tmp_path: Path):
    def fake_run(cmd, cwd, timeout=120):
        if cmd[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout="aaa111aaa111\n", stderr="")
        if cmd == ["git", "rev-parse", "origin/main"]:
            return SimpleNamespace(returncode=0, stdout="bbb222bbb222\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(self_update, "_run", fake_run)
    monkeypatch.setattr(self_update, "_is_git_checkout", lambda root: True)

    check = self_update.check_for_update(tmp_path)
    assert check.ok and check.available
    assert check.current == "aaa111aaa111" and check.latest == "bbb222bbb222"


def test_check_for_update_archive_uses_baseline(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(self_update, "_is_git_checkout", lambda root: False)
    monkeypatch.setattr(self_update, "_remote_head_sha", lambda repo, branch: "c" * 40)

    # Первый запуск: базовый SHA только записывается, обновление не предлагается.
    first = self_update.check_for_update(tmp_path)
    assert first.ok and not first.available
    assert (tmp_path / "storage" / "update_baseline.txt").read_text() == "c" * 40

    second = self_update.check_for_update(tmp_path)
    assert second.ok and not second.available

    monkeypatch.setattr(self_update, "_remote_head_sha", lambda repo, branch: "d" * 40)
    third = self_update.check_for_update(tmp_path)
    assert third.ok and third.available


def test_check_for_update_archive_no_network(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(self_update, "_is_git_checkout", lambda root: False)
    monkeypatch.setattr(self_update, "_remote_head_sha", lambda repo, branch: None)
    check = self_update.check_for_update(tmp_path)
    assert not check.ok and not check.available and check.error
