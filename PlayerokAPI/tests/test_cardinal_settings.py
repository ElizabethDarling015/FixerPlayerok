"""Тесты конфигов Cardinal (`cardinal.settings`): загрузка, валидация, русские ошибки, сохранение."""
import pytest

from cardinal.first_setup import check_token, normalize_cookies
from cardinal.settings import (
    AutoDeliveryConfig,
    AutoDeliveryLot,
    AutoResponseConfig,
    ConfigError,
    MainSettings,
    load_autodelivery_config,
    load_autoresponse_config,
    load_main_settings,
    save_autodelivery_config,
    save_autoresponse_config,
    save_main_settings,
)

VALID_MAIN = """
language = "ru"

[playerok]
cookies = "token=abc; __ddg5_=x"

[telegram]
token = "123:ABC"
admin_ids = [42]

[modules]
autoraise = true
"""


def test_load_main_settings_valid(tmp_path):
    path = tmp_path / "main.toml"
    path.write_text(VALID_MAIN, encoding="utf-8")
    settings = load_main_settings(str(path))
    assert settings.playerok.cookies.startswith("token=")
    assert settings.telegram.admin_ids == [42]
    assert settings.modules.autoraise is True
    assert settings.modules.autodelivery is True  # значение по умолчанию
    assert settings.notifications.item_paid is True


def test_load_main_settings_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="не найден"):
        load_main_settings(str(tmp_path / "nope.toml"))


def test_load_main_settings_broken_toml(tmp_path):
    path = tmp_path / "main.toml"
    path.write_text("[playerok\ncookies=", encoding="utf-8")
    with pytest.raises(ConfigError, match="некорректный TOML"):
        load_main_settings(str(path))


def test_load_main_settings_missing_cookies_russian_error(tmp_path):
    path = tmp_path / "main.toml"
    path.write_text("[playerok]\nuser_agent = \"x\"\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc_info:
        load_main_settings(str(path))
    message = str(exc_info.value)
    assert "playerok.cookies" in message
    assert "обязательное поле отсутствует" in message


def test_cookies_without_token_rejected(tmp_path):
    path = tmp_path / "main.toml"
    path.write_text("[playerok]\ncookies = \"session=abc\"\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="token"):
        load_main_settings(str(path))


def test_unsupported_language_rejected():
    with pytest.raises(Exception, match="ru.*en|поддерживаются"):
        MainSettings.model_validate({"language": "de", "playerok": {"cookies": "token=x"}})


def test_main_settings_roundtrip(tmp_path):
    settings = MainSettings.model_validate({
        "playerok": {"cookies": "token=abc"},
        "telegram": {"token": "1:B", "admin_ids": [1, 2]},
    })
    path = tmp_path / "main.toml"
    save_main_settings(settings, str(path))
    loaded = load_main_settings(str(path))
    assert loaded.model_dump() == settings.model_dump()


def test_autoresponse_missing_file_is_empty(tmp_path):
    config = load_autoresponse_config(str(tmp_path / "nope.toml"))
    assert config.commands == {}


def test_autoresponse_roundtrip(tmp_path):
    config = AutoResponseConfig(commands={"!привет": "Привет, $username!"})
    path = tmp_path / "ar.toml"
    save_autoresponse_config(config, str(path))
    assert load_autoresponse_config(str(path)).commands == config.commands


def test_autoresponse_blank_response_rejected(tmp_path):
    path = tmp_path / "ar.toml"
    path.write_text("[commands]\n\"!x\" = \"  \"\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="пустой текст ответа"):
        load_autoresponse_config(str(path))


def test_autodelivery_roundtrip(tmp_path):
    config = AutoDeliveryConfig(lots={
        "Лот с пробелами": AutoDeliveryLot(stock_file="storage/stock/a.txt", restore=True,
                                            deactivate_when_empty=True),
    })
    path = tmp_path / "ad.toml"
    save_autodelivery_config(config, str(path))
    loaded = load_autodelivery_config(str(path))
    assert loaded.lots["Лот с пробелами"].restore is True
    assert loaded.lots["Лот с пробелами"].deactivate_when_empty is True


def test_autodelivery_requires_stock_file(tmp_path):
    path = tmp_path / "ad.toml"
    path.write_text("[lots.\"Лот\"]\nrestore = true\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="stock_file"):
        load_autodelivery_config(str(path))


@pytest.mark.parametrize("raw,expected", [
    # Голое значение токена (JWT) — оборачивается в token=.
    ("eyJhbGciOiJIUzI1NiJ9.payload.signature", "token=eyJhbGciOiJIUzI1NiJ9.payload.signature"),
    ("  eyJhbGci.p.s  ", "token=eyJhbGci.p.s"),
    # Полная строка cookies — принимается как есть.
    ("token=eyJhbGci.p.s; __ddg5_=abc", "token=eyJhbGci.p.s; __ddg5_=abc"),
    ("  token=abc  ", "token=abc"),
    # Не похоже ни на что — None (мастер просит ещё раз).
    ("__ddg5_=abc; other=1", None),
    ("", None),
    ("   ", None),
])
def test_normalize_cookies(raw, expected):
    """Мастер настройки принимает и cookies, и голое значение токена (без 'token=')."""
    assert normalize_cookies(raw) == expected


def make_jwt(payload: dict) -> str:
    """Собирает фейковый JWT (подпись не проверяется — только структура и payload)."""
    import base64
    import json

    def encode(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode(payload)}.fakesignature"


def test_check_token_valid():
    import time
    token = make_jwt({"sub": "user-id", "exp": time.time() + 3600})
    assert check_token(f"token={token}; __ddg5_=x") is None


def test_check_token_without_exp_is_ok():
    assert check_token(f"token={make_jwt({'sub': 'user-id'})}") is None


def test_check_token_truncated():
    """Обрезанный при вставке токен (реальный кейс: Playerok отвечает на него HTTP 500)."""
    warning = check_token("token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIi")
    assert warning is not None and "не целиком" in warning


def test_check_token_garbage_payload():
    warning = check_token("token=abc.@@@не-base64@@@.signature")
    assert warning is not None and "повреждён" in warning


def test_check_token_expired():
    warning = check_token(f"token={make_jwt({'exp': 1000})}")
    assert warning is not None and "просрочен" in warning


def test_digest_timezone_valid_and_empty():
    from cardinal.settings import DigestSettings

    assert DigestSettings(timezone="Europe/Moscow").timezone == "Europe/Moscow"
    assert DigestSettings(timezone="").timezone is None
    assert DigestSettings().timezone is None


def test_digest_timezone_unknown_rejected():
    from pydantic import ValidationError

    from cardinal.settings import DigestSettings

    with pytest.raises(ValidationError, match="часовой пояс"):
        DigestSettings(timezone="Mars/Olympus")
