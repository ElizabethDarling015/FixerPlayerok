# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Язык

Код, docstrings, комментарии, логи и сообщения пользователю — на русском. Новый код пишите так же.

## Команды

```bash
pip install -e ".[dev,cardinal]"   # установка со всеми зависимостями (бот + тесты)

python -m pytest                    # все тесты (testpaths=tests, asyncio_mode=auto)
python -m pytest tests/test_parser.py                 # один файл
python -m pytest tests/test_parser.py -k имя_теста    # один тест

python -m cardinal                  # запуск бота напрямую (нужен configs/main.toml,
                                    # иначе стартует интерактивный мастер first_setup)
./cardinal.sh                       # полный запуск Linux/macOS (venv + зависимости + настройка)
./cardinal.sh --check               # проверить token/авторизацию
./cardinal.sh --setup|--update|--upgrade|--service|--status|--logs
```

Линтер не настроен. Все тесты работают на моках без сети и реальных cookies — общие фейки в `tests/cardinal_helpers.py` (`FakeAccount`, `make_deal`, `make_page`, `drain_events`).

## Архитектура

Два слоя, оба — Python-пакеты (см. `pyproject.toml`):

**`playerokapi/`** — самостоятельная **синхронная** библиотека для playerok.com (GraphQL поверх curl_cffi, авторизация по cookie). Можно использовать без бота (`docs/library.md`, `examples/`).

- `account.py` — `Account`: клиент GraphQL, все запросы/мутации к площадке.
- `graphql_queries.py` — тексты GraphQL-запросов (~10k строк, собраны с фронтенда).
- `parser.py` — сырой JSON → датаклассы из `types.py`.
- `updater/runner.py` — `Runner.listen()`: поллинг чатов/сделок/отзывов, генерирует события из `updater/events.py` (`NewMessageEvent`, `NewDealEvent`, `ItemPaidEvent`, …).
- `autodelivery.py` + `delivery_ledger.py` — автовыдача из файлов-складов; дедуп по сделке в SQLite, при сбое отправки позиция возвращается на склад.
- `autoraise.py` — автоподнятие лотов по таймеру.
- `plugins.py` — `PluginManager`: хуки `PRE_<METHOD>`/`POST_<METHOD>`, оборачивающие методы `Account`; плагины из `plugins/` регистрируются через `bind()`.

**`cardinal/`** — бот PlayerokCardinal (asyncio + aiogram-панель в Telegram).

- `core.py` — класс `Cardinal`, мост между синхронной библиотекой и asyncio: `Runner.listen()` крутится в фоновом потоке и шлёт события в `asyncio.Queue` через `call_soon_threadsafe`; все вызовы `Account` из async-кода — через `asyncio.to_thread`. `_consume_events()` раздаёт события модулям и `Notifier`, ошибка одного не роняет остальных.
- `modules/` — модули бота (`autoresponse`, `greeting`, `autorestore`, `online`, `digest`, `autoupdate`): наследуют `BaseModule` (`on_start`/`on_event`/`on_stop`), собираются в `build_modules()`, включаются флагами `[modules]` в конфиге. Автовыдача/автоподнятие живут в библиотеке, а флаги уважают через обёртки `_ToggleableAutoDelivery`/`_ToggleableAutoRaise` в `core.py`.
- `tg/` — aiogram: хендлеры панели `/menu` в `tg/handlers/`, уведомления в `tg/notifications.py` (`Notifier`).
- `settings.py` — pydantic-модели; TOML-конфиги в `configs/`: `main.toml`, `autoresponse.toml`, `autodelivery.toml`, `blacklist.toml`. Последние три перечитываются на лету (`Cardinal.reload_configs()`).
- `locales/` (`ru`/`en`) + `localization.py` — строки интерфейса; новые тексты добавляйте в оба языка.
- Перезапуск из TG-панели: `request_restart()` ставит `restart_requested`, `main.py` перезапускает процесс.

## Живой API Playerok

- Интроспекция GraphQL на сервере закрыта; поля input-типов перечисляются через ошибки валидатора (пустой/лишний input). Живая схема может расходиться с `graphql_queries.py`.
- Read-only проверки против живого API — скрипты `tools/probe_live_api.py`, `verify_live_api.py`, `dump_raw_api.py` с cookies из `storage/probe_token.txt` (только query, без мутаций); дампы в `storage/probe/`. `storage/` в .gitignore.
- Антибот DDoS-Guard: при `BotCheckDetectedException` нужны полные cookies браузера (`__ddg5_` и т.п.) или прокси.
- curl_cffi зажат `<0.12`: в ≥0.10 убран `files=` — multipart собирается вручную (`Account._build_multipart`, порядок полей по graphql-multipart-request-spec); на macOS при проблемах ставится `curl_cffi==0.7.4`.
