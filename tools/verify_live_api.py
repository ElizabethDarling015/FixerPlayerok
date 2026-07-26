/"""Живая read-only сверка методов Account с API Playerok.

Прогоняет публичные read-only методы на пустом тестовом аккаунте и складывает
сырые ответы (data до парсинга) в storage/probe/raw_*.json для ручной сверки
со схемой в playerokapi/parser.py / types.py.

Ничего не меняет на аккаунте: только query-операции, никаких mutation/WS.
"""
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.probe_live_api import load_cookies, OUT  # noqa: E402
from playerokapi.account import Account  # noqa: E402

RESULTS: list[str] = []


def dump(name: str, data) -> None:
    (OUT / f"raw_{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str))


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "OK " if ok else "FAIL"
    line = f"[{mark}] {label}" + (f" — {detail}" if detail else "")
    RESULTS.append(line)
    print(line)


def check(label: str, fn, dump_name: str | None = None):
    """Выполняет вызов, печатает вердикт и (опционально) дампит сырой ответ."""
    try:
        raw, parsed = fn()
    except Exception as e:
        report(label, False, f"{type(e).__name__}: {str(e)[:200]}")
        traceback.print_exc()
        return None
    if dump_name is not None:
        dump(dump_name, raw)
    if parsed is None and raw:
        report(label, False, f"парсер вернул None при непустом raw ({list(raw)[:5]})")
        return None
    n = ""
    if parsed is not None and hasattr(parsed, "total_count"):
        n = f"total={parsed.total_count}"
    report(label, True, n or type(parsed).__name__)
    return parsed


def main() -> None:
    acc = Account(cookies=load_cookies(ROOT / "storage/probe_token.txt"))
    acc.get()
    print(f"Аккаунт: id={acc.id} username={acc.username}\n")

    # --- Финансы: транзакции (проблема №1 из диагностики) ---
    check("get_transactions()", lambda: (
        acc._query("transactions", {"pagination": {"first": 5}, "filter": {},
                                    "hasSupportAccess": False}, idempotent=True),
        acc.get_transactions(count=5)), dump_name="transactions")

    # --- Отзывы: testimonials (проблема №2) ---
    reviews = check("get_my_reviews() (testimonials)", lambda: (
        acc._persisted_query("testimonials", {"pagination": {"first": 5},
                                              "filter": {"userId": acc.id},
                                              "hasSupportAccess": False}),
        acc.get_my_reviews(count=5)), dump_name="reviews")

    # --- countDeals / countChats (проблема №3) ---
    try:
        n = acc.count_deals()
        report("count_deals()", True, f"count={n}")
    except Exception as e:
        report("count_deals()", False, f"{type(e).__name__}: {str(e)[:200]}")
    try:
        n = acc.count_chats()
        report("count_chats()", True, f"count={n}")
    except Exception as e:
        report("count_chats()", False, f"{type(e).__name__}: {str(e)[:200]}")

    # --- Чаты ---
    chats = check("get_chats()", lambda: (
        acc._persisted_query("userChats", {"pagination": {"first": 5},
                                           "filter": {"userId": acc.id},
                                           "hasSupportAccess": False}),
        acc.get_chats(count=5)), dump_name="chats")

    chat_id = chats.chats[0].id if chats and chats.chats else None
    if chat_id:
        check(f"get_chat({chat_id})", lambda: (
            acc._persisted_query("chat", {"id": chat_id, "hasSupportAccess": False}),
            acc.get_chat(chat_id)), dump_name="chat")
        check(f"get_chat_messages({chat_id})", lambda: (
            acc._persisted_query("chatMessages", {
                "pagination": {"first": 10}, "filter": {"chatId": chat_id},
                "hasSupportAccess": False, "showForbiddenImage": True}),
            acc.get_chat_messages(chat_id, count=10)), dump_name="chatMessages")
    else:
        report("get_chat()/get_chat_messages()", False, "нет чатов для проверки")

    # --- Сделки и лоты ---
    check("get_deals()", lambda: (
        acc._persisted_query("deals", {"pagination": {"first": 5},
                                       "filter": {"userId": acc.id},
                                       "showForbiddenImage": True}),
        acc.get_deals(count=5)), dump_name="deals")
    check("get_my_items()", lambda: (
        acc._persisted_query("items", {"pagination": {"first": 5},
                                       "filter": {"userId": acc.id},
                                       "showForbiddenImage": True}),
        acc.get_my_items(count=5)), dump_name="items")
    # get_item_priority_statuses — лотов нет (canPublishItems=false), пропускаем.
    report("get_item_priority_statuses()", True, "пропущено: на аккаунте нет лотов")

    # --- Пользователь ---
    check("get_user(id)", lambda: (
        acc._persisted_query("user", {"id": acc.id, "hasSupportAccess": False}),
        acc.get_user(id=acc.id)), dump_name="user")

    # --- Игры ---
    games = check("get_games()", lambda: (
        acc._persisted_query("games", {"pagination": {"first": 5}}),
        acc.get_games(count=5)), dump_name="games")
    game_id = None
    if games is not None:
        items = getattr(games, "games", None) or []
        if items:
            game_id = items[0].id
    if game_id:
        check(f"get_game({game_id})", lambda: (
            acc._persisted_query("GamePage", {"id": game_id}),
            acc.get_game(id=game_id)), dump_name="game")
    else:
        report("get_game()", False, "get_games() не вернул игр")

    print("\n=== ИТОГ ===")
    fails = [r for r in RESULTS if r.startswith("[FAIL]")]
    print(f"OK: {len(RESULTS) - len(fails)}, FAIL: {len(fails)}")
    for r in fails:
        print(" ", r)


if __name__ == "__main__":
    main()
