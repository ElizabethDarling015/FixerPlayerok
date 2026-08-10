"""
Живая диагностика библиотеки на реальном аккаунте Playerok — **только чтение**, никаких мутаций:
ничего не отправляет в чаты, не меняет лоты и сделки, не тратит баланс.

Запуск:
1. Вставьте cookies своего аккаунта в переменную `COOKIES` ниже.
2. `python examples/smoke_check.py`

Скрипт по шагам проверяет HTTP-запросы (авторизация, чаты, сообщения, сделки, лоты, отзывы)
и WebSocket-подписку, печатает `OK`/`FAIL` по каждому шагу и итоговую сводку. Код выхода 0 —
все проверки прошли, 1 — есть провалы. Если сервер перестал узнавать persisted-хэш какого-то
запроса (`PersistedQueryNotFoundError`) — это будет видно в выводе конкретного шага.
"""
import json
import logging
import sys
import time

import websocket

from playerokapi.account import Account
from playerokapi.common.exceptions import PersistedQueryNotFoundError
from playerokapi.graphql_queries import QUERIES
from playerokapi.updater.runner import _WS_ORIGIN, _WS_SUBPROTOCOL, _WS_URL

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

COOKIES = "token=...; __ddg5_=..."  # cookies авторизованного аккаунта Playerok
USER_AGENT = None  # желательно указать User-Agent браузера, из которого сняты cookies
PROXY = None  # прокси в формате curl_cffi, например "http://user:pass@host:port"

# Сколько секунд слушать WS после подписки (за это время сервер успеет прислать error, если подписка кривая).
WS_LISTEN_SECONDS = 5


def check_ws(account: Account) -> str:
    """Рукопожатие graphql-transport-ws + подписка chatUpdated; слушаем несколько секунд."""
    headers = [
        f"Cookie: {account._cookie_header()}",
        f"User-Agent: {account.user_agent}",
    ]
    ws = websocket.create_connection(
        _WS_URL, header=headers, origin=_WS_ORIGIN, subprotocols=[_WS_SUBPROTOCOL], timeout=10,
    )
    try:
        ws.send(json.dumps({
            "type": "connection_init",
            "payload": {"x-gql-op": "ws-subscription", "x-timezone-offset": time.timezone // 60},
        }))
        deadline = time.monotonic() + 10
        while True:
            if time.monotonic() > deadline:
                raise ConnectionError("нет connection_ack за 10 секунд")
            message = json.loads(ws.recv())
            if message.get("type") == "connection_ack":
                break
            if message.get("type") == "ping":
                ws.send(json.dumps({"type": "pong"}))

        ws.send(json.dumps({
            "id": "smoke-1",
            "type": "subscribe",
            "payload": {
                "variables": {"filter": {"userId": account.id}, "showForbiddenImage": True},
                "extensions": {},
                "operationName": "chatUpdated",
                "query": QUERIES["chatUpdated"],
            },
        }))

        frames = 0
        ws.settimeout(1)
        listen_until = time.monotonic() + WS_LISTEN_SECONDS
        while time.monotonic() < listen_until:
            try:
                raw = ws.recv()
            except Exception:
                continue  # таймаут чтения — тишина в эфире, это нормально
            if not raw:
                continue
            message = json.loads(raw)
            message_type = message.get("type")
            if message_type == "error":
                raise ConnectionError(f"сервер отверг подписку: {message.get('payload')}")
            if message_type == "ping":
                ws.send(json.dumps({"type": "pong"}))
            frames += 1
        return f"ack получен, подписка принята, кадров за {WS_LISTEN_SECONDS} c: {frames}"
    finally:
        try:
            ws.close()
        except Exception:
            pass


def main() -> int:
    if "token=..." in COOKIES or "token=" not in COOKIES:
        print("Заполните переменную COOKIES в начале этого файла — проверка невозможна.")
        return 1

    account = Account(cookies=COOKIES, user_agent=USER_AGENT, proxy=PROXY)
    results: list[tuple[str, bool, str]] = []

    def run_check(name: str, func) -> None:
        try:
            detail = func() or ""
            ok = True
        except PersistedQueryNotFoundError as exc:
            detail, ok = f"устарел persisted-хэш: {exc}", False
        except Exception as exc:
            detail, ok = f"{type(exc).__name__}: {exc}", False
        results.append((name, ok, detail))
        print(f"[{'OK' if ok else 'FAIL':>4}] {name}" + (f" — {detail}" if detail else ""))

    def check_auth() -> str:
        account.get()
        balance = account.profile.balance.value if account.profile and account.profile.balance else "?"
        return f"вошли как {account.username}, баланс: {balance}"

    def check_chats() -> str:
        page = account.get_chats(count=5)
        chats = page.chats if page else []
        if chats:
            main.first_chat_id = chats[0].id
        return f"чатов на первой странице: {len(chats)}"

    def check_messages() -> str:
        chat_id = getattr(main, "first_chat_id", None)
        if not chat_id:
            return "пропущено — нет ни одного чата"
        page = account.get_chat_messages(chat_id, count=5)
        messages = page.messages if page else []
        return f"сообщений в чате {chat_id}: {len(messages)}"

    def check_deals() -> str:
        page = account.get_deals(count=5)
        deals = page.deals if page else []
        statuses = ", ".join(str(d.raw_status.name) for d in deals if d.raw_status) or "—"
        return f"сделок на первой странице: {len(deals)} (статусы: {statuses})"

    def check_items() -> str:
        page = account.get_my_items(count=5)
        items = page.items if page else []
        return f"лотов на первой странице: {len(items)}"

    def check_reviews() -> str:
        page = account.get_my_reviews(count=5)
        reviews = page.reviews if page else []
        return f"отзывов на первой странице: {len(reviews)}"

    run_check("Авторизация (Account.get)", check_auth)
    if not results[0][1]:
        print("\nАвторизация не прошла — остальные проверки не имеют смысла. Проверьте cookies в COOKIES.")
        return 1

    run_check("Чаты (get_chats)", check_chats)
    run_check("Сообщения чата (get_chat_messages)", check_messages)
    run_check("Сделки (get_deals)", check_deals)
    run_check("Лоты (get_my_items)", check_items)
    run_check("Отзывы (get_my_reviews)", check_reviews)
    run_check("WebSocket-подписка (chatUpdated)", lambda: check_ws(account))

    failed = [name for name, ok, _ in results if not ok]
    print()
    if failed:
        print(f"Итог: {len(results) - len(failed)}/{len(results)} проверок прошло. Провалились: {', '.join(failed)}")
        return 1
    print(f"Итог: все {len(results)} проверок прошли — библиотека совместима с текущим API Playerok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
