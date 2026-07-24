#!/usr/bin/env python3
"""Скачивает JS-чанки playerok.com в `_jsbundle/` для последующего `build_hashes.py`.

Cookies (Netscape cookie.txt или `NAME=VALUE; ...`) передаются через:

  --cookies PATH   или   PLAYEROK_COOKIES / PLAYEROK_COOKIES_FILE

Пример:

  python tools/graphql/collect_gql.py --cookies /secure/cookies.txt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from curl_cffi import requests as cr

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://playerok.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def load_cookies(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    jar: dict[str, str] = {}
    # Netscape cookie.txt
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line or line.startswith("# "):
            continue
        raw = line[len("#HttpOnly_"):] if line.startswith("#HttpOnly_") else line
        parts = raw.split("\t")
        if len(parts) >= 7:
            jar[parts[5]] = parts[6]
    if jar:
        return jar
    # Простая строка cookie: token=...; __ddg5_=...
    for part in text.replace("\n", ";").split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            jar[k.strip()] = v.strip()
    if not jar:
        raise SystemExit(f"Не удалось разобрать cookies из {path}")
    return jar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cookies",
        type=Path,
        default=None,
        help="Файл cookies (Netscape или token=...; ...)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "_jsbundle",
        help="Куда складывать скачанные чанки (по умолчанию _jsbundle/)",
    )
    args = parser.parse_args()

    cookies_path = args.cookies
    if cookies_path is None:
        env_file = os.environ.get("PLAYEROK_COOKIES_FILE")
        env_raw = os.environ.get("PLAYEROK_COOKIES")
        if env_file:
            cookies_path = Path(env_file)
        elif env_raw:
            tmp = args.out_dir / "_cookies_env.txt"
            args.out_dir.mkdir(parents=True, exist_ok=True)
            tmp.write_text(env_raw, encoding="utf-8")
            cookies_path = tmp
        else:
            raise SystemExit(
                "Укажите cookies: --cookies PATH или PLAYEROK_COOKIES / PLAYEROK_COOKIES_FILE"
            )

    cookies = load_cookies(cookies_path)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    sess = cr.Session(impersonate="chrome124")
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": UA,
        "referer": "https://playerok.com/",
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
    }

    print("Скачиваю главную страницу...")
    response = sess.get(BASE, headers=headers, timeout=30)
    print("main page status:", response.status_code, "len:", len(response.text))
    html = response.text
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    js_urls: set[str] = set()
    for pattern in (
        r'(?:src|href)="([^"]+\.js)"',
        r'"([^"]*_next/static/[^"]+\.js)"',
        r'/(_next/[^"\'\s]+\.js)',
    ):
        for match in re.finditer(pattern, html):
            js_urls.add(match.group(1))

    normalized: set[str] = set()
    for url in js_urls:
        if url.startswith("http"):
            normalized.add(url)
        elif url.startswith("/"):
            normalized.add(BASE + url)
        else:
            normalized.add(BASE + "/" + url)
    print(f"Найдено {len(normalized)} js-ссылок на главной")

    downloaded: list[str] = []
    for url in sorted(normalized):
        try:
            chunk = sess.get(url, headers=headers, timeout=30)
            if chunk.status_code != 200:
                continue
            fname = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1])
            path = out_dir / fname
            path.write_text(chunk.text, encoding="utf-8")
            downloaded.append(str(path))
        except Exception as exc:
            print("ошибка загрузки", url, exc, file=sys.stderr)
    print(f"Скачано {len(downloaded)} чанков → {out_dir}")
    (out_dir / "_downloaded.json").write_text(
        json.dumps(downloaded, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
