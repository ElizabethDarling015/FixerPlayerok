#!/usr/bin/env python3
"""Построчный diff полнотекстовых операций библиотеки и сайта."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from graphql import parse, print_ast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from playerokapi.graphql_queries import QUERIES  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "graphql_collected.json")
    parser.add_argument(
        "names",
        nargs="*",
        help="Имена операций (по умолчанию — все QUERIES, у которых хэш отличается)",
    )
    args = parser.parse_args()

    site = json.loads(args.site.read_text(encoding="utf-8"))
    names = list(args.names) if args.names else sorted(QUERIES)
    for name in names:
        if name not in QUERIES:
            print(f"нет в QUERIES: {name}", file=sys.stderr)
            continue
        lib = print_ast(parse(QUERIES[name]))
        site_text = (site.get(name) or {}).get("query") or ""
        if not site_text:
            print(f"\n{name}: нет на сайте")
            continue
        site_canon = print_ast(parse(site_text))
        if lib == site_canon:
            print(f"\n{name}: совпадает")
            continue
        diff = list(
            difflib.unified_diff(
                lib.splitlines(),
                site_canon.splitlines(),
                fromfile=f"lib/{name}",
                tofile=f"site/{name}",
                lineterm="",
            )
        )
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        print(f"\n{'=' * 70}\n{name}: +{added} / -{removed}")
        print("\n".join(diff[:80]))


if __name__ == "__main__":
    main()
