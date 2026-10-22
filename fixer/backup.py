"""Бэкап конфигов Fixer: один zip-архив для переноса между копиями бота (Mac ↔ VM).

Что входит в архив:

* ``configs/main.toml`` — глобальные переключатели и все настройки бота, уведомления,
  аккаунт Playerok (cookies, user-agent, прокси), токен Telegram-бота и админы,
  ночное сообщение, сводка и часовой пояс, автоподнятие;
* ``configs/autoresponse.toml``, ``configs/autodelivery.toml``, ``configs/blacklist.toml``;
* склады автовыдачи (сами позиции товара) — ``stock/…``, по одному файлу на лот;
* ``storage/withdrawal.json`` — последний способ вывода («⚡ Как в прошлый раз»);
* ``manifest.json`` — опись: формат, версия, дата, аккаунт, какой склад к какому лоту.

Что не входит, специально: журнал выдач (память «какой сделке что выдано» — с другой машины
он навредит), сохранённые прокси (у каждой машины своя сеть), кэши и логи.

Импорт: архив проверяется целиком (опись, имена файлов, валидность каждого конфига) до
того, как что-либо записывается; текущие настройки перед применением сохраняются в
``storage/backups/`` (последние `KEEP_SAFETY_COPIES`). После применения нужен перезапуск —
``main.toml`` читается только при старте.
"""
from __future__ import annotations

import datetime
import io
import json
import os
import re
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass, field

from .settings import (
    AUTODELIVERY_CONFIG,
    AUTORESPONSE_CONFIG,
    BLACKLIST_CONFIG,
    CONFIG_DIR,
    MAIN_CONFIG,
    STORAGE_DIR,
    AutoDeliveryConfig,
    AutoResponseConfig,
    BlacklistConfig,
    ConfigError,
    MainSettings,
    _load_config,
)
from .toml_utils import write_toml

FORMAT = "fixer-backup"
VERSION = 1
MANIFEST = "manifest.json"
#: Конфиги: имя в архиве → путь на диске (по умолчанию).
CONFIG_FILES = {
    "configs/main.toml": MAIN_CONFIG,
    "configs/autoresponse.toml": AUTORESPONSE_CONFIG,
    "configs/autodelivery.toml": AUTODELIVERY_CONFIG,
    "configs/blacklist.toml": BLACKLIST_CONFIG,
}
WITHDRAWAL_FILE = os.path.join(STORAGE_DIR, "withdrawal.json")
WITHDRAWAL_ARCNAME = "storage/withdrawal.json"
STOCK_DIR = os.path.join(STORAGE_DIR, "stock")
BACKUPS_DIR = os.path.join(STORAGE_DIR, "backups")
#: Сколько страховочных копий (перед импортом) хранить.
KEEP_SAFETY_COPIES = 5
#: Отметка «бэкап применён» — её читает стартовое уведомление после перезапуска.
APPLIED_MARK = os.path.join(STORAGE_DIR, "backup_applied.json")
#: Предел размера архива (Telegram отдаёт ботам файлы до 20 МБ).
MAX_ARCHIVE_SIZE = 20 * 1024 * 1024

_MODELS = {
    "configs/main.toml": MainSettings,
    "configs/autoresponse.toml": AutoResponseConfig,
    "configs/autodelivery.toml": AutoDeliveryConfig,
    "configs/blacklist.toml": BlacklistConfig,
}
_STOCK_RE = re.compile(r"^stock/[\w.-]+\.txt$", re.UNICODE)


class BackupError(Exception):
    """Архив не подходит — понятная причина по-русски."""


def _safe_name(text: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "_", text or "", flags=re.UNICODE).strip("_")
    return cleaned or "fixer"


def export_filename(username: str | None, now: datetime.datetime | None = None) -> str:
    now = now or datetime.datetime.now()
    return f"fixer-backup_{_safe_name(username or '')}_{now:%Y-%m-%d_%H-%M}.zip"


# ----------------------------------------------------------------------
# Экспорт
# ----------------------------------------------------------------------

