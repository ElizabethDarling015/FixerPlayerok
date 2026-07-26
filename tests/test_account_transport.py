"""
Тесты транспортного слоя `Account`: выбор цели impersonate, браузерные заголовки,
сигнатуры антибот-страниц и пересоздание сессии после серии сетевых сбоев.
"""
import pytest

from playerokapi import account as account_module
from playerokapi.account import Account
from playerokapi.common.exceptions import BotCheckDetectedException, RequestSendingError


class FakeSession:
    """Фейковая curl_cffi-сессия: возвращает заранее заданный ответ и запоминает заголовки."""

    def __init__(self, response=None):
        self.response = response
        self.last_headers: dict | None = None

    def get(self, url, **kwargs):
        self.last_headers = kwargs.get("headers")
        return self.response

    post = get


class FakeResponse:
    def __init__(self, payload=None, text="", status_code=200):
        self._payload = payload if payload is not None else {"data": {}}
        self.text = text
        self.status_code = status_code
        self.headers = {}
        self.url = "https://playerok.com/graphql"

    def json(self):
        return self._payload


def make_account(**kwargs):
    # backoff_factor=0 — без задержек между попытками в тестах.
    kwargs.setdefault("max_requests_retries", 3)
    kwargs.setdefault("backoff_factor", 0)
    return Account(cookies="token=x", **kwargs)


# ----------------------------------------------------------------------
# Выбор цели impersonate
# ----------------------------------------------------------------------

def test_impersonate_prefers_newest_available(monkeypatch):
    """Берём первую (самую свежую) цель, которую понимает установленная curl_cffi."""
    used = []

    def fake_session(impersonate=None):
        used.append(impersonate)
        return FakeSession()

    monkeypatch.setattr(account_module.curl_requests, "Session", fake_session)
    account = make_account()
    account._get_session()

    assert used == [account_module._IMPERSONATE_TARGETS[0]]
    assert account._impersonate == account_module._IMPERSONATE_TARGETS[0]


def test_impersonate_falls_back_to_older_target(monkeypatch):
    """Если свежие цели неизвестны установленной версии curl_cffi — откатываемся к старым."""
    used = []

    def fake_session(impersonate=None):
        used.append(impersonate)
        if impersonate in account_module._IMPERSONATE_TARGETS[:2]:
            raise ValueError(f"Impersonate target {impersonate} is not supported")
        return FakeSession()

    monkeypatch.setattr(account_module.curl_requests, "Session", fake_session)
    account = make_account()
    account._get_session()

    assert used == list(account_module._IMPERSONATE_TARGETS[:3])
    assert account._impersonate == account_module._IMPERSONATE_TARGETS[2]


def test_impersonate_last_resort_session_without_target(monkeypatch):
    """Ни одна цель не подошла — сессия всё равно создаётся, но уже без имитации браузера."""
    calls = []

    def fake_session(impersonate=None):
        calls.append(impersonate)
        if impersonate is not None:
            raise ValueError("unknown target")
        return FakeSession()

    monkeypatch.setattr(account_module.curl_requests, "Session", fake_session)
    account = make_account()

    assert isinstance(account._get_session(), FakeSession)
    assert account._impersonate is None
    assert calls[-1] is None


def test_installed_curl_cffi_accepts_some_target():
    """На реально установленной curl_cffi хотя бы одна цель из списка должна создаваться."""
    account = make_account()
    account._get_session()
    assert account._impersonate in account_module._IMPERSONATE_TARGETS


# ----------------------------------------------------------------------
# Браузерные заголовки
# ----------------------------------------------------------------------

def test_sec_ch_ua_matches_impersonate_target():
    account = make_account()
    account._impersonate = "chrome131"
    headers = account._client_hint_headers()

    assert headers["sec-ch-ua"] == ('"Chromium";v="131", "Google Chrome";v="131", '
                                    '"Not.A/Brand";v="99"')
    assert '"Chromium";v="131.0.6778.86"' in headers["sec-ch-ua-full-version-list"]

    # Смена цели (например, после пересоздания сессии) обновляет кэш заголовков.
    account._impersonate = "chrome124"
    assert '"124"' in account._client_hint_headers()["sec-ch-ua"]


