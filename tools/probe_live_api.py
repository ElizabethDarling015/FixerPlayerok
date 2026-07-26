"""Read-only диагностика playerokapi против живого API.

Читает cookies из storage/probe_token.txt (Netscape-формат, частично битый),
прогоняет основные GET-операции Account и складывает сырые ответы в storage/probe/.
Ничего не меняет на аккаунте.
"""
import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playerokapi.account import Account  # noqa: E402

OUT = ROOT / "storage" / "probe"
OUT.mkdir(parents=True, exist_ok=True)

JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def load_cookies(path: Path) -> dict:
    cookies: dict[str, str] = {}
    pending_name: str | None = None  # имя куки с пустым значением, ждущее orphan-строку
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 7:
            name, value = parts[5], parts[6]
            if value:
                cookies[name] = value
                pending_name = None
            else:
                pending_name = name  # значение, видимо, на следующей строке
        elif len(parts) == 1:
            orphan = parts[0].strip()
            if JWT_RE.fullmatch(orphan) and "token" not in cookies:
                cookies["token"] = orphan
            elif pending_name:
                cookies[pending_name] = orphan
                pending_name = None
    return cookies


def dump(name: str, data) -> None:
    (OUT / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str)
    )


def probe(label: str, fn) -> None:
    print(f"\n=== {label} ===")
    try:
        result = fn()
        if result is None:
            print("-> None (тихий провал?)")
            return
        if hasattr(result, "__dict__"):
            keys = list(vars(result).keys())
            print(f"-> {type(result).__name__}, поля: {keys}")
        else:
            print(f"-> {type(result).__name__}: {str(result)[:300]}")
    except Exception as e:
        print(f"-> ИСКЛЮЧЕНИЕ: {type(e).__name__}: {e}")
        traceback.print_exc()


def main() -> None:
    cookies = load_cookies(ROOT / "storage" / "probe_token.txt")
    print(f"Загружено кук: {len(cookies)}: {sorted(cookies)}")
    assert "token" in cookies, "token не найден!"

    acc = Account(cookies=cookies)

    probe("get() — профиль аккаунта", lambda: acc.get())
    print(f"   id={acc.id} username={acc.username}")
    if acc.profile:
        dump("profile", vars(acc.profile))

    probe("get_balance()", lambda: acc.get_balance())
    if acc.profile is None:
        print("!! профиль не загрузился — дальше бессмысленно")
        return

    probe("get_chats()", lambda: acc.get_chats(count=5))
    probe("get_deals()", lambda: acc.get_deals(count=5))
    probe("get_my_items()", lambda: acc.get_my_items(count=5))
    probe("get_my_reviews()", lambda: acc.get_my_reviews(count=5))
    probe("get_transactions()", lambda: acc.get_transactions(count=5))
    probe("get_games()", lambda: acc.get_games(count=5))
    probe("count_deals()", lambda: acc.count_deals())
    probe("count_chats()", lambda: acc.count_chats())

    # Сырой GraphQL-ответ для ручной сверки со схемой в коде
    print("\n=== сырые ответы сохранены в storage/probe/ ===")


if __name__ == "__main__":
    main()
