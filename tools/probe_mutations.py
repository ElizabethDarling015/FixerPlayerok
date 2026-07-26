"""Живой прогон мутаций playerokapi: создание черновика лота -> update -> удаление.

Cookies читаются из storage/live_cookies.json (JSON-экспорт браузера: список
объектов с полями name/value). Черновик НЕ публикуется и удаляется в конце —
на витрине аккаунта ничего не остаётся.
"""
import json
import struct
import sys
import traceback
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playerokapi.account import Account  # noqa: E402

COOKIES_FILE = ROOT / "storage" / "live_cookies.json"


def make_png(size: int = 64, rgb: tuple[int, int, int] = (60, 120, 200)) -> bytes:
    """Однотонный PNG size×size без внешних зависимостей (для категорий, требующих фото)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    row = b"\x00" + bytes(rgb) * size
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * size))
            + chunk(b"IEND", b""))


def load_cookies(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text())
    return {c["name"]: c["value"] for c in raw if c.get("value")}


def step(label: str, fn):
    print(f"\n=== {label} ===")
    try:
        result = fn()
        print(f"-> OK: {type(result).__name__}" if result is not None else "-> None")
        return result
    except Exception as e:
        print(f"-> FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


def main() -> None:
    cookies = load_cookies(COOKIES_FILE)
    print(f"Кук загружено: {len(cookies)} (token: {'да' if 'token' in cookies else 'НЕТ'})")

    acc = Account(cookies=cookies)
    step("get() — авторизация", acc.get)
    print(f"   username={acc.username} id={acc.id}")
    p = acc.profile
    if p:
        print(f"   balance={p.balance.value if p.balance else None} "
              f"can_publish_items={p.can_publish_items} "
              f"has_confirmed_phone_number={p.has_confirmed_phone_number} "
              f"is_funds_protection_active={p.is_funds_protection_active}")

    step("get_balance()", acc.get_balance)
    step("has_enabled_notifications()", acc.has_enabled_notifications)
    step("get_chats(5)", lambda: acc.get_chats(count=5))
    step("get_deals(5)", lambda: acc.get_deals(count=5))
    my_items = step("get_my_items(5)", lambda: acc.get_my_items(count=5))
    if my_items is not None:
        print(f"   лотов на аккаунте: {my_items.total_count}")

    # --- Мутации: черновик лота ---
    games = step("get_games(5)", lambda: acc.get_games(count=5))
    if not games or not games.games:
        print("!! Игры не получены — мутации пропущены")
        return
    game_brief = games.games[0]
    print(f"   первая игра: {game_brief.name} ({game_brief.slug})")

    game = step(f"get_game(slug={game_brief.slug!r})", lambda: acc.get_game(slug=game_brief.slug))
    categories = getattr(game, "categories", None) or []
    if not categories:
        print("!! У игры нет категорий — мутации пропущены")
        return
    category = categories[0]
    print(f"   категория: {category.name} ({category.slug})")

    obtaining = step("get_game_category_obtaining_types()",
                     lambda: acc.get_game_category_obtaining_types(category.id))
    obtaining_type_id = (obtaining.obtaining_types[0].id
                        if obtaining and obtaining.obtaining_types else None)

    fields_page = step("get_game_category_data_fields()",
                       lambda: acc.get_game_category_data_fields(category.id,
                                                                 obtaining_type_id=obtaining_type_id))
    data_fields = {}
    if fields_page:
        for field in fields_page.data_fields:
            if field.type is not None and field.type.name == "ITEM_DATA":
                data_fields[field.id] = "тест (черновик, будет удалён)"

    item = step("create_item() — черновик", lambda: acc.create_item(
        game_id=game.id,
        category_id=category.id,
        name="Тест playerokapi — черновик, будет удалён",
        price=99999,
        description="Технический черновик для проверки API. Не публикуется.",
        obtaining_type_id=obtaining_type_id,
        data_fields=data_fields or None,
        attachments=[make_png()],
    ))
    if item is None:
        print("!! Черновик не создан — update/remove пропущены")
        return
    print(f"   создан: id={item.id} name={item.name!r} status={item.status}")

    updated = step("update_item() — смена цены", lambda: acc.update_item(item.id, price=88888))
    if updated is not None:
        print(f"   цена после update: {updated.price}")

    removed = step("remove_item() — очистка", lambda: acc.remove_item(item.id))
    print(f"   удалён: {removed}")


if __name__ == "__main__":
    main()