def build_backup(paths: dict | None = None, *, username: str | None = None,
                 now: datetime.datetime | None = None) -> bytes:
    """Собирает архив. `paths` — подмена путей (для тестов): ключи как в `CONFIG_FILES`,
    плюс ``withdrawal``."""
    paths = {**CONFIG_FILES, "withdrawal": WITHDRAWAL_FILE, **(paths or {})}
    now = now or datetime.datetime.now()
    buffer = io.BytesIO()
    manifest: dict = {"format": FORMAT, "version": VERSION, "created_at": now.isoformat(timespec="seconds"),
                      "account": username, "files": [], "stocks": {}}
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname in CONFIG_FILES:
            path = paths[arcname]
            if os.path.isfile(path):
                archive.write(path, arcname)
                manifest["files"].append(arcname)
        # Склады: по описи autodelivery.toml (путь склада может быть любым — в архиве свой).
        ad_path = paths["configs/autodelivery.toml"]
        if os.path.isfile(ad_path):
            config = _load_config(ad_path, AutoDeliveryConfig, missing_ok=True)
            used: set[str] = set()
            for lot_name, lot in config.lots.items():
                if not os.path.isfile(lot.stock_file):
                    continue
                base = _safe_name(os.path.splitext(os.path.basename(lot.stock_file))[0])[:60]
                arcname, n = f"stock/{base}.txt", 2
                while arcname in used:
                    arcname, n = f"stock/{base}_{n}.txt", n + 1
                used.add(arcname)
                archive.write(lot.stock_file, arcname)
                manifest["stocks"][lot_name] = arcname
        if os.path.isfile(paths["withdrawal"]):
            archive.write(paths["withdrawal"], WITHDRAWAL_ARCNAME)
            manifest["files"].append(WITHDRAWAL_ARCNAME)
        archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def describe(manifest: dict) -> dict:
    """Короткая опись для экрана: дата, аккаунт, сколько складов."""
    return {"created_at": manifest.get("created_at"), "account": manifest.get("account"),
            "stocks": len(manifest.get("stocks") or {})}


# ----------------------------------------------------------------------
# Импорт
# ----------------------------------------------------------------------

@dataclass
class ImportPlan:
    """Проверенное содержимое архива, готовое к записи."""

    manifest: dict
    configs: dict[str, bytes] = field(default_factory=dict)       # arcname → содержимое
    stocks: dict[str, bytes] = field(default_factory=dict)        # имя лота → содержимое склада
    withdrawal: bytes | None = None
    main: MainSettings | None = None
    autodelivery: AutoDeliveryConfig | None = None


def read_backup(data: bytes) -> ImportPlan:
    """Открывает и проверяет архив. Ничего не пишет. Бросает `BackupError`."""
    if len(data) > MAX_ARCHIVE_SIZE:
        raise BackupError("архив больше 20 МБ")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise BackupError("это не zip-архив")
    with archive:
        names = set(archive.namelist())
        if MANIFEST not in names:
            raise BackupError("в архиве нет описи — это не бэкап Fixer")
        try:
            manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
        except Exception:
            raise BackupError("опись архива повреждена")
        if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
            raise BackupError("это не бэкап Fixer")
        if int(manifest.get("version") or 0) > VERSION:
            raise BackupError("бэкап сделан более новой версией бота — сначала обновите бота")

        allowed = set(CONFIG_FILES) | {WITHDRAWAL_ARCNAME, MANIFEST}
        stocks = manifest.get("stocks") or {}
        if not isinstance(stocks, dict):
            raise BackupError("опись складов повреждена")
        for arcname in stocks.values():
            if not isinstance(arcname, str) or not _STOCK_RE.match(arcname):
                raise BackupError(f"недопустимое имя склада в описи: {arcname!r}")
            allowed.add(arcname)
        extra = names - allowed
        if extra:
            raise BackupError("в архиве лишние файлы: " + ", ".join(sorted(extra)[:3]))
        if "configs/main.toml" not in names:
            raise BackupError("в архиве нет главного конфига main.toml")

        plan = ImportPlan(manifest=manifest)
        for arcname, model in _MODELS.items():
            if arcname not in names:
                continue
            raw = archive.read(arcname)
            try:
                parsed = tomllib.loads(raw.decode("utf-8"))
                obj = model.model_validate(parsed)
            except Exception as exc:
                raise BackupError(f"{arcname} не прошёл проверку: {str(exc)[:200]}")
            plan.configs[arcname] = raw
            if arcname == "configs/main.toml":
                plan.main = obj
            elif arcname == "configs/autodelivery.toml":
                plan.autodelivery = obj
        for lot_name, arcname in stocks.items():
            if arcname in names:
                plan.stocks[lot_name] = archive.read(arcname)
        if WITHDRAWAL_ARCNAME in names:
            raw = archive.read(WITHDRAWAL_ARCNAME)
            try:
                json.loads(raw.decode("utf-8"))
            except Exception:
                raise BackupError("withdrawal.json повреждён")
            plan.withdrawal = raw
    return plan


