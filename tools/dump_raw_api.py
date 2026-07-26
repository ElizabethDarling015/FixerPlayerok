"""Дамп сырых GraphQL-ответов живого API в storage/probe/raw_*.json.

Только read-only операции. Использует внутренние методы Account для доступа
к сырым данным до парсинга.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.probe_live_api import load_cookies, OUT  # noqa: E402
from playerokapi.account import Account  # noqa: E402


def dump(name: str, data) -> None:
    (OUT / f"raw_{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str))
    print(f"raw_{name}.json: {(OUT / f'raw_{name}.json').stat().st_size} bytes")


def main() -> None:
    acc = Account(cookies=load_cookies(ROOT / "storage" / "probe_token.txt"))
    acc.get()

    # viewer (полный ответ авторизации)
    dump("viewer", acc._query("viewer", {}, idempotent=True))

    # viewerBalance — persisted-запрос, get_balance() вернул None
    try:
        dump("viewerBalance", acc._persisted_query("viewerBalance", {}))
    except Exception as e:
        print(f"viewerBalance: {type(e).__name__}: {e}")

    # попробуем полнотекстовый viewer с балансом — как это делает сайт
    from playerokapi import graphql_queries as gq
    q = getattr(gq, "VIEWER", None) or getattr(gq, "viewer", None)
    print("viewer query const:", "найдена" if q else "НЕ найдена")

    # chats / deals / items / reviews — сырые (variables как в публичных методах)
    dump("chats", acc._persisted_query("userChats", {
        "pagination": {"first": 3}, "filter": {"userId": acc.id}, "hasSupportAccess": False}))
    dump("deals", acc._persisted_query("deals", {
        "pagination": {"first": 3}, "filter": {"userId": acc.id}, "showForbiddenImage": True}))
    try:
        dump("reviews", acc._persisted_query("testimonials", {
            "pagination": {"first": 3}, "filter": {"userId": acc.id}}))
    except Exception as e:
        print(f"testimonials: {type(e).__name__}: {e}")
    # items — через публичный метод сложно достать сырой ответ, делаем запрос напрямую
    try:
        from playerokapi import parser as _p  # noqa: F401
        dump("items", acc._query("items", {
            "pagination": {"first": 3},
            "filter": {"userId": acc.id},
            "showForbiddenImage": True}, idempotent=True))
    except Exception as e:
        print(f"items: {type(e).__name__}: {e}")

    # transactions / countDeals — 403, подтверждаем и сохраняем тело ошибки
    for op, var in [("transactions", {"pagination": {"first": 3}}), ("countDeals", {"filter": {}})]:
        try:
            dump(op, acc._query(op, var, idempotent=True))
        except Exception as e:
            print(f"{op}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
