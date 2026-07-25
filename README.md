<div align="center">

<img src="banner.png" alt="PLAYEROK CARDINAL" width="720">

# PlayerokCardinal

Бот для автоматизации продаж на [Playerok](https://playerok.com).


---

![status](https://img.shields.io/badge/status-beta-orange)
![stack](https://img.shields.io/badge/stack-Python%20%C2%B7%20aiogram%20%C2%B7%20Playerok-blue)
![license](https://img.shields.io/badge/license-MIT-blue)
![stars](https://img.shields.io/github/stars/scwee/PlayerokCardinal)
![forks](https://img.shields.io/github/forks/scwee/PlayerokCardinal)
![watchers](https://img.shields.io/github/watchers/scwee/PlayerokCardinal)
![visitors](https://api.visitorbadge.io/api/visitors?path=scwee%2FPlayerokCardinal&label=visitors&labelColor=%23555555&countColor=%23007ec6)

![PLAYEROK](https://img.shields.io/badge/PLAYEROK-BOT-brightgreen?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.7%2B-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-BOT-26A5E0?style=for-the-badge&logo=telegram&logoColor=white)

</div>

> Неофициальный проект. Не аффилирован с Playerok и не связан с администрацией площадки.
> Статус: **beta**.

## Содержание

- [Возможности](#возможности)
  - [Playerok](#playerok)
  - [Уведомления и ПУ в Telegram](#уведомления-и-пу-в-telegram)
  - [Дополнительные возможности](#дополнительные-возможности)
- [Преимущества](#преимущества)
  - [Для пользователей](#для-пользователей)
  - [Для разработчиков](#для-разработчиков)
- [Плагины](#плагины)
- [Установка](#установка)
  - [Cookies / token Playerok](#cookies--token-playerok)
  - [Windows](#windows)
  - [Linux / macOS](#linux--macos)
- [Установка плагинов](#установка-плагинов)
- [Помощь](#помощь)
- [FAQ](#faq)
- [Star it](#star-it)

## Возможности

### Playerok

- Автовыдача товаров из файлов-складов (безопасная: при сбое отправки позиция возвращается на склад; дедуп по сделке в SQLite).
- Автоподнятие лотов по таймеру.
- Автоответ на заготовленные `!команды` (переменные `$username`, `$chat_id`, `$date`, `$time`).
- Приветствие новых покупателей (с дедупом).
- Автовосстановление лотов после продажи (тот же приоритет DEFAULT/PREMIUM; при нехватке
  баланса на премиум — бесплатное выставление + предупреждение в Telegram).
- Вечный онлайн.
- Ежедневная сводка в Telegram (продажи, выручка, баланс, остатки складов).
- Чёрный список покупателей.
- Уведомления в Telegram и полноценная панель управления.

### Уведомления и ПУ в Telegram

- Панель `/menu`: статус, модули, автовыдача, автоответчик, чёрный список, уведомления, плагины, логи, бэкап, перезагрузка конфигов, перезапуск и выключение.
- Уведомления о сделках, оплате, выдаче (с остатком склада), сообщениях, отзывах, проблемах в сделках, поднятии лотов, нехватке баланса, ошибках, пустом складе и покупках из чёрного списка.
- Ответ на сообщения покупателя прямо из Telegram (reply на уведомление).
- Настройка автовыдачи и автоответчика из панели (в т.ч. пополнение склада текстом или `.txt`-файлом).

### Дополнительные возможности

- Переменные в текстах автоответа / приветствия / выдачи.
- Плагины без правки кода бота (папка `plugins/`).
- Бэкап конфигов и данных zip-архивом из Telegram.
- Автозапуск через systemd (`./cardinal.sh --service`, Linux).

## Преимущества

### Для пользователей

- Нужный продавцу функционал в одном боте: выдача, ответы, поднятие, онлайн, сводка, ПУ в Telegram.
- Установка одной командой: `./cardinal.sh` (Linux/macOS) или `Cardinal.bat` (Windows).
- Конфиги в TOML (`configs/`), логи с ротацией в `storage/logs/`.
- Плагины расширяют поведение под свои сценарии.
- Полное управление через Telegram после первичной настройки.

### Для разработчиков

- Python 3.11+, type-hints, pydantic-валидация конфигов, loguru.
- Плагины через хуки (`PluginManager`).
- Отдельный Python-пакет **playerokapi** (Account, Runner, события) — можно использовать без бота; примеры: [`docs/library.md`](docs/library.md).

## Плагины

Отдельного канала с плагинами нет. Кладёте свои `.py` в `plugins/` (см. [`plugins/example_plugin.py`](plugins/example_plugin.py)) или ставите файл через раздел «Плагины» в `/menu`.

**Важно:** не устанавливайте плагины из непроверенных источников. Через систему плагинов злоумышленник может получить полный доступ к устройству и аккаунту Playerok.

## Установка

Требуется **Python 3.11+**.

### Cookies / token Playerok

1. Откройте [playerok.com](https://playerok.com) и войдите в аккаунт.
2. DevTools (F12) → вкладка Network → любой запрос к `playerok.com`.
3. Скопируйте заголовок **Cookie** целиком (или хотя бы значение куки `token` — JWT вида `eyJ...`).
4. Вставьте в мастер настройки при первом запуске (или в `configs/main.toml`, секция `[playerok]`, поле `cookies`).

Обычно хватает `token=...`. Если появится `BotCheckDetectedException` — добавьте куки DDoS-Guard (например `__ddg5_`) из того же браузера или укажите прокси.

### Windows

1. Установите [Python 3.11+](https://www.python.org/downloads/) с галочкой **Add python.exe to PATH**.
2. Скачайте и распакуйте архив репозитория.
3. Запустите `Cardinal.bat` двойным кликом.
4. При первом запуске пройдите мастер настройки (cookies, Telegram-бот, админы, модули).

### Linux / macOS

Из корня репозитория:

```bash
chmod +x cardinal.sh
./cardinal.sh              # первый раз: Python (если нужно) + зависимости + настройка + запуск
./cardinal.sh --setup      # заново пройти настройку
./cardinal.sh --check      # проверить token и авторизацию
./cardinal.sh --update     # обновить зависимости
./cardinal.sh --service    # systemd-автозапуск (Linux)
```

Одной командой:

```bash
wget https://github.com/scwee/PlayerokCardinal/archive/refs/heads/main.tar.gz -O pc.tar.gz \
  && tar -xzf pc.tar.gz && cd PlayerokCardinal-main && chmod +x cardinal.sh && ./cardinal.sh
```

Либо, если уже клонировали репозиторий на сервер: `./cardinal.sh`.

Авторизация в Telegram-панели: ID администраторов в `configs/main.toml`, либо секретный код из консоли при старте.

## Установка плагинов

1. Положите файл `.py` в папку `plugins/` и перезапустите бота  
   **или** `/menu` → Плагины → добавить файл из Telegram.
2. Не ставьте плагины из неизвестных источников (см. предупреждение выше).

## Помощь

**Создатель** — [@Scwee_xz](https://t.me/Scwee_xz)

Telegram-чат поддержки появится позже. Пока смотрите [FAQ](#faq), логи в `storage/logs/cardinal.log` и раздел «Система» в `/menu`.

## FAQ

**Где взять cookies?**  
См. [Cookies / token Playerok](#cookies--token-playerok). В мастер можно вставить и голое значение `token` без префикса `token=`.

**BotCheckDetectedException / антибот**  
Добавьте полные cookies из браузера (в т.ч. `__ddg5_`) или прокси в `[playerok]` → `proxy`. Проверка: `./cardinal.sh --check`.

**Token «обрезался» / 500 при авторизации**  
Token — JWT из трёх частей через точку. Скопируйте его целиком; мастер предупредит, если строка похожа на обрезанную или просроченную.

**macOS: ошибка curl_cffi / symbol not found**  
Зависимости ограничивают `curl_cffi<0.10`. При проблеме: `pip install "curl_cffi==0.7.4"`.

**Бот в Telegram не отвечает**  
Проверьте токен бота и ID админов; при пустом списке админов отправьте боту код из консоли.

## Star it

Если PlayerokCardinal вам полезен — [поставьте звезду](https://github.com/scwee/PlayerokCardinal) репозиторию на GitHub (нужно быть авторизованным).

## Лицензия

MIT — см. [`LICENSE`](LICENSE).
