"""
Мастер первичной настройки Cardinal (rich): запускается автоматически при первом старте,
когда `configs/main.toml` ещё не существует.

Спрашивает cookies Playerok, токен Telegram-бота, ID администраторов и включаемые модули;
создаёт `configs/main.toml`, пустые `autoresponse.toml`/`autodelivery.toml` с примерами
и папки `storage/`.
"""
from __future__ import annotations

import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .settings import (
    AUTODELIVERY_CONFIG,
    AUTORESPONSE_CONFIG,
    CONFIG_DIR,
    MAIN_CONFIG,
    STORAGE_DIR,
    MainSettings,
    save_main_settings,
)
from .toml_utils import write_toml

console = Console()


def normalize_cookies(raw: str) -> str | None:
    """
    Приводит ввод пользователя к строке cookies.

    Принимает и полную строку cookies (с `token=...`), и голое значение токена
    (обычно JWT `eyJ...`) — тогда оборачивает его в `token=<значение>`.

    :return: Строка cookies, либо `None`, если ввод не похож ни на то, ни на другое.
    """
    raw = raw.strip()
    if "token=" in raw:
        return raw
    if raw and "=" not in raw and ";" not in raw:
        return f"token={raw}"
    return None


def check_token(cookies: str) -> str | None:
    """
    Локальная проверка токена из cookies (без обращения к сети).

    Токен Playerok — это JWT: три base64url-части через точку. Обрезанный при вставке
    токен сервер встречает ошибкой 500, поэтому ловим проблему заранее.

    :return: Текст предупреждения, либо `None`, если токен выглядит нормально.
    """
    import base64
    import json
    import time

    token = next((part.split("=", 1)[1].strip() for part in cookies.split(";")
                  if part.strip().startswith("token=")), "")
    parts = token.split(".")
    if len(parts) != 3:
        return (f"token не похож на JWT (частей: {len(parts)} вместо 3, длина: {len(token)}) — "
                "похоже, он вставился не целиком")
    try:
        payload_raw = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_raw))
    except Exception:
        return "не удалось расшифровать token — возможно, он повреждён"
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        return "token просрочен — зайдите на playerok.com и скопируйте свежий"
    return None


def _ask_admin_ids() -> list[int]:
    raw = Prompt.ask(
        "[bold]ID администраторов Telegram[/] (через запятую; пусто — привязка кодом при первом сообщении боту)",
        default="",
        show_default=False,
    )
    admin_ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            admin_ids.append(int(part))
    return admin_ids


def run_first_setup() -> MainSettings:
    """Проводит интерактивную настройку и возвращает готовые настройки (файлы уже записаны)."""
    console.print(Panel.fit(
        "[bold cyan]🐦 PlayerokCardinal — первичная настройка[/]\n"
        "Ответьте на несколько вопросов — конфиги будут созданы автоматически.\n"
        f"Потом всё можно поменять в файлах папки [bold]{CONFIG_DIR}/[/] или через Telegram-панель.",
        border_style="cyan",
    ))

    # --- Playerok ---
    console.print("\n[bold]1. Аккаунт Playerok[/]")
    console.print("Cookies можно скопировать из браузера: DevTools → Network → любой запрос к playerok.com → "
                  "заголовок Cookie. Можно вставить и просто значение куки token (eyJ...) без 'token='.")
    while True:
        cookies = normalize_cookies(Prompt.ask("[bold]Cookies или значение token[/]"))
        if cookies is None:
            console.print("[red]Не похоже ни на cookies с 'token=', ни на значение токена — попробуйте ещё раз.[/]")
            continue
        warning = check_token(cookies)
        if warning is None:
            break
        console.print(f"[yellow]Проверка токена: {warning}[/]")
        if Confirm.ask("Использовать этот token всё равно?", default=False):
            break
    if "__ddg5_" not in cookies:
        console.print("[yellow]Куки __ddg5_ нет — пробуем без неё (обычно хватает имитации Chrome). "
                      "Если появится BotCheckDetectedException — добавьте её из браузера.[/]")
    user_agent = Prompt.ask("[bold]User-Agent браузера[/] (пусто — стандартный Chrome)", default="",
                            show_default=False).strip() or None
    proxy = Prompt.ask("[bold]Прокси[/] (формат http://user:pass@host:port; пусто — без прокси)", default="",
                       show_default=False).strip() or None

    # --- Telegram ---
    console.print("\n[bold]2. Telegram-бот[/] (панель управления и уведомления)")
    console.print("Создайте бота у @BotFather и вставьте токен. Пусто — Cardinal будет работать без Telegram.")
    token = Prompt.ask("[bold]Токен бота[/]", default="", show_default=False).strip()
    admin_ids: list[int] = _ask_admin_ids() if token else []

    # --- Модули ---
    console.print("\n[bold]3. Модули[/] (всё можно переключить позже из Telegram)")
    modules = {
        "autodelivery": Confirm.ask("Авто-выдача товаров?", default=True),
        "autoresponse": Confirm.ask("Автоответчик на команды?", default=True),
        "greeting": Confirm.ask("Приветствие новых покупателей?", default=False),
        "autoraise": Confirm.ask("Автоподнятие лотов (тратит баланс!)?", default=False),
        "autorestore": Confirm.ask("Автовосстановление лотов после продажи?", default=False),
        "online": Confirm.ask("Вечный онлайн?", default=True),
        "digest": Confirm.ask("Ежедневная сводка в Telegram?", default=True),
    }

    language = Prompt.ask("[bold]Язык интерфейса[/]", choices=["ru", "en"], default="ru")

    settings = MainSettings.model_validate({
        "language": language,
        "playerok": {"cookies": cookies, "user_agent": user_agent, "proxy": proxy},
        "telegram": {"token": token, "admin_ids": admin_ids},
        "modules": modules,
    })

    # --- Запись файлов ---
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(os.path.join(STORAGE_DIR, "stock"), exist_ok=True)
    os.makedirs(os.path.join(STORAGE_DIR, "logs"), exist_ok=True)

    save_main_settings(settings, MAIN_CONFIG)
    if not os.path.isfile(AUTORESPONSE_CONFIG):
        write_toml(AUTORESPONSE_CONFIG, {"commands": {
            "!привет": "Привет, $username! Чем могу помочь?",
        }})
    if not os.path.isfile(AUTODELIVERY_CONFIG):
        write_toml(AUTODELIVERY_CONFIG, {"lots": {}})

    console.print(Panel.fit(
        f"[bold green]Готово![/] Конфиги созданы в папке [bold]{CONFIG_DIR}/[/].\n"
        f"Авто-выдача настраивается в [bold]{AUTODELIVERY_CONFIG}[/] или через Telegram-панель (/menu).",
        border_style="green",
    ))
    return settings
