<div align="center">

<img src="assets/banner.png" alt="FIXER PLAYEROK" width="720">

# FixerPlayerok

Бот-помощник для продавцов [Playerok](https://playerok.com): автовыдача, уведомления о сделках
и переписка с покупателями — всё из Telegram.

---

![status](https://img.shields.io/badge/status-beta-orange)
![stack](https://img.shields.io/badge/stack-Python%20%C2%B7%20aiogram%20%C2%B7%20Playerok-blue)
![license](https://img.shields.io/badge/license-MIT-blue)

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.7%2B-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-BOT-26A5E0?style=for-the-badge&logo=telegram&logoColor=white)

![stars](https://img.shields.io/github/stars/ElizabethDarling015/FixerPlayerok)
![forks](https://img.shields.io/github/forks/ElizabethDarling015/FixerPlayerok)
![last commit](https://img.shields.io/github/last-commit/ElizabethDarling015/FixerPlayerok)

</div>

> Неофициальный проект. Не аффилирован с Playerok и не связан с администрацией площадки.
> Статус: **beta**.

## Содержание

- [Возможности](#возможности)
- [Установка](#установка)
  - [Cookies / token Playerok](#cookies--token-playerok)
  - [Linux / macOS](#linux--macos)
  - [Windows](#windows)
- [Команды запуска](#команды-запуска)
- [Автозапуск (systemd)](#автозапуск-systemd)
- [Обновление](#обновление)
- [Где что лежит](#где-что-лежит)
- [FAQ](#faq)
- [Лицензия](#лицензия)

## Возможности

**Playerok**

- Автовыдача товаров из файлов-складов: при сбое отправки позиция возвращается на склад,
  повторная выдача по одной сделке исключена (журнал в SQLite).
- Автоподнятие лотов по таймеру.
- Автовосстановление лотов после продажи.
- Вечный онлайн.
- Чёрный список покупателей.

**Telegram**

- Панель `/menu`: статус и баланс, чаты с покупателями, статистика, сводка по запросу,
  автовыдача, автоответчик, чёрный список, уведомления, логи, бэкап, прокси,
  обновление с GitHub.
- Чаты с покупателями: история переписки, живой диалог (текст и фото уходят покупателю),
  быстрые шаблоны — `!!команда` подставляет заготовленный ответ из автоответчика
  (переменные `$username`, `$chat_id`, `$date`, `$time`).
- Уведомления о сделках, оплате, выдаче, сообщениях, отзывах, проблемах в сделках,
  ошибках, пустом складе и покупках из чёрного списка; ответ покупателю — reply на уведомление.
- Ежедневная сводка: продажи, выручка, баланс, остатки складов.
- Бэкап конфигов и данных одним zip-архивом.

## Установка

Нужен **Python 3.11+** (на Linux скрипт поставит его сам).

### Cookies / token Playerok

1. Откройте [playerok.com](https://playerok.com) и войдите в аккаунт.
2. DevTools (F12) → Network → любой запрос к `playerok.com`.
3. Скопируйте заголовок **Cookie** целиком (минимум — значение куки `token`, JWT вида `eyJ...`).
4. Вставьте в мастер настройки при первом запуске (или в `configs/main.toml`, `[playerok]` → `cookies`).

Если бот ловит антибот-проверку (`BotCheckDetectedException`) — возьмите свежие cookies
вместе с `__ddg5_` из браузера на том же IP, с которого работает бот.

### Linux / macOS

```bash
git clone https://github.com/ElizabethDarling015/FixerPlayerok.git
cd FixerPlayerok
./fixer.sh
```

При первом запуске скрипт создаст виртуальное окружение, поставит зависимости и проведёт
мастер настройки (cookies, Telegram-бот, админы, модули). Ставьте через `git clone`, а не
архивом — так обновления приходят чисто.

### Windows

1. Установите [Python 3.11+](https://www.python.org/downloads/) с галочкой **Add python.exe to PATH**.
2. Скачайте репозиторий и запустите `Fixer.bat`.

## Команды запуска

| Команда | Что делает |
|---|---|
| `./fixer.sh` | установка (при первом запуске), настройка и запуск бота |
| `./fixer.sh --setup` | заново пройти мастер настройки (перезапишет `configs/main.toml`) |
| `./fixer.sh --check` | проверить token и авторизацию на Playerok, бота не запускает |
| `./fixer.sh --update` | обновить код с GitHub и зависимости |
| `./fixer.sh --install-service` | установить systemd-сервис `FixerPlayerok` и запустить его |
| `./fixer.sh --remove-service` | остановить и удалить сервис |
| `./fixer.sh --offline` | запуск без подключения к Playerok API — для тестов; действует только на этот запуск |
| `./fixer.sh --proxyN` | Telegram-сессия через N-й сохранённый прокси, разово (на чёрный день, когда без прокси Telegram недоступен) |
| `./fixer.sh --add-proxy=URL` | добавить прокси без запуска бота (`socks5://user:pass@host:port` и т.п.) |

Скрипт рассчитан на bash; `sh fixer.sh` тоже работает — он сам перезапустится под bash.

## Автозапуск (systemd)

```bash
./fixer.sh --install-service
```

Без `sudo` — пароль скрипт спросит сам. Сервис создаётся под текущего пользователя и папку проекта:
`/etc/systemd/system/FixerPlayerok.service`. Если на машине есть `sing-box.service`,
бот стартует после него. Старый сервис `PlayerokCardinal` при установке будет найден и удалён.

```bash
sudo systemctl status FixerPlayerok     # статус
sudo systemctl restart FixerPlayerok    # перезапуск
journalctl -u FixerPlayerok -f          # логи
```

## Обновление

- Из Telegram: `/menu` → ⚙️ Настройки → ⬇️ Обновить с GitHub — скачает новую версию и перезапустит бота.
- С сервера: `./fixer.sh --update` — если работает сервис, скрипт остановит его на время обновления
  и запустит обратно.

`configs/`, `storage/` и свои файлы в `plugins/` при обновлении не затрагиваются.

## Где что лежит

| Путь | Что там |
|---|---|
| `configs/main.toml` | cookies, токен Telegram-бота, админы, модули |
| `configs/autoresponse.toml` | шаблоны ответов (`!!команда` в живом диалоге) |
| `configs/autodelivery.toml` | лоты автовыдачи |
| `configs/blacklist.toml` | чёрный список |
| `storage/` | склады, базы, журнал выдач, прокси |
| `storage/logs/fixer.log` | лог бота |

Кнопка «💾 Бэкап» в настройках присылает zip с `configs/` и `storage/` (без логов).
Внутри cookies и токен — не пересылайте архив никому.

## FAQ

**BotCheckDetectedException / антибот**
Свежие cookies (включая `__ddg5_`) из браузера на том же IP, что и бот. Не запускайте две копии
бота с одним аккаунтом с разных IP. Проверка: `./fixer.sh --check`.

**Token «обрезался» / 500 при авторизации**
Token — JWT из трёх частей через точку; мастер предупредит, если строка обрезана или просрочена.

**macOS: ошибка curl_cffi / symbol not found**
Зависимости ограничивают `curl_cffi<0.10`. При проблеме: `pip install "curl_cffi==0.7.4"`.

**Бот в Telegram не отвечает**
Проверьте токен бота и ID админов; при пустом списке админов отправьте боту код из консоли.

## Лицензия

MIT — см. [`LICENSE`](LICENSE). Проект вырос из PlayerokCardinal (scwee), исходный копирайт сохранён.
