"""
Настройки Cardinal: pydantic-модели + TOML-файлы в папке `configs/`.

Три файла конфигурации:

- `configs/main.toml` — главный: cookies Playerok, Telegram-бот, переключатели модулей, интервалы.
- `configs/autoresponse.toml` — команды автоответчика (`[commands]`: команда = текст ответа).
- `configs/autodelivery.toml` — лоты авто-выдачи (`[lots."Название лота"]`: склад, восстановление).
- `configs/blacklist.toml` — чёрный список покупателей (`usernames = [...]`).

Ошибки валидации переводятся в человекочитаемый русский текст (`format_validation_error`).
"""
from __future__ import annotations

import os
import tomllib
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from .toml_utils import write_toml

#: Папки по умолчанию (относительно рабочей директории запуска).
CONFIG_DIR = "configs"
STORAGE_DIR = "storage"

MAIN_CONFIG = os.path.join(CONFIG_DIR, "main.toml")
AUTORESPONSE_CONFIG = os.path.join(CONFIG_DIR, "autoresponse.toml")
AUTODELIVERY_CONFIG = os.path.join(CONFIG_DIR, "autodelivery.toml")
BLACKLIST_CONFIG = os.path.join(CONFIG_DIR, "blacklist.toml")


# ----------------------------------------------------------------------
# Модели main.toml
# ----------------------------------------------------------------------

class PlayerokSettings(BaseModel):
    """Секция `[playerok]` — доступ к аккаунту Playerok."""

    cookies: str = Field(min_length=1)
    user_agent: str | None = None
    proxy: str | None = None
    requests_delay: float = Field(default=5.0, gt=0)
    requests_timeout: float = Field(default=30.0, gt=0)
    
    # НОВОЕ: режим разработки — бот работает только через Telegram, без подключения к Playerok API
    offline_mode: bool = False

    @field_validator("cookies")
    @classmethod
    def _cookies_must_contain_token(cls, value: str) -> str:
        if "token=" not in value:
            raise ValueError("в cookies не найден 'token=' — скопируйте cookies авторизованного аккаунта")
        return value


class TelegramSettings(BaseModel):
    """Секция `[telegram]` — управляющий Telegram-бот."""

    token: str = ""
    admin_ids: list[int] = Field(default_factory=list)


class ModulesSettings(BaseModel):
    """Секция `[modules]` — переключатели модулей Cardinal."""

    autodelivery: bool = True
    autoraise: bool = False
    autoresponse: bool = True
    autorestore: bool = False
    greeting: bool = False
    online: bool = True
    digest: bool = True


class AutoRaiseSettings(BaseModel):
    """Секция `[autoraise]` — параметры автоподнятия лотов."""

    interval: float = Field(default=4 * 60 * 60, gt=0)
    min_balance_reserve: int = Field(default=0, ge=0)


class AutoDeliverySettings(BaseModel):
    """Секция `[autodelivery]` — общие параметры авто-выдачи (лоты — в autodelivery.toml)."""

    delivery_text: str = "Спасибо за покупку! Вот ваш товар:\n{item}"
    ledger_file: str = os.path.join(STORAGE_DIR, "autodelivery_ledger.sqlite3")


class GreetingSettings(BaseModel):
    """Секция `[greeting]` — приветствие новых покупателей."""

    text: str = "Привет, $username! Я на связи — пишите, если есть вопросы по лоту."


class OnlineSettings(BaseModel):
    """Секция `[online]` — «вечный онлайн»."""

    interval: float = Field(default=300.0, gt=0)


class DigestSettings(BaseModel):
    """Секция `[digest]` — ежедневная сводка в Telegram."""

    time: str = "21:00"
    #: Часовой пояс продавца (IANA, например "Europe/Moscow"). Пустое значение —
    #: локальный пояс сервера; на UTC-сервере «день продаж» будет смещён.
    timezone: str | None = None

    @field_validator("time")
    @classmethod
    def _time_format(cls, value: str) -> str:
        parts = value.strip().split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts) \
                or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
            raise ValueError("время сводки должно быть в формате ЧЧ:ММ, например '21:00'")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"

    @field_validator("timezone")
    @classmethod
    def _timezone_must_exist(cls, value: str | None) -> str | None:
        if not value:
            return None
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(value)
        except Exception:
            raise ValueError(f"неизвестный часовой пояс {value!r} — используйте имя IANA, например 'Europe/Moscow'")
        return value