def _atomic_write(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".import-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def stock_target(lot_name: str, original: str) -> str:
    """Куда положить склад лота: исходный путь, если он внутри папки бота (относительный),
    иначе — `storage/stock/<лот>.txt` (абсолютный путь с другой машины здесь не годится)."""
    if original and not os.path.isabs(original) and ".." not in original.replace("\\", "/").split("/"):
        return original
    return os.path.join(STOCK_DIR, f"{_safe_name(lot_name)[:60]}.txt")


def safety_copy(username: str | None, *, now: datetime.datetime | None = None,
                backups_dir: str = BACKUPS_DIR, paths: dict | None = None) -> str:
    """Страховочная копия текущих настроек перед импортом. Хранятся последние `KEEP_SAFETY_COPIES`."""
    os.makedirs(backups_dir, exist_ok=True)
    now = now or datetime.datetime.now()
    path = os.path.join(backups_dir, "before-import_" + export_filename(username, now))
    with open(path, "wb") as f:
        f.write(build_backup(paths, username=username, now=now))
    copies = sorted(p for p in os.listdir(backups_dir) if p.startswith("before-import_"))
    for old in copies[:-KEEP_SAFETY_COPIES]:
        try:
            os.remove(os.path.join(backups_dir, old))
        except OSError:
            pass
    return path


def apply_backup(plan: ImportPlan, current: MainSettings | None, paths: dict | None = None) -> dict:
    """Записывает проверенный архив на диск. Возвращает итог для отчёта и стартового сообщения:
    ``telegram`` — ``same``/``changed`` (токен бота и список админов), ``stocks`` — сколько складов."""
    paths = {**CONFIG_FILES, "withdrawal": WITHDRAWAL_FILE, **(paths or {})}
    result = {**describe(plan.manifest), "telegram": "same", "stocks": 0}
    if current is not None and plan.main is not None:
        same = (plan.main.telegram.token == current.telegram.token
                and sorted(plan.main.telegram.admin_ids) == sorted(current.telegram.admin_ids))
        result["telegram"] = "same" if same else "changed"

    # Склады: пути в autodelivery.toml приводим к этой машине.
    ad_raw = plan.configs.get("configs/autodelivery.toml")
    if plan.autodelivery is not None:
        stock_by_lot = {}
        for lot_name, lot in plan.autodelivery.lots.items():
            target = stock_target(lot_name, lot.stock_file)
            stock_by_lot[lot_name] = target
            lot.stock_file = target
        ad_raw = None  # перепишем из модели (с новыми путями)
        for lot_name, content in plan.stocks.items():
            target = stock_by_lot.get(lot_name)
            if target:
                _atomic_write(target, content)
                result["stocks"] += 1

    for arcname, raw in plan.configs.items():
        if arcname == "configs/autodelivery.toml":
            continue
        _atomic_write(paths[arcname], raw)
    if plan.autodelivery is not None:
        path = paths["configs/autodelivery.toml"]
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        tmp = path + ".import-tmp"
        write_toml(tmp, plan.autodelivery.model_dump())
        os.replace(tmp, path)
    elif ad_raw is not None:
        _atomic_write(paths["configs/autodelivery.toml"], ad_raw)
    if plan.withdrawal is not None:
        _atomic_write(paths["withdrawal"], plan.withdrawal)
    return result


def write_applied_mark(result: dict, path: str = APPLIED_MARK) -> None:
    _atomic_write(path, json.dumps(result, ensure_ascii=False).encode("utf-8"))


def pop_applied_mark(path: str = APPLIED_MARK) -> dict | None:
    """Читает и удаляет отметку «бэкап применён» (её показывает стартовое уведомление)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    try:
        os.remove(path)
    except OSError:
        pass
    return data if isinstance(data, dict) else None


__all__ = ["BackupError", "ConfigError", "CONFIG_DIR", "build_backup", "read_backup", "apply_backup",
           "safety_copy", "export_filename", "write_applied_mark", "pop_applied_mark"]
