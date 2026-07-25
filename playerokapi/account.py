"""
Класс `Account` — основная точка входа в библиотеку `playerokapi`.

Отвечает за авторизацию по cookie, отправку GraphQL-запросов (с обходом DDoS-Guard через
`curl_cffi` с имитацией Chrome) и все методы работы с аккаунтом: чаты, сообщения, сделки,
лоты, отзывы, баланс.
"""
from __future__ import annotations

import json
import logging
import random
import threading
import time
import uuid

from curl_cffi import requests as curl_requests

from . import parser, types
from .common.enums import MessageTemplateTypes, PriorityTypes
from .common.exceptions import (
    BotCheckDetectedException,
    NotInitiatedError,
    PersistedQueryNotFoundError,
    RequestFailedError,
    RequestPlayerokError,
    RequestSendingError,
    UnauthorizedError,
)
from .common.utils import parse_cookies_string, resolve_image_file
from .graphql_queries import PERSISTED_QUERIES, QUERIES, QUERY_TEXTS

logger = logging.getLogger("playerokapi.account")

_API_URL = "https://playerok.com/graphql"

# Сигнатуры в тексте ответа, по которым можно понять, что запрос перехвачен антибот-защитой,
# а не обработан GraphQL-сервером.
_BOT_CHECK_SIGNATURES = ("ddos-guard", "Ray ID", "cf-error-details", "Attention Required!")

# Код ошибки Apollo Persisted Queries, который сервер возвращает, если не узнал sha256Hash запроса.
_PERSISTED_QUERY_NOT_FOUND_CODE = "PERSISTED_QUERY_NOT_FOUND"

# GraphQL-код «нет прав на поле/операцию» (Playerok часто отдаёт его ещё и как HTTP 403).
_GRAPHQL_FORBIDDEN_CODE = "FORBIDDEN"


def _empty_review_list() -> types.ReviewList:
    """Пустая страница отзывов — для graceful-деградации при FORBIDDEN на testimonials."""
    return types.ReviewList(
        reviews=[],
        page_info=types.PageInfo(None, None, False, False),
        total_count=0,
    )


