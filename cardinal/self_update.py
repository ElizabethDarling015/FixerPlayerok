"""
Обновление PlayerokCardinal с GitHub (для кнопки в TG-панели).

Два режима:
1. Есть `.git` и `git` в PATH — `fetch` + `reset --hard` на ветку origin.
2. Иначе — скачать архив ветки с GitHub и аккуратно перезаписать код
   (configs/, storage/, .venv/, plugins/ не трогаем).

Затем опционально обновляет pip-зависимости из `requirements.txt`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

#: Репозиторий по умолчанию (owner/name).
DEFAULT_REPO = "scwee/PlayerokCardinal"
DEFAULT_BRANCH = "main"

#: Каталоги из архива, которые можно перезаписать целиком.
SYNC_DIRS = (
    "cardinal",
    "playerokapi",
    "docs",
    "assets",
    "examples",
    "tools",
    "tests",
)

#: Файлы в корне, которые можно перезаписать.
SYNC_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "cardinal.sh",
    "Cardinal.bat",
    "LICENSE",
    "README.md",
    "PlayerokCardinal@.service",
)

#: Никогда не трогать при обновлении из архива.
PROTECTED_NAMES = frozenset(
    {
        "configs",
        "storage",
        ".venv",
        "venv",
        ".git",
        "plugins",
        "__pycache__",
    }
)

_GIT_TIMEOUT = 120
_DOWNLOAD_TIMEOUT = 120


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    method: str  # "git" | "archive" | "none"
    message: str
    detail: str = ""
    changed: bool = False


@dataclass(frozen=True)
class UpdateCheck:
    """Результат проверки наличия обновления (без применения)."""

    ok: bool
    available: bool
    current: str = ""
    latest: str = ""
    error: str = ""


#: Файл с базовым SHA для установок из архива (нет .git — не с чем сравнивать иначе).
ARCHIVE_BASELINE_FILE = os.path.join("storage", "update_baseline.txt")


def project_root() -> Path:
    """Корень установки: родитель пакета `cardinal/`."""
    return Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path, timeout: int = _GIT_TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _git_available() -> bool:
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _is_git_checkout(root: Path) -> bool:
    return (root / ".git").exists() and _git_available()


def _ensure_origin(root: Path, repo: str) -> None:
    remote = _run(["git", "remote", "get-url", "origin"], root)
    if remote.returncode == 0 and remote.stdout.strip():
        return
    url = f"https://github.com/{repo}.git"
    added = _run(["git", "remote", "add", "origin", url], root)
    if added.returncode != 0:
        # remote мог появиться между проверками — пробуем set-url
        _run(["git", "remote", "set-url", "origin", url], root)


def _update_via_git(root: Path, repo: str, branch: str) -> UpdateResult:
    _ensure_origin(root, repo)

    fetch = _run(["git", "fetch", "--depth", "1", "origin", branch], root)
    if fetch.returncode != 0:
        err = (fetch.stderr or fetch.stdout or "git fetch failed").strip()
        return UpdateResult(False, "git", "Не удалось скачать обновления с GitHub.", err)

    before = _run(["git", "rev-parse", "HEAD"], root)
    after_ref = _run(["git", "rev-parse", f"origin/{branch}"], root)
    if before.returncode != 0 or after_ref.returncode != 0:
        return UpdateResult(False, "git", "Не удалось определить версию (git rev-parse).", (before.stderr or after_ref.stderr).strip())

    old_sha = before.stdout.strip()
    new_sha = after_ref.stdout.strip()
    if old_sha == new_sha:
        return UpdateResult(True, "git", "Уже последняя версия.", old_sha[:12], changed=False)

    reset = _run(["git", "reset", "--hard", f"origin/{branch}"], root)
    if reset.returncode != 0:
        err = (reset.stderr or reset.stdout or "git reset failed").strip()
        return UpdateResult(False, "git", "Не удалось применить обновление (git reset).", err)

    return UpdateResult(
        True,
        "git",
        f"Обновлено: {old_sha[:7]} → {new_sha[:7]}.",
        (reset.stdout or "").strip(),
        changed=True,
    )


def _remote_head_sha(repo: str, branch: str) -> str | None:
    """SHA последнего коммита ветки через GitHub API (`None`, если API недоступен)."""
    url = f"https://api.github.com/repos/{repo}/commits/{branch}"
    request = urllib.request.Request(url, headers={
        "User-Agent": "PlayerokCardinal-Updater/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None
    sha = payload.get("sha") if isinstance(payload, dict) else None
    return sha if isinstance(sha, str) and sha else None


def _read_archive_baseline(root: Path) -> str:
    baseline = root / ARCHIVE_BASELINE_FILE
    try:
        return baseline.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_archive_baseline(root: Path, sha: str) -> None:
    baseline = root / ARCHIVE_BASELINE_FILE
    try:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(sha, encoding="utf-8")
    except OSError:
        pass  # не критично: в худшем случае следующая проверка снова предложит обновиться


def check_for_update(
    root: Path | str | None = None,
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
) -> UpdateCheck:
    """
    Проверяет, есть ли на GitHub более новая версия, НЕ применяя её.

    Git-установка: `git fetch` + сравнение SHA. Установка из архива: сравнение SHA ветки
    (GitHub API) с сохранённым базовым (`storage/update_baseline.txt`); при первом запуске
    базовый SHA просто записывается — «обновление доступно» не сообщается.
    """
    dest = Path(root) if root is not None else project_root()
    if not dest.is_dir():
        return UpdateCheck(False, False, error=f"Каталог не найден: {dest}")

    if _is_git_checkout(dest):
        fetch = _run(["git", "fetch", "--depth", "1", "origin", branch], dest)
        if fetch.returncode != 0:
            return UpdateCheck(False, False, error=(fetch.stderr or fetch.stdout or "git fetch failed").strip())
        head = _run(["git", "rev-parse", "HEAD"], dest)
        remote = _run(["git", "rev-parse", f"origin/{branch}"], dest)
        if head.returncode != 0 or remote.returncode != 0:
            return UpdateCheck(False, False, error=(head.stderr or remote.stderr or "git rev-parse failed").strip())
        current, latest = head.stdout.strip(), remote.stdout.strip()
        return UpdateCheck(True, current != latest, current=current[:12], latest=latest[:12])

    latest_sha = _remote_head_sha(repo, branch)
    if latest_sha is None:
        return UpdateCheck(False, False, error="GitHub API недоступен (нет сети или лимит запросов).")
    known = _read_archive_baseline(dest)
    if not known:
        _write_archive_baseline(dest, latest_sha)
        return UpdateCheck(True, False, current="?", latest=latest_sha[:12])
    return UpdateCheck(True, known != latest_sha, current=known[:12], latest=latest_sha[:12])


def _archive_url(repo: str, branch: str) -> str:
    return f"https://github.com/{repo}/archive/refs/heads/{branch}.tar.gz"


def _download_archive(url: str, dest: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PlayerokCardinal-Updater/1.0"},
    )
    with urllib.request.urlopen(request, timeout=_DOWNLOAD_TIMEOUT) as response:
        dest.write_bytes(response.read())


def _extracted_root(extract_dir: Path) -> Path:
    children = [p for p in extract_dir.iterdir() if p.is_dir()]
    if len(children) == 1:
        return children[0]
    return extract_dir


def _sync_from_extracted(src_root: Path, dest_root: Path) -> list[str]:
    """Копирует код из распакованного архива. Возвращает список затронутых путей."""
    touched: list[str] = []
    for name in SYNC_DIRS:
        src = src_root / name
        if not src.is_dir():
            continue
        dest = dest_root / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        touched.append(name + "/")

    for name in SYNC_FILES:
        src = src_root / name
        if not src.is_file():
            continue
        dest = dest_root / name
        shutil.copy2(src, dest)
        if name.endswith(".sh"):
            try:
                os.chmod(dest, dest.stat().st_mode | 0o111)
            except OSError:
                pass
        touched.append(name)

    # Не затираем пользовательские plugins/, но подтянем example, если его ещё нет.
    example_src = src_root / "plugins" / "example_plugin.py"
    example_dest = dest_root / "plugins" / "example_plugin.py"
    if example_src.is_file():
        example_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example_src, example_dest)
        touched.append("plugins/example_plugin.py")

    return touched


def _update_via_archive(root: Path, repo: str, branch: str) -> UpdateResult:
    url = _archive_url(repo, branch)
    try:
        with tempfile.TemporaryDirectory(prefix="cardinal-update-") as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "src.tar.gz"
            _download_archive(url, archive_path)
            extract_dir = tmp_path / "extract"
            extract_dir.mkdir()
            with tarfile.open(archive_path, "r:gz") as tar:
                # Python 3.12+: filter='data' безопаснее и без DeprecationWarning на 3.14.
                try:
                    tar.extractall(extract_dir, filter="data")
                except TypeError:
                    tar.extractall(extract_dir)
            src_root = _extracted_root(extract_dir)
            # Защита от случайного копирования protected имён, если SYNC_* расширят.
            for name in PROTECTED_NAMES:
                if name in SYNC_DIRS or name in SYNC_FILES:
                    return UpdateResult(False, "archive", f"Внутренняя ошибка: {name} в списке синхронизации.")
            touched = _sync_from_extracted(src_root, root)
    except urllib.error.HTTPError as exc:
        return UpdateResult(False, "archive", f"GitHub вернул HTTP {exc.code}.", str(exc))
    except urllib.error.URLError as exc:
        return UpdateResult(False, "archive", "Не удалось скачать архив с GitHub.", str(exc.reason))
    except (OSError, tarfile.TarError, TimeoutError) as exc:
        return UpdateResult(False, "archive", "Ошибка распаковки/записи обновления.", str(exc))

    if not touched:
        return UpdateResult(False, "archive", "В архиве не найдены файлы кода.")
    return UpdateResult(
        True,
        "archive",
        "Код обновлён из архива GitHub.",
        ", ".join(touched[:12]) + ("…" if len(touched) > 12 else ""),
        changed=True,
    )


def _update_dependencies(root: Path) -> str:
    """Тихо обновляет зависимости текущего интерпретатора. Ошибки — строкой, не исключением."""
    requirements = root / "requirements.txt"
    if not requirements.is_file():
        return "requirements.txt не найден — pip пропущен."
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"pip не выполнен: {exc}"
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "pip failed").strip()
        return f"pip завершился с ошибкой: {err[:400]}"
    return "Зависимости обновлены (pip)."


def update_from_github(
    root: Path | str | None = None,
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    update_deps: bool = True,
) -> UpdateResult:
    """
    Обновляет установку Cardinal с GitHub.

    :param root: корень проекта (по умолчанию — рядом с пакетом `cardinal`).
    :param repo: `owner/name` на GitHub.
    :param branch: ветка (обычно `main`).
    :param update_deps: после успешного обновления кода вызвать pip install -r requirements.txt.
    """
    dest = Path(root) if root is not None else project_root()
    if not dest.is_dir():
        return UpdateResult(False, "none", f"Каталог не найден: {dest}")

    if _is_git_checkout(dest):
        result = _update_via_git(dest, repo, branch)
    else:
        result = _update_via_archive(dest, repo, branch)
        if result.ok and result.changed:
            # Запоминаем установленный SHA — иначе check_for_update будет предлагать
            # это же обновление снова.
            sha = _remote_head_sha(repo, branch)
            if sha:
                _write_archive_baseline(dest, sha)

    if not result.ok:
        return result

    detail_parts = [result.detail] if result.detail else []
    if update_deps and result.changed:
        detail_parts.append(_update_dependencies(dest))
    elif update_deps and not result.changed:
        detail_parts.append("pip пропущен — изменений нет.")

    return UpdateResult(
        result.ok,
        result.method,
        result.message,
        "\n".join(p for p in detail_parts if p),
        changed=result.changed,
    )
