"""Вспомогательные функции общего назначения."""
from __future__ import annotations

import mimetypes
import os


def parse_cookies_string(cookies: str) -> dict[str, str]:
    """
    Парсит строку cookies формата `"token=abc; __ddg5_=def"` в словарь `{"token": "abc", "__ddg5_": "def"}`.

    :param cookies: Строка cookies (как её можно скопировать из браузера).
    :return: Словарь `{имя_cookie: значение}`.
    """
    result: dict[str, str] = {}
    for part in cookies.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        result[key.strip()] = value.strip()
    return result


_WS_SUPPORTED_SCHEMES = {"socks5", "socks5h", "socks4", "http", "https"}
_WS_DEFAULT_PORTS = {"socks5": 1080, "socks5h": 1080, "socks4": 1080, "http": 8080, "https": 443}


def parse_proxy_for_ws(proxy_url: str | None) -> dict:
    """
    Разбирает `proxy_url` (тот же формат, что принимает `Account(proxy=...)` для `curl_cffi`,
    например `"http://user:pass@host:port"` или `"socks5://host:port"`) в kwargs для
    `websocket.create_connection` (библиотека `websocket-client`): `http_proxy_host`,
    `http_proxy_port`, `http_proxy_auth`, `proxy_type`.

    Используется в `updater/runner.py`, чтобы WebSocket-подключение шло через тот же
    прокси, что и REST-запросы `Account` — иначе один и тот же аккаунт «светит» разными
    IP одновременно, что сильно повышает шанс словить антибот-блокировку.

    :return: Пустой словарь, если `proxy_url` не задан — тогда подключение идёт напрямую.
    """
    if not proxy_url:
        return {}
    from urllib.parse import urlsplit
    parts = urlsplit(proxy_url)
    scheme = (parts.scheme or "http").lower()
    if scheme not in _WS_SUPPORTED_SCHEMES:
        return {}
    # websocket-client принимает proxy_type: "http", "socks4", "socks5", "socks5h".
    ws_proxy_type = "http" if scheme in ("http", "https") else scheme
    kwargs: dict = {
        "http_proxy_host": parts.hostname,
        "http_proxy_port": parts.port or _WS_DEFAULT_PORTS.get(scheme, 1080),
        "proxy_type": ws_proxy_type,
    }
    if parts.username:
        kwargs["http_proxy_auth"] = (parts.username, parts.password or "")
    return kwargs


def resolve_image_file(image: str | bytes | bytearray) -> tuple[str, object, str]:
    """
    Готовит файл-приложение (изображение) для отправки в multipart-запросе.

    Принимает либо путь к файлу на диске, либо готовые байты изображения (тогда имя файла
    и MIME-тип определяются по сигнатуре первых байт).

    :param image: Путь к файлу или байты изображения.
    :return: Тройка `(имя_файла, файловый_объект_или_байты, mime_тип)`.
    """
    if isinstance(image, (bytes, bytearray)):
        sig = bytes(image[:12])
        if sig[:8] == b"\x89PNG\r\n\x1a\n":
            ext, content_type = "png", "image/png"
        elif sig[:3] == b"\xff\xd8\xff":
            ext, content_type = "jpg", "image/jpeg"
        elif sig[:6] in (b"GIF87a", b"GIF89a"):
            ext, content_type = "gif", "image/gif"
        elif sig[:4] == b"RIFF" and sig[8:12] == b"WEBP":
            ext, content_type = "webp", "image/webp"
        else:
            ext, content_type = "bin", "application/octet-stream"
        return f"image.{ext}", bytes(image), content_type

    filename = os.path.basename(image)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, open(image, "rb"), content_type
