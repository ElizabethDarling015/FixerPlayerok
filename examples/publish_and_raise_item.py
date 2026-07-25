"""
Пример полного цикла работы с лотом: создание черновика -> публикация -> поднятие приоритета.

Перед запуском вставьте cookies своего аккаунта в переменную `COOKIES` ниже, а также подставьте
реальные `GAME_SLUG` и `CATEGORY_SLUG` под нужную вам игру/категорию (посмотреть их можно в URL
страницы категории на сайте).
"""
from playerokapi.account import Account

COOKIES = "token=...; __ddg5_=..."  # cookies авторизованного аккаунта Playerok
GAME_SLUG = "steam"
CATEGORY_SLUG = "steam-accounts"


def main() -> None:
    account = Account(cookies=COOKIES).get()

    game = account.get_game(slug=GAME_SLUG)
    if not game:
        raise SystemExit(f"Игра со slug={GAME_SLUG!r} не найдена")

    category = account.get_game_category(game_id=game.id, slug=CATEGORY_SLUG)
    if not category:
        raise SystemExit(f"Категория со slug={CATEGORY_SLUG!r} не найдена")
    print(f"Игра: {game.name}, категория: {category.name}")

    obtaining_types = account.get_game_category_obtaining_types(category.id)
    obtaining_type_id = obtaining_types.obtaining_types[0].id if obtaining_types and obtaining_types.obtaining_types else None

    data_fields_page = account.get_game_category_data_fields(category.id, obtaining_type_id=obtaining_type_id)
    data_fields = {}
    if data_fields_page:
        for field in data_fields_page.data_fields:
            if field.type is not None and field.type.name == "ITEM_DATA":
                data_fields[field.id] = "Пример значения"

    item = account.create_item(
        game_id=game.id,
        category_id=category.id,
        name="Тестовый лот (создан через playerokapi)",
        price=100,
        description="Описание тестового лота.",
        obtaining_type_id=obtaining_type_id,
        data_fields=data_fields or None,
    )
    print(f"Создан черновик лота: {item.id} ({item.name})")

    priority_statuses = account.get_item_priority_statuses(item.id, price=item.price)
    default_status = next((s for s in priority_statuses if s.type is not None and s.type.name == "DEFAULT"), None)

    published = account.publish_item(item.id, priority_status_id=default_status.id if default_status else None)
    print(f"Лот опубликован, статус: {published.status}")

    premium_status = next((s for s in priority_statuses if s.type is not None and s.type.name == "PREMIUM"), None)
    if premium_status:
        raised = account.increase_item_priority_status(item.id, priority_status_id=premium_status.id)
        print(f"Лот поднят, приоритет: {raised.priority}")
    else:
        print("Платный статус приоритета не найден для этой категории/цены — пропускаем поднятие.")


if __name__ == "__main__":
    main()