def _close_file_objects(file_objects) -> None:
    """Закрывает файловые объекты multipart-вложений (байтовые вложения пропускает)."""
    for file_obj in file_objects:
        close = getattr(file_obj, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


class Account:
    """
    Аккаунт Playerok, авторизованный через cookie.

    :param cookies: Строка cookies (`"token=...; __ddg5_=..."`) или уже распарсенный словарь `{имя: значение}`.
    :param user_agent: User-Agent, под которым отправляются запросы. Желательно указывать тот же,
        под которым вы получили cookies — иначе выше риск сработавшей антибот-защиты.
    :param requests_timeout: Таймаут одного HTTP-запроса в секундах.
    :param proxy: Прокси в формате `curl_cffi` (например `"http://user:pass@host:port"`), опционально.
    :param max_requests_retries: Сколько раз повторить запрос при сетевой ошибке, временной (5xx)
        ошибке сервера или сработавшей антибот-проверке, прежде чем поднять итоговое исключение.
    :param backoff_factor: Множитель экспоненциальной задержки между повторными попытками —
        `backoff_factor * 2 ** номер_попытки` секунд (плюс небольшой случайный джиттер).
    """

    def __init__(self, cookies: str | dict, user_agent: str | None = None, requests_timeout: int = 15,
                 proxy: str | None = None, max_requests_retries: int = 3, backoff_factor: float = 0.5):
        self.cookies: dict = parse_cookies_string(cookies) if isinstance(cookies, str) else dict(cookies)
        self.user_agent: str = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        self.requests_timeout: int = requests_timeout
        self.proxy: str | None = proxy
        self.max_requests_retries: int = max_requests_retries
        self.backoff_factor: float = backoff_factor

        self.id: str | None = None
        """ID аккаунта. Заполняется после вызова `get()`."""
        self.username: str | None = None
        """Никнейм аккаунта. Заполняется после вызова `get()`."""
        self.profile: types.AccountProfile | None = None
        """Полный профиль аккаунта (баланс, статистика и т.п.). Заполняется после вызова `get()`."""

        self._session: curl_requests.Session | None = None
        # Общая curl_cffi-сессия не потокобезопасна, а её конкурентно используют потоки Runner
        # (WS-обработчики, поллинг) и пользовательский код — сериализуем запросы через lock.
        self._session_lock = threading.Lock()
        self._runner = None  # ссылка на Runner проставляется самим Runner'ом при создании
        self._unread_counters: dict[str, int] = {}  # chat_id -> unreadMessagesCounter (см. _note_chat)
        # Операция testimonials на Playerok часто закрыта для seller (только support/admin) —
        # после первого FORBIDDEN больше не дёргаем API, чтобы не спамить 403 в лог.
        self._testimonials_forbidden: bool = False

    # ------------------------------------------------------------------
    # Низкоуровневая отправка запросов
    # ------------------------------------------------------------------

    def _get_session(self) -> curl_requests.Session:
        if self._session is None:
            self._session = curl_requests.Session(impersonate="chrome124")
        return self._session

    def _cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def request(self, method: str, url: str = _API_URL, headers: dict | None = None, payload=None,
                files: dict | None = None, idempotent: bool = True) -> curl_requests.Response:
        """
        Отправляет HTTP-запрос к сайту Playerok через `curl_cffi` (с имитацией Chrome, чтобы обойти
        DDoS-Guard) и с cookies аккаунта. Используется всеми остальными методами `Account`.

        :param method: HTTP-метод (`"get"` или `"post"`).
        :param url: URL запроса. По умолчанию — GraphQL-эндпоинт Playerok.
        :param headers: Дополнительные заголовки (переопределяют заголовки по умолчанию).
        :param payload: Тело запроса. Для `GET` — словарь query-параметров. Для `POST` без `files` — JSON-тело.
            Для `POST` с `files` — словарь полей multipart-формы (см. `files`).
        :param files: Словарь файлов для multipart-запроса (ключ — имя поля формы).
        :param idempotent: Можно ли безопасно повторять запрос при неоднозначных ошибках (сеть/5xx/
            антибот). Для мутаций (отправка сообщений, оплата и т.п.) передавайте `False` — иначе
            повтор после фактически доставленного запроса может привести к дублям.
        :raises BotCheckDetectedException: Сработала антибот-защита сайта (после исчерпания повторных попыток).
        :raises RequestFailedError: Код ответа сервера не равен 200 (для 4xx — сразу, без повторных попыток).
        :raises PersistedQueryNotFoundError: Сервер не узнал хэш persisted-запроса (устарел, см. README).
        :raises RequestPlayerokError: GraphQL-ответ содержит поле `errors` (прочие случаи).
        :raises RequestSendingError: Не удалось отправить запрос за `max_requests_retries` попыток.
        :return: Объект ответа `curl_cffi`.
        """
        operation_name = "viewer"
        if isinstance(payload, dict):
            operation_name = payload.get("operationName", operation_name)

        default_headers = {
            "accept": "*/*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json" if not files else None,
            "cookie": self._cookie_header(),
            "origin": "https://playerok.com",
            "referer": "https://playerok.com/",
            "user-agent": self.user_agent,
            "x-gql-op": operation_name,
            # Обязательные заголовки Playerok: без x-gql-path сервер отвечает
            # HTTP 500 «Internal server error» на ЛЮБОЙ GraphQL-запрос.
            "x-gql-path": "/",
            "x-timezone-offset": str(time.timezone // 60),
        }
        default_headers = {k: v for k, v in default_headers.items() if v is not None}
        merged_headers = {**default_headers, **(headers or {})}

        session = self._get_session()
        last_error: Exception | None = None

        # Неидемпотентные запросы (мутации) не повторяем автоматически: после сетевой ошибки
        # или 5xx нельзя знать, был ли запрос уже обработан сервером, а повтор породит дубли.
        max_attempts = self.max_requests_retries if idempotent else 1

        for attempt in range(max_attempts):
            is_last_attempt = attempt == max_attempts - 1
            logger.debug("[%s] %s %s (попытка %d/%d)", operation_name, method.upper(), url, attempt + 1,
                         max_attempts)
            try:
                kwargs = {"headers": merged_headers, "timeout": self.requests_timeout}
                if self.proxy:
                    kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
                with self._session_lock:
                    if method.lower() == "get":
                        kwargs["params"] = payload
                        response = session.get(url, **kwargs)
                    else:
                        if files:
                            kwargs["data"] = payload
                            kwargs["files"] = files
                        else:
                            kwargs["json"] = payload
                        response = session.post(url, **kwargs)
            except Exception as exc:
                last_error = exc
                logger.warning("[%s] Сетевая ошибка (попытка %d/%d): %s", operation_name, attempt + 1,
                               max_attempts, exc)
                if is_last_attempt:
                    raise RequestSendingError(url, str(last_error)) from exc
                self._sleep_before_retry(attempt)
                continue

            response_text = ""
            try:
                response_text = response.text
            except Exception:
                pass

            if any(sig in response_text for sig in _BOT_CHECK_SIGNATURES):
                logger.warning("[%s] Обнаружена антибот-проверка (попытка %d/%d)", operation_name, attempt + 1,
                               max_attempts)
                if is_last_attempt:
                    raise BotCheckDetectedException()
                self._sleep_before_retry(attempt)
                continue

            try:
                response_json = response.json()
            except Exception:
                response_json = None

            if response.status_code != 200:
                if response.status_code >= 500 and not is_last_attempt:
                    logger.warning("[%s] Сервер вернул %d (попытка %d/%d) — повтор", operation_name,
                                   response.status_code, attempt + 1, max_attempts)
                    self._sleep_before_retry(attempt)
                    continue
                # GraphQL-ошибки могут прийти и с HTTP 4xx (Playerok так отдаёт FORBIDDEN),
                # не только с 200 — иначе callers видят сырой RequestFailedError вместо кода GQL.
                if isinstance(response_json, dict) and response_json.get("errors"):
                    first_error = (response_json.get("errors") or [{}])[0]
                    error_code = (first_error.get("extensions") or {}).get("code")
                    if error_code == _PERSISTED_QUERY_NOT_FOUND_CODE:
                        logger.error("[%s] Хэш persisted-запроса не распознан сервером", operation_name)
                        raise PersistedQueryNotFoundError(response, operation_name)
                    logger.error(
                        "[%s] GraphQL-ошибка (HTTP %d): %s",
                        operation_name,
                        response.status_code,
                        first_error.get("message"),
                    )
                    raise RequestPlayerokError(response)
                logger.error("[%s] Сервер вернул %d", operation_name, response.status_code)
                raise RequestFailedError(response)

            if isinstance(response_json, dict) and response_json.get("errors"):
                first_error = (response_json.get("errors") or [{}])[0]
                error_code = (first_error.get("extensions") or {}).get("code")
                if error_code == _PERSISTED_QUERY_NOT_FOUND_CODE:
                    logger.error("[%s] Хэш persisted-запроса не распознан сервером", operation_name)
                    raise PersistedQueryNotFoundError(response, operation_name)
                logger.error("[%s] GraphQL-ошибка: %s", operation_name, first_error.get("message"))
                raise RequestPlayerokError(response)

            logger.debug("[%s] Успешный ответ (%d)", operation_name, response.status_code)
            return response

        raise RequestSendingError(url, str(last_error))

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = self.backoff_factor * (2 ** attempt)
        # Джиттер размазывает повторные попытки во времени, чтобы несколько потоков
        # не ретраили синхронно (и не выглядели как бот-волна).
        delay += random.uniform(0, self.backoff_factor)
        time.sleep(delay)

    def _persisted_query(self, operation_name: str, variables: dict) -> dict:
        """
        Apollo Automatic Persisted Queries: сначала GET только с sha256Hash; если сервер
        ответил `PERSISTED_QUERY_NOT_FOUND` — один POST с полным текстом из `QUERY_TEXTS`
        (стандартный APQ-фолбэк).
        """
        sha = PERSISTED_QUERIES[operation_name]
        extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha}}
        payload = {
            "operationName": operation_name,
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(extensions, separators=(",", ":")),
        }
        try:
            response = self.request("get", payload=payload)
        except PersistedQueryNotFoundError:
            query_text = QUERY_TEXTS.get(operation_name) or QUERIES.get(operation_name)
            if not query_text:
                raise
            logger.warning(
                "[%s] Хэш persisted-запроса не распознан — повторяю POST с полным текстом (APQ)",
                operation_name,
            )
            response = self.request(
                "post",
                payload={
                    "operationName": operation_name,
                    "variables": variables,
                    "query": query_text,
                    "extensions": extensions,
                },
                idempotent=True,
            )
        return response.json()["data"]

    def _query(self, operation_name: str, variables: dict, idempotent: bool = False) -> dict:
        """
        Отправляет обычный (не multipart) POST-запрос с полным текстом запроса из `QUERIES`.

        Большинство таких запросов — мутации, поэтому по умолчанию `idempotent=False`
        (без авто-повтора). Для запросов на чтение (например, `viewer`) передавайте
        `idempotent=True`, чтобы работали повторные попытки при сетевых сбоях.
        """
        payload = {"operationName": operation_name, "variables": variables, "query": QUERIES[operation_name]}
        response = self.request("post", payload=payload, idempotent=idempotent)
        return response.json()["data"]

    def _note_chat(self, chat: types.Chat | None) -> None:
        """Запоминает актуальный `unread_messages_counter` чата — используется `mark_chat_as_read_if_needed`."""
        if chat and chat.id and chat.unread_messages_counter is not None:
            self._unread_counters[chat.id] = chat.unread_messages_counter

    def _note_chats(self, chats) -> None:
        for chat in chats or []:
            self._note_chat(chat)

    # ------------------------------------------------------------------
    # Аккаунт: профиль, баланс
    # ------------------------------------------------------------------

    def get(self) -> "Account":
        """
        Загружает/обновляет данные своего аккаунта (`id`, `username`, `profile`).

        :raises UnauthorizedError: Cookies недействительны/просрочены.
        :return: `self` — для удобного чейнинга (`account = Account(cookies).get()`).
        """
        if self._runner is not None:
            self._runner._dispatch_hook("PRE_INIT")
        try:
            # Полнотекстовый запрос `viewer` — так же авторизуется сам сайт playerok.com.
            # Persisted-запрос `user` для этого не подходит: он требует id/username,
            # которые до авторизации неизвестны.
            data = self._query("viewer", {}, idempotent=True)
        except RequestPlayerokError as exc:
            raise UnauthorizedError(cause=exc.error_message or f"GraphQL-код {exc.error_code}") from exc
        except RequestFailedError as exc:
            body = (exc.html_text or "").strip().replace("\n", " ")[:200]
            raise UnauthorizedError(cause=f"HTTP {exc.status_code}. Ответ сервера: {body or '<пусто>'}") from exc

        raw_user = data.get("viewer") or data.get("user")
        if not raw_user or not raw_user.get("id"):
            raise UnauthorizedError(cause="сервер ответил успешно, но не вернул данные пользователя — "
                                          "обычно это значит, что токен просрочен")

        self.profile = parser.account_profile(raw_user)
        self.id = raw_user.get("id")
        self.username = self.profile.username if self.profile else raw_user.get("username")
        if self._runner is not None:
            self._runner._dispatch_hook("POST_INIT")
        return self

    def get_balance(self) -> types.AccountBalance | None:
        """
        Запрашивает актуальный баланс аккаунта (без обновления остальных полей `profile`).

        :return: Баланс аккаунта либо `None`, если сервер не вернул данных.
        """
        data = self._persisted_query("viewerBalance", {})
        balance = parser.account_balance(data.get("viewerBalance") or (data.get("viewer") or {}).get("balance"))
        if balance and self.profile:
            self.profile.balance = balance
        return balance

    def get_user(self, id: str | None = None, username: str | None = None) -> types.UserProfile | None:
        """
        Получает публичный профиль пользователя по его ID или никнейму.

        :param id: ID пользователя (взаимоисключающе с `username`).
        :param username: Никнейм пользователя (взаимоисключающе с `id`).
        :return: Профиль пользователя либо `None`, если не найден.
        """
        # hasSupportAccess — обязательная переменная запроса `user`:
        # без неё сервер отвечает ошибкой «Variable "$hasSupportAccess" ... was not provided».
        variables: dict = {"hasSupportAccess": False}
        if id:
            variables["id"] = id
        if username:
            variables["username"] = username
        data = self._persisted_query("user", variables)
        return parser.user_profile(data.get("user"))

    def get_my_reviews(self, count: int = 20, after_cursor: str | None = None) -> types.ReviewList | None:
        """
        Получает отзывы о своём аккаунте.

        :param count: Сколько отзывов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации (см. `ReviewList.page_info.end_cursor`).
        :raises NotInitiatedError: Аккаунт не инициализирован (`Account(...).get()` не вызывался).
        :return: Страница списка отзывов.
        """
        if not self.id:
            raise NotInitiatedError()
        return self.get_user_reviews(self.id, count=count, after_cursor=after_cursor)

    def get_user_reviews(self, user_id: str, count: int = 20, after_cursor: str | None = None) -> types.ReviewList | None:
        """
        Получает отзывы о пользователе.

        :param user_id: ID пользователя (продавца), чьи отзывы нужно получить.
        :param count: Сколько отзывов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка отзывов. Если операция `testimonials` недоступна аккаунту
            (GraphQL FORBIDDEN — типично для seller без support-доступа), возвращает пустой список
            и больше не дергает API.
        """
        if self._testimonials_forbidden:
            return _empty_review_list()
        # hasSupportAccess — обязательная переменная схемы (Boolean!), без неё сервер отвечает 500.
        # Сама переменная не выдаёт доступ: поле testimonials на сервере часто закрыто для seller.
        variables = {"pagination": {"first": count}, "filter": {"userId": user_id},
                     "hasSupportAccess": False}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        try:
            data = self._persisted_query("testimonials", variables)
        except RequestPlayerokError as exc:
            if exc.error_code == _GRAPHQL_FORBIDDEN_CODE:
                self._testimonials_forbidden = True
                logger.warning(
                    "Операция testimonials недоступна этому аккаунту (FORBIDDEN) — "
                    "список отзывов пропускаем (обычно нужно support-право; для seller-бота это не критично)"
                )
                return _empty_review_list()
            raise
        return parser.review_list(data.get("testimonials"))

    # ------------------------------------------------------------------
    # Чаты и сообщения
    # ------------------------------------------------------------------

    def get_chats(self, count: int = 20, after_cursor: str | None = None) -> types.ChatList | None:
        """
        Получает список своих чатов.

        :param count: Сколько чатов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :raises NotInitiatedError: Аккаунт не инициализирован (`Account(...).get()` не вызывался).
        :return: Страница списка чатов.
        """
        if not self.id:
            raise NotInitiatedError()
        # Форма variables снята с реального трафика: сайт передаёт filter.userId.
        variables: dict = {"pagination": {"first": count}, "filter": {"userId": self.id},
                           "hasSupportAccess": False}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("userChats", variables)
        chat_list = parser.chat_list(data.get("chats"))
        if chat_list:
            self._note_chats(chat_list.chats)
        return chat_list

    def get_chat(self, id: str) -> types.Chat | None:
        """
        Получает чат по его ID.

        :param id: ID чата.
        :return: Чат либо `None`, если не найден.
        """
        data = self._persisted_query("chat", {"id": id, "hasSupportAccess": False})
        chat = parser.chat(data.get("chat"))
        self._note_chat(chat)
        return chat

    def get_chat_messages(self, chat_id: str, count: int = 50, after_cursor: str | None = None) -> types.ChatMessageList | None:
        """
        Получает сообщения чата.

        :param chat_id: ID чата.
        :param count: Сколько сообщений запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка сообщений чата.
        """
        # Форма variables снята с реального трафика: chatId лежит в filter,
        # плюс флаги hasSupportAccess/showForbiddenImage.
        variables: dict = {
            "pagination": {"first": count},
            "filter": {"chatId": chat_id},
            "hasSupportAccess": False,
            "showForbiddenImage": True,
        }
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("chatMessages", variables)
        return parser.chat_message_list(data.get("chatMessages"))

    def mark_chat_as_read(self, chat_id: str) -> types.Chat | None:
        """
        Безусловно отмечает чат как прочитанный (шлёт мутацию, даже если чат уже был прочитан).

        В большинстве случаев удобнее `mark_chat_as_read_if_needed()` — он не делает лишний запрос,
        если по данным библиотеки в чате и так уже нет непрочитанных сообщений.

        :param chat_id: ID чата.
        :return: Обновлённый чат.
        """
        data = self._query("markChatAsRead", {"input": {"chatId": chat_id}})
        chat = parser.chat(data.get("markChatAsRead"))
        self._note_chat(chat)
        return chat

    def mark_chat_as_read_if_needed(self, chat_id: str) -> bool:
        """
        Отмечает чат как прочитанный, но только если это действительно нужно.

        Ориентируется на последний известный библиотеке `unread_messages_counter` этого чата
        (обновляется в `get_chats`/`get_chat`/`send_message`, а также `Runner`-ом на каждое
        WS-обновление чата). Если по этим данным в чате нет непрочитанных сообщений — никакого
        запроса не отправляется. Если данных о чате ещё нет — на всякий случай отмечает прочитанным.

        :param chat_id: ID чата.
        :return: `True`, если запрос `mark_chat_as_read` был отправлен, `False`, если он не потребовался.
        """
        if self._unread_counters.get(chat_id, 1) <= 0:
            return False
        self.mark_chat_as_read(chat_id)
        return True

    def upload_chat_image(self, image: str | bytes, chat_id: str) -> types.TemporaryAttachmentUploadOutput | None:
        """
        Загружает изображение во временное хранилище перед отправкой его в сообщении чата.

        Для обычной отправки картинки этот метод вызывать не нужно — передайте изображение сразу
        в `send_message(chat_id, image=...)` (путь к файлу или байты), загрузка произойдёт сама.

        :param image: Путь к файлу изображения на диске либо готовые байты изображения.
        :param chat_id: ID чата, для которого загружается изображение.
        :return: Информация о загруженном временном вложении.
        """
        filename, file_obj, content_type = resolve_image_file(image)
        client_attachment_id = str(uuid.uuid4())
        payload = {
            "operationName": "uploadChatImageIntoTemporaryStore",
            "variables": {"input": {"chatId": chat_id, "clientAttachmentId": client_attachment_id}},
            "query": QUERIES["uploadChatImageIntoTemporaryStore"],
        }
        multipart_payload = {
            "operations": json.dumps(payload, separators=(",", ":")),
            "map": json.dumps({"0": ["variables.file"]}, separators=(",", ":")),
        }
        files = {"0": (filename, file_obj, content_type)}
        try:
            response = self.request("post", payload=multipart_payload, files=files, idempotent=False)
        finally:
            _close_file_objects([file_obj])
        data = response.json()["data"]
        return parser.temporary_attachment_upload_output(data.get("uploadChatImageIntoTemporaryStore"))

    def send_message(self, chat_id: str, text: str | None = None, image: str | bytes | None = None,
                      mark_as_read: bool = True) -> types.ChatMessage | None:
        """
        Отправляет сообщение в чат.

        :param chat_id: ID чата.
        :param text: Текст сообщения (может отсутствовать, если отправляется только изображение).
        :param image: Путь к файлу изображения на диске либо готовые байты изображения, опционально.
        :param mark_as_read: Отметить ли чат прочитанным после отправки сообщения. Реальный запрос
            `mark_chat_as_read` отправляется только если это необходимо — см. `mark_chat_as_read_if_needed`.
        :return: Отправленное сообщение.
        """
        input_data: dict = {"chatId": chat_id}
        if text:
            input_data["text"] = text

        if image is not None:
            filename, file_obj, content_type = resolve_image_file(image)
            payload = {
                "operationName": "createChatMessage",
                "variables": {"input": input_data, "file": None, "showForbiddenImage": True},
                "query": QUERIES["createChatMessage"],
            }
            multipart_payload = {
                "operations": json.dumps(payload, separators=(",", ":")),
                "map": json.dumps({"0": ["variables.file"]}, separators=(",", ":")),
            }
            files = {"0": (filename, file_obj, content_type)}
            try:
                response = self.request("post", payload=multipart_payload, files=files, idempotent=False)
            finally:
                _close_file_objects([file_obj])
            data = response.json()["data"]
        else:
            data = self._query("createChatMessage", {"input": input_data, "file": None, "showForbiddenImage": True})

        message = parser.chat_message(data.get("createChatMessage"))

        if mark_as_read:
            try:
                self.mark_chat_as_read_if_needed(chat_id)
            except Exception:
                logger.warning("[send_message] Не удалось отметить чат %s прочитанным", chat_id, exc_info=True)

        return message

    # ------------------------------------------------------------------
    # Сделки
    # ------------------------------------------------------------------

    def get_deals(self, count: int = 20, after_cursor: str | None = None, status=None,
                  direction=None) -> types.ItemDealList | None:
        """
        Получает список своих сделок.

        :param count: Сколько сделок запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :param status: Фильтр по "сырому" статусу сделки (значение `common.enums.ItemDealStatuses`, опционально).
        :param direction: Фильтр по направлению сделки (значение `common.enums.ItemDealDirections`, опционально).
        :return: Страница списка сделок.
        """
        if not self.id:
            raise NotInitiatedError()
        # filter — обязательная переменная схемы (ItemDealFilter!): без неё сервер отвечает 500
        # «Variable "$filter" ... was not provided». Минимум — userId своего аккаунта.
        filter_data: dict = {"userId": self.id}
        if status is not None:
            filter_data["status"] = status.name if hasattr(status, "name") else status
        if direction is not None:
            filter_data["direction"] = direction.name if hasattr(direction, "name") else direction
        variables: dict = {"pagination": {"first": count}, "filter": filter_data,
                           "showForbiddenImage": True}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("deals", variables)
        return parser.item_deal_list(data.get("deals"))

    def get_deal(self, id: str) -> types.ItemDeal | None:
        """
        Получает сделку по её ID.

        :param id: ID сделки.
        :return: Сделка либо `None`, если не найдена.
        """
        data = self._persisted_query("deal", {"id": id, "hasSupportAccess": False,
                                              "showForbiddenImage": True})
        return parser.item_deal(data.get("deal"))

    def update_deal(self, deal_id: str, status) -> types.ItemDeal | None:
        """
        Обновляет статус сделки (например, подтверждает получение товара покупателем или оформляет
        возврат средств).

        Playerok сам ограничивает, какие переходы статуса допустимы для текущей стороны сделки —
        при недопустимом переходе будет поднята `RequestPlayerokError`.

        :param deal_id: ID сделки.
        :param status: Новый статус сделки (значение `common.enums.ItemDealStatuses`, обычно
            `CONFIRMED` — подтвердить получение товара, или `ROLLED_BACK` — оформить возврат).
        :return: Обновлённая сделка.
        """
        input_data = {"id": deal_id, "status": status.name if hasattr(status, "name") else status}
        data = self._query("updateDeal", {"input": input_data, "showForbiddenImage": True})
        result = parser.item_deal(data.get("updateDeal"))
        if result:
            logger.info("Статус сделки %s обновлён: %s", deal_id, result.raw_status)
        return result

    def get_message_templates(self, type: MessageTemplateTypes = MessageTemplateTypes.ACTIVE_DEAL_PROBLEM,
                               count: int = 20, after_cursor: str | None = None) -> types.MessageTemplateList | None:
        """
        Получает шаблонные сообщения — доступные варианты причины проблемы в сделке
        (используются как `problem_type_id` в `report_deal_problem`).

        :param type: Тип шаблонных сообщений — проблема в активной или в завершённой сделке
            (см. `common.enums.MessageTemplateTypes`).
        :param count: Сколько шаблонов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка шаблонных сообщений.
        """
        variables: dict = {"pagination": {"first": count},
                           "filter": {"type": type.name if hasattr(type, "name") else type}}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("messageTemplates", variables)
        return parser.message_template_list(data.get("messageTemplates"))

    def report_deal_problem(self, deal_id: str, description: str, problem_type_id: str) -> types.ItemDeal | None:
        """
        Заявляет проблему по сделке (например, товар не пришёл или не соответствует описанию).

        :param deal_id: ID сделки.
        :param description: Описание проблемы.
        :param problem_type_id: ID типа (причины) проблемы — ID шаблонного сообщения из
            `get_message_templates()`.
        :return: Обновлённая сделка (`has_problem=True`).
        """
        input_data = {"dealId": deal_id, "description": description, "problemTypeId": problem_type_id}
        data = self._query("reportDealProblem", {"input": input_data, "showForbiddenImage": True})
        result = parser.item_deal(data.get("reportDealProblem"))
        if result:
            logger.info("Заявлена проблема по сделке %s: %r", deal_id, description)
        return result

    # ------------------------------------------------------------------
    # Игры / категории / поля
    # ------------------------------------------------------------------

    def get_games(self, name: str | None = None, count: int = 50,
                  after_cursor: str | None = None) -> types.GameList | None:
        """
        Получает список игр/приложений сайта.

        :param name: Фильтр по названию (поиск), опционально.
        :param count: Сколько игр запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка игр/приложений.
        """
        filter_data: dict = {}
        if name:
            filter_data["name"] = name
        variables: dict = {"pagination": {"first": count}}
        if filter_data:
            variables["filter"] = filter_data
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("games", variables)
        return parser.game_list(data.get("games"))

    def get_game(self, id: str | None = None, slug: str | None = None) -> types.Game | None:
        """
        Получает игру/приложение по ID или по имени страницы (`slug`).

        :param id: ID игры/приложения (взаимоисключающе с `slug`).
        :param slug: Имя страницы игры/приложения, как в URL (взаимоисключающе с `id`).
        :return: Игра/приложение либо `None`, если не найдена.
        """
        variables: dict = {}
        if id:
            variables["id"] = id
        if slug:
            variables["slug"] = slug
        data = self._persisted_query("GamePage", variables)
        return parser.game(data.get("game"))

    def get_game_category(self, game_id: str | None = None, slug: str | None = None,
                           category_id: str | None = None) -> types.GameCategory | None:
        """
        Получает категорию игры/приложения.

        :param game_id: ID игры/приложения, которой принадлежит категория.
        :param slug: Имя страницы категории, как в URL.
        :param category_id: ID категории (альтернативный способ идентификации).
        :return: Категория игры либо `None`, если не найдена.
        """
        variables: dict = {}
        if game_id:
            variables["gameId"] = game_id
        if slug:
            variables["slug"] = slug
        if category_id:
            variables["categoryId"] = category_id
        data = self._persisted_query("GamePageCategory", variables)
        return parser.game_category(data.get("gameCategory"))

    def get_game_category_obtaining_types(self, game_category_id: str, count: int = 50,
                                           after_cursor: str | None = None) -> types.GameCategoryObtainingTypeList | None:
        """
        Получает способы получения предмета в категории (нужны для `create_item`).

        :param game_category_id: ID категории игры.
        :param count: Сколько способов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка способов получения.
        """
        variables: dict = {"filter": {"gameCategoryId": game_category_id}, "pagination": {"first": count}}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("gameCategoryObtainingTypes", variables)
        return parser.game_category_obtaining_type_list(data.get("gameCategoryObtainingTypes"))

    def get_game_category_data_fields(self, game_category_id: str, obtaining_type_id: str | None = None,
                                       count: int = 50,
                                       after_cursor: str | None = None) -> types.GameCategoryDataFieldList | None:
        """
        Получает поля с данными категории, которые нужно заполнить при создании лота (`create_item`).

        :param game_category_id: ID категории игры.
        :param obtaining_type_id: ID выбранного способа получения (если у категории несколько способов).
        :param count: Сколько полей запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :return: Страница списка полей с данными.
        """
        filter_data: dict = {"gameCategoryId": game_category_id}
        if obtaining_type_id:
            filter_data["obtainingTypeId"] = obtaining_type_id
        variables: dict = {"filter": filter_data, "pagination": {"first": count}}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("gameCategoryDataFields", variables)
        return parser.game_category_data_field_list(data.get("gameCategoryDataFields"))

    # ------------------------------------------------------------------
    # Лоты
    # ------------------------------------------------------------------

    def _resolve_items(self, raw_item: dict | None):
        return parser.my_item(raw_item) if raw_item and raw_item.get("__typename") == "MyItem" else parser.item(raw_item)

    def create_item(self, game_id: str, category_id: str, name: str, price: int, description: str = "",
                     obtaining_type_id: str | None = None, attachments: list[str | bytes] | None = None,
                     data_fields: dict[str, str] | None = None, options: dict[str, str] | None = None,
                     comment: str | None = None) -> types.MyItem | types.Item | None:
        """
        Создаёт черновик лота (для публикации используйте `publish_item`).

        :param game_id: ID игры/приложения.
        :param category_id: ID категории игры.
        :param name: Название лота.
        :param price: Цена лота (в рублях).
        :param description: Описание лота.
        :param obtaining_type_id: ID способа получения товара (см. `get_game_category_obtaining_types`).
        :param attachments: Пути к файлам изображений на диске либо готовые байты изображений.
        :param data_fields: Значения полей данных лота `{id_поля: значение}` (см. `get_game_category_data_fields`).
        :param options: Значения опций (атрибутов) лота `{id_опции: значение}` (см. `GameCategory.options`).
        :param comment: Комментарий продавца к лоту.
        :return: Созданный лот (черновик).
        """
        input_data: dict = {"gameId": game_id, "categoryId": category_id, "name": name, "price": price,
                             "description": description}
        if obtaining_type_id:
            input_data["obtainingTypeId"] = obtaining_type_id
        if comment:
            input_data["comment"] = comment
        if data_fields:
            input_data["dataFields"] = [{"id": k, "value": v} for k, v in data_fields.items()]
        if options:
            input_data["attributes"] = [{"id": k, "value": v} for k, v in options.items()]

        files_list = [resolve_image_file(att) for att in (attachments or [])]
        if files_list:
            payload = {
                "operationName": "createItem",
                "variables": {"input": input_data, "attachments": [None] * len(files_list),
                              "showForbiddenImage": True},
                "query": QUERIES["createItem"],
            }
            multipart_payload = {
                "operations": json.dumps(payload, separators=(",", ":")),
                "map": json.dumps(
                    {str(i): [f"variables.attachments.{i}"] for i in range(len(files_list))},
                    separators=(",", ":"),
                ),
            }
            files = {str(i): (fn, fobj, ct) for i, (fn, fobj, ct) in enumerate(files_list)}
            try:
                response = self.request("post", payload=multipart_payload, files=files, idempotent=False)
            finally:
                _close_file_objects(fobj for _, fobj, _ in files_list)
            data = response.json()["data"]
        else:
            data = self._query("createItem", {"input": input_data, "attachments": [], "showForbiddenImage": True})
        return self._resolve_items(data.get("createItem"))

    def update_item(self, item_id: str, name: str | None = None, price: int | None = None,
                     description: str | None = None, data_fields: dict[str, str] | None = None,
                     options: dict[str, str] | None = None, comment: str | None = None,
                     added_attachments: list[str | bytes] | None = None) -> types.MyItem | types.Item | None:
        """
        Обновляет уже созданный лот.

        :param item_id: ID лота.
        :param name: Новое название лота, опционально.
        :param price: Новая цена лота, опционально.
        :param description: Новое описание лота, опционально.
        :param data_fields: Новые значения полей данных лота `{id_поля: значение}`, опционально.
        :param options: Новые значения опций (атрибутов) лота `{id_опции: значение}`, опционально.
        :param comment: Новый комментарий продавца к лоту, опционально.
        :param added_attachments: Пути к новым файлам изображений на диске либо готовые байты изображений
            (добавляются к уже имеющимся изображениям лота).
        :return: Обновлённый лот.
        """
        input_data: dict = {"id": item_id}
        if name is not None:
            input_data["name"] = name
        if price is not None:
            input_data["price"] = price
        if description is not None:
            input_data["description"] = description
        if comment is not None:
            input_data["comment"] = comment
        if data_fields:
            input_data["dataFields"] = [{"id": k, "value": v} for k, v in data_fields.items()]
        if options:
            input_data["attributes"] = [{"id": k, "value": v} for k, v in options.items()]

        files_list = [resolve_image_file(att) for att in (added_attachments or [])]
        if files_list:
            payload = {
                "operationName": "updateItem",
                "variables": {"input": input_data, "addedAttachments": [None] * len(files_list),
                              "showForbiddenImage": True},
                "query": QUERIES["updateItem"],
            }
            multipart_payload = {
                "operations": json.dumps(payload, separators=(",", ":")),
                "map": json.dumps(
                    {str(i): [f"variables.addedAttachments.{i}"] for i in range(len(files_list))},
                    separators=(",", ":"),
                ),
            }
            files = {str(i): (fn, fobj, ct) for i, (fn, fobj, ct) in enumerate(files_list)}
            try:
                response = self.request("post", payload=multipart_payload, files=files, idempotent=False)
            finally:
                _close_file_objects(fobj for _, fobj, _ in files_list)
            data = response.json()["data"]
        else:
            data = self._query("updateItem", {"input": input_data, "addedAttachments": [],
                                               "showForbiddenImage": True})
        return self._resolve_items(data.get("updateItem"))

    def remove_item(self, item_id: str) -> bool:
        """
        Удаляет лот.

        :param item_id: ID лота.
        :return: `True`, если удаление прошло успешно.
        """
        data = self._query("removeItem", {"id": item_id, "showForbiddenImage": True})
        # На актуальной схеме removeItem возвращает полный RegularItem; раньше — {id,status}.
        removed = data.get("removeItem")
        result = bool(removed)
        if result:
            logger.info("Лот удалён: id=%s", item_id)
        return result

    def remove_items(self, item_ids: list[str]) -> dict[str, bool]:
        """
        Удаляет несколько лотов подряд.

        Ошибка при удалении одного лота не прерывает удаление остальных — она логируется, а для
        этого лота в результате будет `False`.

        :param item_ids: Список ID лотов для удаления.
        :return: Словарь `{item_id: успешность_удаления}` по каждому переданному лоту.
        """
        results: dict[str, bool] = {}
        for item_id in item_ids:
            try:
                results[item_id] = self.remove_item(item_id)
            except Exception:
                logger.warning("Не удалось удалить лот %s", item_id, exc_info=True)
                results[item_id] = False
        succeeded = sum(1 for ok in results.values() if ok)
        logger.info("Массовое удаление лотов: удалено %d из %d", succeeded, len(results))
        return results

    def remove_all_items(self, status=None) -> dict[str, bool]:
        """
        Удаляет все свои лоты (опционально — только лоты с указанным статусом).

        Сначала полностью собирает список ID лотов постранично (`get_my_items`), и только потом
        удаляет их — чтобы удаление лотов по ходу не мешало курсорной пагинации по оставшимся страницам.

        :param status: Фильтр по статусу лота (значение `common.enums.ItemStatuses`), опционально.
            Если не указан — удаляются лоты во всех статусах, включая уже проданные/заблокированные.
        :return: Словарь `{item_id: успешность_удаления}` по каждому найденному лоту.
        """
        item_ids: list[str] = []
        after_cursor: str | None = None
        while True:
            page = self.get_my_items(status=status, count=50, after_cursor=after_cursor)
            if not page or not page.items:
                break
            item_ids.extend(item.id for item in page.items if item and item.id)
            if not page.page_info or not page.page_info.has_next_page:
                break
            next_cursor = page.page_info.end_cursor
            if not next_cursor or next_cursor == after_cursor:
                # Защита от зацикливания при пустом/неподвижном курсоре пагинации.
                break
            after_cursor = next_cursor
        return self.remove_items(item_ids)

    def get_item_priority_statuses(self, item_id: str, price: int) -> list[types.ItemPriorityStatus]:
        """
        Получает доступные статусы приоритета для лота при заданной цене (нужны для `publish_item`
        и `increase_item_priority_status`).

        :param item_id: ID лота.
        :param price: Цена лота (влияет на стоимость статусов приоритета).
        :return: Список доступных статусов приоритета.
        """
        data = self._persisted_query("itemPriorityStatuses", {"itemId": item_id, "price": price})
        raw_list = data.get("itemPriorityStatuses") or []
        return [status for status in (parser.item_priority_status(s) for s in raw_list) if status]

    def publish_item(self, item_id: str, priority_status_id: str | None = None,
                      provider_id: str = "LOCAL") -> types.MyItem | types.Item | None:
        """
        Публикует лот (отправляет на модерацию), опционально оплачивая статус приоритета.

        :param item_id: ID лота.
        :param priority_status_id: ID статуса приоритета (см. `get_item_priority_statuses`).
            Если не указан — используется бесплатный (стандартный) приоритет.
        :param provider_id: ID провайдера оплаты статуса приоритета (см. `common.enums.TransactionProviderIds`).
            По умолчанию `"LOCAL"` — оплата с баланса аккаунта на сайте.
        :return: Опубликованный (или отправленный на модерацию) лот.
        """
        input_data: dict = {"id": item_id, "providerId": provider_id}
        if priority_status_id:
            input_data["priorityStatusId"] = priority_status_id
        data = self._query("publishItem", {"input": input_data, "showForbiddenImage": True})
        return self._resolve_items(data.get("publishItem"))

    def increase_item_priority_status(self, item_id: str, priority_status_id: str,
                                       provider_id: str = "LOCAL") -> types.MyItem | types.Item | None:
        """
        Поднимает лот в списке — покупает более высокий статус приоритета для уже опубликованного лота.

        :param item_id: ID лота.
        :param priority_status_id: ID статуса приоритета (см. `get_item_priority_statuses`).
        :param provider_id: ID провайдера оплаты (см. `common.enums.TransactionProviderIds`).
            По умолчанию `"LOCAL"` — оплата с баланса аккаунта на сайте.
        :return: Лот с обновлённым статусом приоритета.
        """
        if self._runner is not None:
            self._runner._dispatch_hook("PRE_LOTS_RAISE", item_id=item_id)
        input_data = {"id": item_id, "priorityStatusId": priority_status_id, "providerId": provider_id}
        data = self._query("increaseItemPriorityStatus",
                           {"input": input_data, "showForbiddenImage": True})
        result = self._resolve_items(data.get("increaseItemPriorityStatus"))
        if result:
            logger.info("Лот поднят: %r (id=%s), статус приоритета: %s, приоритет теперь: %s",
                        result.name, item_id, priority_status_id, result.priority)
        if self._runner is not None:
            self._runner._dispatch_hook("POST_LOTS_RAISE", item_id=item_id, item=result)
        return result

    def get_my_items(self, status=None, count: int = 20, after_cursor: str | None = None) -> types.ItemProfileList | None:
        """
        Получает список своих лотов.

        :param status: Фильтр по статусу лота — значение `common.enums.ItemStatuses` либо список
            таких значений, опционально.
        :param count: Сколько лотов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :raises NotInitiatedError: Аккаунт не инициализирован (`Account(...).get()` не вызывался).
        :return: Страница списка своих лотов.
        """
        if not self.id:
            raise NotInitiatedError()
        return self.get_items(user_id=self.id, status=status, count=count, after_cursor=after_cursor)

    def get_items(self, user_id: str | None = None, game_id: str | None = None, category_id: str | None = None,
                  status=None, count: int = 20, after_cursor: str | None = None,
                  with_official: bool | None = None) -> types.ItemProfileList | None:
        """
        Получает список лотов (своих или чужих) с фильтрами.

        :param user_id: Фильтр по ID продавца, опционально.
        :param game_id: Фильтр по ID игры, опционально.
        :param category_id: Фильтр по ID категории, опционально.
        :param status: Фильтр по статусу лота — значение `common.enums.ItemStatuses` либо список
            таких значений (сервер принимает массив статусов), опционально.
        :param count: Сколько лотов запросить (размер страницы).
        :param after_cursor: Курсор для пагинации.
        :param with_official: Включать ли официальные лоты (сайт передаёт `withOfficial: false`
            для списка лотов продавца), опционально.
        :return: Страница списка лотов.
        """
        filter_data: dict = {}
        if user_id:
            filter_data["userId"] = user_id
        if game_id:
            filter_data["gameId"] = game_id
        if category_id:
            filter_data["categoryId"] = category_id
        if status is not None:
            # По снятому трафику сервер ждёт массив статусов; одиночное значение оборачиваем.
            statuses = status if isinstance(status, (list, tuple, set)) else [status]
            filter_data["status"] = [s.name if hasattr(s, "name") else s for s in statuses]
        if with_official is not None:
            filter_data["withOfficial"] = with_official
        variables: dict = {"pagination": {"first": count}, "showForbiddenImage": True}
        if filter_data:
            variables["filter"] = filter_data
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._persisted_query("items", variables)
        return parser.item_profile_list(data.get("items"))

    def get_item(self, id: str | None = None, slug: str | None = None) -> types.MyItem | types.Item | None:
        """
        Получает лот по ID или по имени страницы (`slug`).

        :param id: ID лота (взаимоисключающе с `slug`).
        :param slug: Имя страницы лота, как в URL (взаимоисключающе с `id`).
        :return: Лот (`MyItem`, если это лот своего аккаунта, иначе `Item`) либо `None`, если не найден.
        """
        variables: dict = {"hasSupportAccess": False, "showForbiddenImage": True}
        if id:
            variables["id"] = id
        if slug:
            variables["slug"] = slug
        data = self._persisted_query("item", variables)
        return self._resolve_items(data.get("item"))

    # ------------------------------------------------------------------
    # Сделки / отзывы (расширение Фазы 2)
    # ------------------------------------------------------------------

    def create_deal(self, item_id: str, **extra_input) -> types.Transaction | None:
        """
        Создаёт сделку на покупку лота (`createDeal`).

        :param item_id: ID лота.
        :param extra_input: Дополнительные поля `CreateItemDealInput` (obtainingFields и т.п.).
        :return: Транзакция оплаты сделки.
        """
        input_data = {"itemId": item_id, **extra_input}
        data = self._query("createDeal", {"input": input_data})
        result = parser.transaction(data.get("createDeal"))
        if result:
            logger.info("Создана сделка на лот %s → транзакция %s", item_id, result.id)
        return result

    def resolve_deal_problem(self, deal_id: str, **extra_input) -> types.ItemDeal | None:
        """Снимает проблему со сделки (`resolveDealProblem`)."""
        input_data = {"dealId": deal_id, **extra_input}
        data = self._query("resolveDealProblem", {"input": input_data, "showForbiddenImage": True})
        result = parser.item_deal(data.get("resolveDealProblem"))
        if result:
            logger.info("Проблема по сделке %s снята", deal_id)
        return result

    def count_deals(self, filter: dict | None = None) -> int:
        """Возвращает число сделок по фильтру (`countDeals`)."""
        data = self._query("countDeals", {"filter": filter or {}}, idempotent=True)
        return int(data.get("countDeals") or 0)

    def create_review(self, deal_id: str, rating: int, text: str = "",
                      **extra_input) -> types.Review | None:
        """Создаёт отзыв по сделке (`createTestimonial`)."""
        input_data = {"dealId": deal_id, "rating": rating, "text": text, **extra_input}
        data = self._query("createTestimonial", {"input": input_data, "showForbiddenImage": True})
        return parser.review(data.get("createTestimonial"))

    def update_review(self, review_id: str, rating: int | None = None, text: str | None = None,
                      **extra_input) -> types.Review | None:
        """Обновляет отзыв (`updateTestimonial`)."""
        input_data: dict = {"id": review_id, **extra_input}
        if rating is not None:
            input_data["rating"] = rating
        if text is not None:
            input_data["text"] = text
        data = self._query("updateTestimonial", {"input": input_data, "showForbiddenImage": True})
        return parser.review(data.get("updateTestimonial"))

    def remove_review(self, review_id: str) -> types.Review | None:
        """Удаляет отзыв (`removeTestimonial`)."""
        data = self._query("removeTestimonial", {"id": review_id, "showForbiddenImage": True})
        return parser.review(data.get("removeTestimonial"))

    # ------------------------------------------------------------------
    # Чаты (расширение)
    # ------------------------------------------------------------------

    def count_chats(self, filter: dict | None = None) -> int:
        """Число чатов по фильтру (`countChats`)."""
        data = self._query("countChats", {"filter": filter}, idempotent=True)
        return int(data.get("countChats") or 0)

    def get_chats_page(self, count: int = 20, after_cursor: str | None = None,
                       filter: dict | None = None) -> types.ChatList | None:
        """
        Альтернативный список чатов через query `chats` (вместо persisted `userChats`).
        """
        variables: dict = {
            "pagination": {"first": count},
            "filter": filter,
            "hasSupportAccess": False,
        }
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._query("chats", variables, idempotent=True)
        result = parser.chat_list(data.get("chats"))
        if result:
            self._note_chats(result.chats)
        return result

    def update_chat(self, chat_id: str, **fields) -> types.Chat | None:
        """Обновляет чат (`updateChat`) — например `bookmarked`, `status`."""
        input_data = {"id": chat_id, **fields}
        data = self._query("updateChat", {"input": input_data, "showForbiddenImage": True})
        raw = data.get("updateChat")
        # Мутация возвращает урезанный набор полей — добираем через chat(), если есть id.
        return parser.chat(raw) if raw else None

    def remove_chat_message(self, message_id: str) -> dict | None:
        """Удаляет сообщение в чате (`removeChatMessage`)."""
        data = self._query("removeChatMessage", {"id": message_id})
        return data.get("removeChatMessage")

    def update_chat_message(self, message_id: str, text: str | None = None,
                            **extra_input) -> types.ChatMessage | None:
        """Редактирует сообщение (`updateChatMessage`)."""
        input_data: dict = {"id": message_id, **extra_input}
        if text is not None:
            input_data["text"] = text
        data = self._query("updateChatMessage", {"input": input_data, "showForbiddenImage": True})
        return parser.chat_message(data.get("updateChatMessage"))

    def send_bulk_message(self, text: str, selector: dict | None = None,
                          buttons: list | None = None, **extra_input) -> types.ChatBulkMessage | None:
        """
        Создаёт массовую рассылку в чаты (`createChatBulkMessage`).

        :param text: Текст рассылки.
        :param selector: Фильтр аудитории (`CreateChatBulkMessageInput.selector`).
        :param buttons: Кнопки сообщения, опционально.
        """
        input_data: dict = {"text": text, **extra_input}
        if selector is not None:
            input_data["selector"] = selector
        if buttons is not None:
            input_data["buttons"] = buttons
        data = self._query("createChatBulkMessage", {"input": input_data})
        return parser.chat_bulk_message(data.get("createChatBulkMessage"))

    # ------------------------------------------------------------------
    # Финансы
    # ------------------------------------------------------------------

    def get_transactions(self, count: int = 20, after_cursor: str | None = None,
                         filter: dict | None = None) -> types.TransactionList | None:
        """Список транзакций аккаунта (`transactions`)."""
        variables: dict = {
            "pagination": {"first": count},
            "filter": filter or {},
            "hasSupportAccess": False,
        }
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._query("transactions", variables, idempotent=True)
        return parser.transaction_list(data.get("transactions"))

    def get_transaction(self, transaction_id: str) -> types.Transaction | None:
        """Одна транзакция по ID (`transaction`)."""
        data = self._query("transaction", {"id": transaction_id}, idempotent=True)
        return parser.transaction(data.get("transaction"))

    def get_payouts(self, count: int = 20, after_cursor: str | None = None,
                    filter: dict | None = None) -> types.PayoutList | None:
        """Список выплат (`payouts`)."""
        variables: dict = {"pagination": {"first": count}, "filter": filter or {}}
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._query("payouts", variables, idempotent=True)
        return parser.payout_list(data.get("payouts"))

    def request_withdrawal(self, value: int, provider_id: str = "LOCAL",
                           **extra_input) -> types.Transaction | None:
        """Запрос вывода средств (`requestWithdrawal`)."""
        input_data = {"value": value, "providerId": provider_id, **extra_input}
        data = self._query("requestWithdrawal", {"input": input_data})
        result = parser.transaction(data.get("requestWithdrawal"))
        if result:
            logger.info("Запрошен вывод %s (provider=%s) → tx %s", value, provider_id, result.id)
        return result

    def create_payout(self, **input_data) -> types.Payout | None:
        """Создаёт payout (`createPayout`) — поля зависят от провайдера."""
        data = self._query("createPayout", {"input": input_data})
        return parser.payout(data.get("createPayout"))

    def create_payment_url(self, value: int, provider_id: str, **extra_input) -> str | None:
        """Создаёт URL пополнения баланса (`createPaymentURL`)."""
        input_data = {"value": value, "providerId": provider_id, **extra_input}
        data = self._query("createPaymentURL", {"input": input_data})
        return data.get("createPaymentURL")

    def get_verified_cards(self, count: int = 20, after_cursor: str | None = None,
                           filter: dict | None = None) -> types.VerifiedCardList | None:
        """Список верифицированных карт (`verifiedCards`)."""
        variables: dict = {"pagination": {"first": count}}
        if filter is not None:
            variables["filter"] = filter
        if after_cursor:
            variables["pagination"]["after"] = after_cursor
        data = self._query("verifiedCards", variables, idempotent=True)
        return parser.verified_card_list(data.get("verifiedCards"))

    def set_chosen_card(self, card_id: str) -> bool:
        """Выбирает карту для вывода (`setChosenCard`)."""
        data = self._query("setChosenCard", {"input": {"id": card_id}})
        return bool(data.get("setChosenCard"))
