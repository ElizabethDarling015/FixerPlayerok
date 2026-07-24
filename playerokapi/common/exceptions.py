"""Исключения библиотеки `playerokapi` (адаптировано из `alleexxeeyy/PlayerokAPI`)."""
from __future__ import annotations


class BotCheckDetectedException(Exception):
    """Возбуждается, если при отправке запроса сработала защита от бот-детекта (DDoS-Guard/Cloudflare)."""

    def __str__(self) -> str:
        return (
            "Бот-проверка заметила подозрительную активность при отправке запроса на сайт Playerok. "
            "Чтобы продолжить работу, поменяйте cookies аккаунта на актуальные "
            "(и, желательно, отправляйте запросы с того же IP-адреса, с которого вы авторизовывались)."
        )


class RequestFailedError(Exception):
    """
    Возбуждается, если код ответа сервера не равен 200 (и это не игнорируемый 304).

    :param response: Объект ответа `curl_cffi`.
    """

    def __init__(self, response):
        self.response = response
        self.status_code = getattr(response, "status_code", None)
        try:
            self.html_text = response.text
        except Exception:
            self.html_text = ""

    def __str__(self) -> str:
        url = getattr(self.response, "url", "?")
        return f"Ошибка запроса к {url}\nКод ошибки: {self.status_code}\nОтвет: {self.html_text}"


class RequestPlayerokError(Exception):
    """
    Возбуждается, если GraphQL-ответ Playerok содержит поле `errors`.

    :param response: Объект ответа `curl_cffi`.
    """

    def __init__(self, response):
        self.response = response
        self.json = response.json()
        error = (self.json.get("errors") or [{}])[0]
        self.error_code = (error.get("extensions") or {}).get("code")
        self.error_message = error.get("message")

    def __str__(self) -> str:
        url = getattr(self.response, "url", "?")
        msg = f"Ошибка запроса к {url}\nКод ошибки: {self.error_code}\nСообщение: {self.error_message}"
        return self.error_message or msg


class PersistedQueryNotFoundError(RequestPlayerokError):
    """
    Возбуждается, если сервер Playerok не узнал хэш persisted-запроса (код Apollo
    `PERSISTED_QUERY_NOT_FOUND`).

    `Account._persisted_query` ловит эту ошибку и повторяет запрос POST'ом с полным текстом
    из `QUERY_TEXTS` (стандартный APQ-фолбэк). Наружу исключение всплывает только если полного
    текста для операции нет.
    """

    def __init__(self, response, operation_name: str | None = None):
        super().__init__(response)
        self.operation_name = operation_name

    def __str__(self) -> str:
        op = self.operation_name or "?"
        return (
            f"Сервер Playerok не узнал persisted-запрос {op!r} (код: {self.error_code}). "
            f"Скорее всего, хэш этого запроса в playerokapi/graphql_queries.py устарел — "
            f"откройте playerok.com в браузере, найдите актуальный sha256Hash для операции "
            f"{op!r} во вкладке Network (DevTools) и обновите PERSISTED_QUERIES[{op!r}]."
        )


class RequestSendingError(Exception):
    """
    Возбуждается, если не удалось отправить запрос за несколько попыток подряд.

    :param url: URL запроса.
    :param error: Текст последней ошибки.
    """

    def __init__(self, url: str, error: str):
        self.url = url
        self.error = error

    def __str__(self) -> str:
        return f"Ошибка при попытке отправить запрос к {self.url}\nТекст ошибки: {self.error}"


class UnauthorizedError(Exception):
    """
    Возбуждается, если не удалось авторизоваться в аккаунте Playerok (невалидные/просроченные cookies).

    :param cause: Краткое описание исходной ошибки (код HTTP, сообщение GraphQL) — чтобы в логе
        было видно настоящую причину, а не только совет «проверьте cookies».
    """

    def __init__(self, cause: str | None = None):
        self.cause = cause

    def __str__(self) -> str:
        text = "Не удалось подключиться к аккаунту Playerok. Проверьте, что вы указали действительные cookies."
        if self.cause:
            text += f"\nПричина: {self.cause}"
            if "403" in self.cause:
                text += (
                    "\nКод 403 часто означает, что защита сайта (DDoS-Guard) блокирует IP-адрес "
                    "сервера. Попробуйте: 1) скопировать из браузера полную строку cookies "
                    "(включая __ddg5_), 2) указать прокси в configs/main.toml (секция [playerok], "
                    "параметр proxy), желательно с IP того же региона, где вы авторизовывались."
                )
            elif "INTERNAL_SERVER_ERROR" in self.cause or "HTTP 500" in self.cause:
                text += (
                    "\nОшибка 500 от Playerok обычно означает, что запрос не соответствует текущей "
                    "схеме API сайта (сайт обновился — нужно обновить библиотеку), реже — что token "
                    "повреждён при вставке (JWT — три части, разделённые точками)."
                )
        return text


class NotInitiatedError(Exception):
    """Возбуждается при вызове метода, требующего предварительного `Account(...).get()`."""

    def __str__(self) -> str:
        return (
            "Аккаунт Playerok не инициализирован для выполнения этого действия. "
            "Прежде чем сделать это, вызовите метод Account(...).get()."
        )
