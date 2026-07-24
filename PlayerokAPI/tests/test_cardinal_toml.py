"""Тесты TOML-сериализатора Cardinal (`cardinal.toml_utils`): round-trip через stdlib tomllib."""
import tomllib

import pytest

from cardinal.toml_utils import dumps_toml, write_toml


def roundtrip(data: dict) -> dict:
    return tomllib.loads(dumps_toml(data) + "\n")


def test_scalars_and_lists():
    data = {"name": "Cardinal", "count": 3, "ratio": 1.5, "enabled": True, "ids": [1, 2, 3]}
    assert roundtrip(data) == data


def test_nested_tables():
    data = {
        "language": "ru",
        "playerok": {"cookies": "token=abc", "requests_delay": 5.0},
        "modules": {"autodelivery": True, "greeting": False},
    }
    assert roundtrip(data) == data


def test_keys_with_spaces_and_unicode():
    # Ключи-названия лотов: кириллица, пробелы, кавычки — должны корректно экранироваться.
    data = {"lots": {"Аккаунт \"премиум\" 100 гемов": {"stock_file": "storage/stock/a.txt", "restore": True}}}
    assert roundtrip(data) == data


def test_string_escaping():
    data = {"text": 'Спасибо за покупку!\nВот товар: {item} и "кавычки"'}
    assert roundtrip(data) == data


def test_none_values_are_skipped():
    parsed = roundtrip({"a": 1, "b": None})
    assert parsed == {"a": 1}


def test_unsupported_type_raises():
    with pytest.raises(TypeError):
        dumps_toml({"bad": object()})


def test_write_toml(tmp_path):
    path = tmp_path / "cfg.toml"
    write_toml(str(path), {"section": {"key": "value"}})
    with open(path, "rb") as f:
        assert tomllib.load(f) == {"section": {"key": "value"}}