class NotificationsSettings(BaseModel):
    """Секция `[notifications]` — какие уведомления слать в Telegram."""

    new_deal: bool = True
    item_paid: bool = True
    delivery: bool = True
    new_message: bool = False
    new_review: bool = True
    deal_problem: bool = True
    deal_confirmed: bool = True
    deal_rolled_back: bool = True
    item_raised: bool = False
    insufficient_balance: bool = True
    errors: bool = True
    stock_empty: bool = True
    blacklist: bool = True


class MainSettings(BaseSettings):
    """Главный конфиг Cardinal (`configs/main.toml`)."""

    model_config = SettingsConfigDict(toml_file=MAIN_CONFIG, extra="ignore")

    language: str = "ru"
    playerok: PlayerokSettings
    telegram: TelegramSettings = TelegramSettings()
    modules: ModulesSettings = ModulesSettings()
    autoraise: AutoRaiseSettings = AutoRaiseSettings()
    autodelivery: AutoDeliverySettings = AutoDeliverySettings()
    greeting: GreetingSettings = GreetingSettings()
    online: OnlineSettings = OnlineSettings()
    digest: DigestSettings = DigestSettings()
    notifications: NotificationsSettings = NotificationsSettings()

    @field_validator("language")
    @classmethod
    def _language_supported(cls, value: str) -> str:
        if value not in ("ru", "en"):
            raise ValueError("поддерживаются языки 'ru' и 'en'")
        return value

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings: PydanticBaseSettingsSource,
                                   env_settings: PydanticBaseSettingsSource,
                                   dotenv_settings: PydanticBaseSettingsSource,
                                   file_secret_settings: PydanticBaseSettingsSource):
        # Приоритет: аргументы конструктора (тесты) > TOML-файл. env/.env не используем — решение
        # пользователя: конфигурация только файлами/кодом.
        return (init_settings, TomlConfigSettingsSource(settings_cls))


# ----------------------------------------------------------------------
# Модели autoresponse.toml / autodelivery.toml
# ----------------------------------------------------------------------

class AutoResponseConfig(BaseModel):
    """Конфиг автоответчика: `[commands]` — таблица `команда = текст ответа`."""

    commands: dict[str, str] = Field(default_factory=dict)

    @field_validator("commands")
    @classmethod
    def _commands_not_blank(cls, value: dict[str, str]) -> dict[str, str]:
        for command, response in value.items():
            if not command.strip():
                raise ValueError("пустая команда недопустима")
            if not response.strip():
                raise ValueError(f"у команды {command!r} пустой текст ответа")
        return value


class AutoDeliveryLot(BaseModel):
    """Один лот авто-выдачи (`[lots."Название"]` в autodelivery.toml)."""

    stock_file: str = Field(min_length=1)
    restore: bool = False
    deactivate_when_empty: bool = False


class AutoDeliveryConfig(BaseModel):
    """Конфиг авто-выдачи: `[lots]` — таблица `Название лота -> параметры`."""

    lots: dict[str, AutoDeliveryLot] = Field(default_factory=dict)


