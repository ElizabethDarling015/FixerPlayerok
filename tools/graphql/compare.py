#!/usr/bin/env python3
"""Сравнивает операции библиотеки с `graphql_collected.json` (результат build_hashes.py)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from graphql import parse, print_ast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from playerokapi.graphql_queries import PERSISTED_QUERIES, QUERIES  # noqa: E402


def norm_hash(text: str) -> str:
    return hashlib.sha256(print_ast(parse(text)).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site",
        type=Path,
        default=ROOT / "graphql_collected.json",
        help="JSON с операциями сайта",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "_compare_report.json",
        help="Куда писать JSON-отчёт",
    )
    args = parser.parse_args()

    site = json.loads(args.site.read_text(encoding="utf-8"))
    report: dict = {"persisted": [], "fulltext": [], "new": []}

    for name, libhash in PERSISTED_QUERIES.items():
        entry = site.get(name)
        if not entry:
            report["persisted"].append((name, libhash, None, "НЕТ НА САЙТЕ"))
            continue
        status = "актуален" if entry["sha256Hash"] == libhash else "УСТАРЕЛ"
        report["persisted"].append((name, libhash, entry["sha256Hash"], status))

    for name, text in QUERIES.items():
        try:
            libhash = norm_hash(text)
        except Exception as exc:
            libhash = f"PARSE_ERR:{exc}"
        entry = site.get(name)
        if not entry:
            report["fulltext"].append((name, libhash, None, "НЕТ НА САЙТЕ"))
            continue
        status = "актуален" if entry["sha256Hash"] == libhash else "РАСХОЖДЕНИЕ"
        report["fulltext"].append((name, libhash, entry["sha256Hash"], status))

    lib_names = set(PERSISTED_QUERIES) | set(QUERIES)
    for name, entry in site.items():
        if name not in lib_names:
            report["new"].append((name, entry["kind"], entry["sha256Hash"]))

    print("=== PERSISTED ===")
    for row in report["persisted"]:
        print(f"  {row[3]:10} {row[0]}: lib={str(row[1])[:12]} site={str(row[2])[:12] if row[2] else '---'}")

    print("\n=== FULL-TEXT ===")
    for row in report["fulltext"]:
        print(f"  {row[3]:12} {row[0]}: lib={str(row[1])[:12]} site={str(row[2])[:12] if row[2] else '---'}")

    print(f"\n=== НОВЫЕ на сайте: {len(report['new'])} ===")
    for row in sorted(report["new"]):
        print(f"  [{row[1]}] {row[0]}: {row[2][:12]}")

    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stale = sum(1 for row in report["persisted"] if row[3] == "УСТАРЕЛ")
    diffs = sum(1 for row in report["fulltext"] if row[3] == "РАСХОЖДЕНИЕ")
    print(
        f"\nИТОГО: persisted={len(report['persisted'])} (устарело {stale}), "
        f"fulltext={len(report['fulltext'])} (расхождений {diffs}), "
        f"новых={len(report['new'])}, всего на сайте={len(site)}"
    )


if __name__ == "__main__":
    main()
