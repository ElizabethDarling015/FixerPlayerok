"""
Парсинг, сборка и проверка прокси для подключения Cardinal к Playerok.

В отличие от общего geo-чекера (как в Shinoa, где проверяется просто «прокси жив»),
здесь проверка идёт ПРЯМО на playerok.com/graphql теми же средствами, что использует
сам Account (curl_cffi с имитацией Chrome) — чтобы сразу поймать ситуацию, когда прокси
технически работает, но сам IP уже заблокирован DDoS-Guard (see BotCheckDetectedException).
curl_cffi поддерживает и http(s), и socks4/socks5 прокси нативно — второй HTTP-клиент
(aiohttp и т.п.) заводить не нужно.
"""
from __future__ import annotations

import logging
import time
from urllib.parse import quote, urlsplit

logger = logging.getLogger(__name__)

SUPPORTED_SCHEMES = {"socks5", "socks5h", "socks4", "http", "https"}
DEFAULT_PORTS = {"socks5": 1080, "socks5h": 1080, "socks4": 1080, "http": 8080, "https": 443}

# Те же сигнатуры, что и в playerokapi/account.py — если они всплыли при проверке
# через прокси, значит DDoS-Guard блокирует именно этот IP, а не сеть в принципе.
_BOT_CHECK_SIGNATURES = ("ddos-guard", "Ray ID", "cf-error-details", "Attention Required!")

_PLAYEROK_CHECK_URL = "https://playerok.com/graphql"
_GEO_URL = "http://ip-api.com/json?lang=en&fields=status,country,countryCode,city"


def parse_proxy_text(text: str, fallback_type: str = "http") -> dict | None:
    """
    Принимает форматы:
      socks5://user:pass@host:port, http://host:port, https://...
      host:port
      host:port:user:pass
    Возвращает dict(type, host, port, username, password) или None при некорректном вводе.
    """
    text = (text or "").strip()
    if not text:
        return None

    username = password = None

    if "://" in text:
        parts = urlsplit(text)
        scheme = (parts.scheme or "").lower()
        if scheme not in SUPPORTED_SCHEMES:
            return None
        host = parts.hostname
        port = parts.port or DEFAULT_PORTS.get(scheme)
        username = parts.username
        password = parts.password
    else:
        pieces = [p.strip() for p in text.split(":")]
        if len(pieces) == 2:
            host, port = pieces
        elif len(pieces) == 3:
            host, port, username = pieces
        elif len(pieces) >= 4:
            host, port, username = pieces[0], pieces[1], pieces[2]
            password = ":".join(pieces[3:])
        else:
            return None
        scheme = fallback_type

    if not host:
        return None
    try:
        port = int(port)
    except (TypeError, ValueError):
        return None
    if not (1 <= port <= 65535):
        return None

    return {
        "type": scheme,
        "host": host,
        "port": port,
        "username": username or None,
        "password": password or None,
    }


def build_proxy_url(p: dict) -> str:
    """Собирает каноничный URL прокси из словаря (proxy_type или type — оба поддерживаются)."""
    auth = ""
    if p.get("username"):
        auth = quote(p["username"], safe="")
        if p.get("password"):
            auth += ":" + quote(p["password"], safe="")
        auth += "@"
    ptype = p.get("proxy_type") or p.get("type")
    return f"{ptype}://{auth}{p['host']}:{p['port']}"


def flag_emoji(country_code: str | None) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"
    try:
        return "".join(chr(127397 + ord(c)) for c in country_code.upper())
    except Exception:
        return "🌐"


def type_label(t: str) -> str:
    return {
        "socks5": "SOCKS5",
        "socks5h": "SOCKS5h",
        "socks4": "SOCKS4",
        "https": "HTTPS",
        "http": "HTTP",
    }.get(t, (t or "").upper())


# Реальная реализация живёт в playerokapi (используется и WS-раннером, и этим модулем) —
# чтобы не дублировать логику разбора proxy-URL в двух местах.
from playerokapi.common.utils import parse_proxy_for_ws  # noqa: E402,F401


def check_proxy(proxy_url: str, timeout: float = 10.0) -> dict:
    """
    Синхронная проверка (вызывать через asyncio.to_thread из хендлеров):
    1) достаёт гео через ip-api.com ЧЕРЕЗ прокси (best-effort, не критично);
    2) идёт на playerok.com/graphql ЧЕРЕЗ прокси — это и есть содержательная проверка.

    Возвращает {"ok", "ms", "error", "country_code", "country_name", "city"}.
    """
    from curl_cffi import requests as curl_requests

    result = {
        "ok": False, "ms": None, "error": None,
        "country_code": None, "country_name": None, "city": None,
    }

    proxies = {"http": proxy_url, "https": proxy_url}
    t0 = time.monotonic()

    # Гео — best-effort, ошибку тут не считаем провалом всей проверки.
    try:
        with curl_requests.Session(impersonate="chrome124") as s:
            geo_resp = s.get(_GEO_URL, proxies=proxies, timeout=timeout)
            geo = geo_resp.json()
        if geo.get("status") == "success":
            result["country_code"] = geo.get("countryCode")
            result["country_name"] = geo.get("country")
            result["city"] = geo.get("city")
    except Exception as e:
        logger.debug("Гео через прокси не определилось: %s", e)

    # Содержательная проверка: реальный запрос к Playerok через тот же клиент, что и Account.
    try:
        with curl_requests.Session(impersonate="chrome124") as s:
            resp = s.get(_PLAYEROK_CHECK_URL, proxies=proxies, timeout=timeout)
        body = ""
        try:
            body = resp.text
        except Exception:
            pass
        if any(sig in body for sig in _BOT_CHECK_SIGNATURES):
            result["error"] = "Прокси работает, но Playerok блокирует этот IP (DDoS-Guard)"
            return result
        # Любой ответ без антибот-сигнатур (даже 4xx на голый GET без нужных заголовков) —
        # значит соединение до Playerok через этот прокси в принципе проходит.
        result["ok"] = True
        result["ms"] = int((time.monotonic() - t0) * 1000)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result
