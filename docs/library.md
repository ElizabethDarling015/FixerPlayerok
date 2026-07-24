# Библиотека playerokapi

Краткие примеры использования Python-пакета `playerokapi` (независим от бота PlayerokCardinal).
Больше сценариев — в папке [`examples/`](../examples/).

## Быстрый старт

```python
from playerokapi.account import Account
from playerokapi.updater.runner import Runner
from playerokapi.common.enums import EventTypes

cookies = "token=..."  # минимум — token; куки DDoS-Guard (__ddg5_ и т.п.) добавляйте,
                       # только если появится BotCheckDetectedException

account = Account(cookies=cookies).get()
print(f"Привет, {account.username}! Баланс: {account.profile.balance.value}")

runner = Runner(account)
for event in runner.listen():
    if event.type is EventTypes.NEW_MESSAGE:
        message = event.message
        if message.text and message.user.id != account.id:
            account.send_message(event.chat.id, "Привет! Это авто-ответ.")
    elif event.type is EventTypes.NEW_DEAL:
        print(f"Новая сделка: {event.deal.id}")
```

## Установка пакета

```bash
pip install -e .
# или только зависимости:
pip install -r requirements.txt
```

## Примеры в репозитории

- [`examples/smoke_check.py`](../examples/smoke_check.py) — диагностика на реальном аккаунте (чтение)
- [`examples/simple_bot.py`](../examples/simple_bot.py) — эхо по чатам и сделкам
- [`examples/autodelivery_bot.py`](../examples/autodelivery_bot.py) — авто-выдача из файла-склада
- [`examples/autoraise_bot.py`](../examples/autoraise_bot.py) — автоподнятие лотов
- [`examples/publish_and_raise_item.py`](../examples/publish_and_raise_item.py) — создать → опубликовать → поднять
- [`plugins/example_plugin.py`](../plugins/example_plugin.py) — заготовка плагина