class BlacklistConfig(BaseModel):
    """Чёрный список покупателей: `usernames` — список ников Playerok (без учёта регистра)."""

    usernames: list[str] = Field(default_factory=list)

    @field_validator("usernames")
    @classmethod
    def _usernames_cleaned(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for username in value:
            username = username.strip()
            if username and username.casefold() not in (u.casefold() for u in cleaned):
                cleaned.append(username)
        return cleaned

    def contains(self, username: str | None) -> bool:
        """Проверяет, есть ли ник в чёрном списке (без учёта регистра)."""
        if not username:
            return False
        needle = username.strip().casefold()
        return any(u.casefold() == needle for u in self.usernames)


# ----------------------------------------------------------------------
# Загрузка / сохранение / ошибки
# ----------------------------------------------------------------------

class ConfigError(Exception):
    """Ошибка чтения или валидации конфига (сообщение уже человекочитаемое, на русском)."""


def format_validation_error(error: ValidationError, path: str) -> str:
    """Переводит pydantic `ValidationError` в понятный русский текст со списком полей."""
    problems = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"]) or "<корень>"
        message = issue["msg"]
        # Самые частые английские сообщения pydantic переводим на русский.
        translations = {
            "Field required": "обязательное поле отсутствует",
            "Input should be a valid string": "ожидается строка",
            "Input should be a valid integer": "ожидается целое число",
            "Input should be a valid number": "ожидается число",
            "Input should be a valid boolean": "ожидается true или false",
            "Input should be a valid list": "ожидается список",
            "Input should be a valid dictionary": "ожидается таблица (секция TOML)",
        }
        for eng, rus in translations.items():
            if message.startswith(eng):
                message = rus
                break
        message = message.removeprefix("Value error, ")
        problems.append(f"  - {location}: {message}")
    return f"Ошибка в конфиге {path}:\n" + "\n".join(problems)


def _read_toml(path: str) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Файл конфигурации не найден: {path}")
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Файл {path} — некорректный TOML: {exc}")


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _load_config(path: str, model_cls: type[_ModelT], *, missing_ok: bool) -> _ModelT:
    """
    Общая логика загрузки TOML-конфига: чтение → валидация pydantic → `ConfigError` по-русски.

    :param missing_ok: `True` — отсутствующий файл означает пустой конфиг (дефолты модели),
        `False` — отсутствие файла это ошибка (главный конфиг обязателен).
    """
    if missing_ok and not os.path.isfile(path):
        return model_cls()
    data = _read_toml(path)
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(format_validation_error(exc, path))


def _save_config(config: BaseModel, path: str, **dump_kwargs) -> None:
    """Общая логика сохранения конфига в TOML (с созданием папки)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    write_toml(path, config.model_dump(**dump_kwargs))


def load_main_settings(path: str = MAIN_CONFIG) -> MainSettings:
    """Загружает и валидирует главный конфиг. Бросает `ConfigError` с русским описанием проблемы."""
    return _load_config(path, MainSettings, missing_ok=False)


def load_autoresponse_config(path: str = AUTORESPONSE_CONFIG) -> AutoResponseConfig:
    """Загружает конфиг автоответчика (отсутствующий файл — это пустой конфиг, не ошибка)."""
    return _load_config(path, AutoResponseConfig, missing_ok=True)


def load_autodelivery_config(path: str = AUTODELIVERY_CONFIG) -> AutoDeliveryConfig:
    """Загружает конфиг авто-выдачи (отсутствующий файл — это пустой конфиг, не ошибка)."""
    return _load_config(path, AutoDeliveryConfig, missing_ok=True)


def load_blacklist_config(path: str = BLACKLIST_CONFIG) -> BlacklistConfig:
    """Загружает чёрный список покупателей (отсутствующий файл — это пустой список, не ошибка)."""
    return _load_config(path, BlacklistConfig, missing_ok=True)


def save_main_settings(settings: MainSettings, path: str = MAIN_CONFIG) -> None:
    """Сохраняет главный конфиг обратно в TOML (используется ПУ при переключении настроек)."""
    _save_config(settings, path, exclude_none=True)


def save_autoresponse_config(config: AutoResponseConfig, path: str = AUTORESPONSE_CONFIG) -> None:
    """Сохраняет конфиг автоответчика в TOML."""
    _save_config(config, path)


def save_autodelivery_config(config: AutoDeliveryConfig, path: str = AUTODELIVERY_CONFIG) -> None:
    """Сохраняет конфиг авто-выдачи в TOML."""
    _save_config(config, path)


def save_blacklist_config(config: BlacklistConfig, path: str = BLACKLIST_CONFIG) -> None:
    """Сохраняет чёрный список покупателей в TOML."""
    _save_config(config, path)