def test_client_hints_follow_user_agent_platform():
    mac = make_account(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
    hints = mac._client_hint_headers()
    assert hints["sec-ch-ua-platform"] == '"macOS"'
    assert hints["sec-ch-ua-platform-version"] == '"10.15.7"'
    assert hints["sec-ch-ua-mobile"] == "?0"

    android = make_account(user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36")
    hints = android._client_hint_headers()
    assert hints["sec-ch-ua-platform"] == '"Android"'
    assert hints["sec-ch-ua-mobile"] == "?1"
    assert hints["sec-ch-ua-arch"] == '"arm"'

    win = make_account()  # UA по умолчанию — Windows
    assert win._client_hint_headers()["sec-ch-ua-platform"] == '"Windows"'


def test_request_sends_full_browser_headers():
    account = make_account()
    session = FakeSession(FakeResponse({"data": {"ok": True}}))
    account._session = session
    account._impersonate = "chrome136"

    account.request("get", payload={"operationName": "chats"})

    headers = session.last_headers
    for name in ("sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-ch-ua-arch",
                 "sec-ch-ua-bitness", "sec-ch-ua-platform-version", "sec-ch-ua-full-version-list",
                 "priority", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"):
        assert name in headers, name
    assert headers["x-gql-op"] == "chats"
    assert headers["x-apollo-operation-name"] == "chats"
    # Старые обязательные заголовки на месте.
    assert headers["x-gql-path"] == "/"
    assert headers["user-agent"] == account.user_agent
    assert headers["cookie"] == "token=x"
    assert '"136"' in headers["sec-ch-ua"]


def test_explicit_headers_still_override_defaults():
    account = make_account()
    session = FakeSession(FakeResponse({"data": {}}))
    account._session = session

    account.request("get", headers={"priority": "u=0"}, payload={"operationName": "viewer"})

    assert session.last_headers["priority"] == "u=0"


# ----------------------------------------------------------------------
# Сигнатуры антибот-защиты
# ----------------------------------------------------------------------

@pytest.mark.parametrize("page", [
    "<html><body>Checking your browser — DDoS-Guard</body></html>",
    "<html>ddos-guard.net</html>",
    "<h2>Attention Required! | Cloudflare</h2>",
    "<title>Just a moment...</title>",
    "<script>window._cf_chl_opt={cvId: '3'};</script>",
    "<div class='cf-browser-verification'></div>",
    "Cloudflare Ray ID: 8f2c1</br>",
    "cf-error-details",
    "Ray ID: 12345",
])
def test_bot_check_signatures_detect_ddos_guard_and_cloudflare(page):
    assert Account._looks_like_bot_check(page)


@pytest.mark.parametrize("page", ["", '{"data": {"viewer": null}}', "<html>Обычная страница</html>"])
def test_bot_check_signatures_ignore_normal_responses(page):
    assert not Account._looks_like_bot_check(page)


def test_bot_check_is_case_insensitive():
    """Регистр разметки у DDoS-Guard/Cloudflare плавает — матчинг не должен от него зависеть."""
    assert Account._looks_like_bot_check("<TITLE>JUST A MOMENT...</TITLE>")
    assert Account._looks_like_bot_check("<html>DDOS-GUARD</html>")


def test_request_raises_bot_check_on_cloudflare_page():
    account = make_account()
    account._session = FakeSession(FakeResponse(text="<title>Just a moment...</title>"))

    with pytest.raises(BotCheckDetectedException):
        account.request("get", payload={"operationName": "viewer"})


# ----------------------------------------------------------------------
# Пересоздание сессии после серии сетевых сбоев
# ----------------------------------------------------------------------

class FailingSession:
    def get(self, url, **kwargs):
        raise ConnectionError("network down")

    post = get


def make_counting_account(session_factory_result):
    """Аккаунт с подменённой фабрикой сессий; возвращает (аккаунт, список созданных сессий)."""
    account = make_account()
    created = []

    def factory():
        session = session_factory_result()
        created.append(session)
        account._impersonate = "chrome136"
        return session

    account._create_session = factory
    return account, created


def test_session_is_recreated_after_three_network_failures():
    account, created = make_counting_account(FailingSession)

    for _ in range(2):
        with pytest.raises(RequestSendingError):
            account.request("get", payload={"operationName": "chats"})

    # Первый запрос израсходовал все 3 попытки → сессия пересоздана перед вторым запросом.
    assert len(created) == 2
    assert created[0] is not created[1]


def test_session_is_recreated_mid_request_when_retries_allow():
    account, created = make_counting_account(FailingSession)
    account.max_requests_retries = 5

    with pytest.raises(RequestSendingError):
        account.request("get", payload={"operationName": "chats"})

    # 5 попыток: после 3-й подряд сетевой ошибки сессия меняется прямо внутри запроса.
    assert len(created) == 2
    assert account._network_fail_streak == 2


def test_successful_response_resets_failure_streak():
    account, created = make_counting_account(FailingSession)
    account.max_requests_retries = 2

    with pytest.raises(RequestSendingError):
        account.request("get", payload={"operationName": "chats"})
    assert account._network_fail_streak == 2

    # Удачный ответ обнуляет счётчик — сессия не пересоздаётся.
    account._session = FakeSession(FakeResponse({"data": {"ok": True}}))
    account.request("get", payload={"operationName": "chats"})
    assert account._network_fail_streak == 0

    ok_session = account._session
    account.request("get", payload={"operationName": "chats"})
    assert account._session is ok_session
    assert len(created) == 1


def test_refresh_keeps_cookies_proxy_and_headers(monkeypatch):
    """Пересоздание сессии не теряет cookies/прокси/заголовки — они живут в самом Account."""
    monkeypatch.setattr(account_module.curl_requests, "Session",
                        lambda impersonate=None: FakeSession(FakeResponse({"data": {}})))
    account = make_account(proxy="http://user:pass@host:3128")
    account.update_cookies("token=abc; __ddg5_=zzz")
    account._network_fail_streak = 3
    account._session = FakeSession()

    account._get_session()
    session = account._session
    account.request("get", payload={"operationName": "viewer"})

    assert account._network_fail_streak == 0
    assert session.last_headers["cookie"] == "token=abc; __ddg5_=zzz"
    assert account.proxy == "http://user:pass@host:3128"
    assert "sec-ch-ua" in session.last_headers
