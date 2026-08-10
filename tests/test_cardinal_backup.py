"""Тесты бэкапа Cardinal: сборка zip-архива configs/ + storage/ (без логов)."""
import io
import zipfile

from cardinal.tg.handlers.system import build_backup_zip


def make_dirs(tmp_path):
    configs = tmp_path / "configs"
    storage = tmp_path / "storage"
    (configs).mkdir()
    (storage / "stock").mkdir(parents=True)
    (storage / "logs").mkdir()

    (configs / "main.toml").write_text("language = \"ru\"\n", encoding="utf-8")
    (configs / "blacklist.toml").write_text("usernames = []\n", encoding="utf-8")
    (storage / "stock" / "lot.txt").write_text("SECRET-1\n", encoding="utf-8")
    (storage / "greeting.sqlite3").write_bytes(b"fake-db")
    (storage / "logs" / "cardinal.log").write_text("log line\n", encoding="utf-8")
    return str(configs), str(storage)


def test_backup_contains_configs_and_storage(tmp_path):
    configs, storage = make_dirs(tmp_path)
    data = build_backup_zip(configs, storage)
    names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
    assert "configs/main.toml" in names
    assert "configs/blacklist.toml" in names
    assert "storage/stock/lot.txt" in names
    assert "storage/greeting.sqlite3" in names


def test_backup_excludes_logs(tmp_path):
    configs, storage = make_dirs(tmp_path)
    data = build_backup_zip(configs, storage)
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert not any("logs" in name for name in names)


def test_backup_file_contents_roundtrip(tmp_path):
    configs, storage = make_dirs(tmp_path)
    data = build_backup_zip(configs, storage)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.read("storage/stock/lot.txt") == b"SECRET-1\n"


def test_backup_missing_dirs_gives_empty_archive(tmp_path):
    data = build_backup_zip(str(tmp_path / "no_configs"), str(tmp_path / "no_storage"))
    assert zipfile.ZipFile(io.BytesIO(data)).namelist() == []
