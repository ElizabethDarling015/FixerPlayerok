# GraphQL regression tools

Скрипты для сверки операций библиотеки с актуальным бандлом [playerok.com](https://playerok.com).

## Порядок

```bash
# 1. Скачать JS-чанки (нужны cookies аккаунта)
python tools/graphql/collect_gql.py --cookies /path/to/cookies.txt

# 2. Пересчитать sha256Hash по алгоритму Apollo → graphql_collected.json
pip install 'graphql-core>=3.2'
python tools/graphql/build_hashes.py

# 3. Сравнить с PERSISTED_QUERIES / QUERIES
python tools/graphql/compare.py

# 4. (опционально) diff конкретного текста
python tools/graphql/diff_fulltext.py viewer createChatMessage
```

Cookies также можно передать через `PLAYEROK_COOKIES` (строка) или `PLAYEROK_COOKIES_FILE`.

## Зависимости

Входят в optional-extra `dev`:

```bash
pip install -e ".[dev]"
```
