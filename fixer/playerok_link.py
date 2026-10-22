"""
Связь с Playerok: фоновое подключение и слежение за обрывами.

**Старт без Playerok.** Если при обычном запуске (без `--offline`) Playerok не ответил, бот не
завершается, а работает как в оффлайне (только Telegram-панель) и подключается в фоне:

- одна попытка = `connect_playerok(attempts=1)` (внутри библиотека сама повторяет запрос
  до 3 раз, это до ~1,5 мин без сети);
- между попытками пауза: 30 с → 1 мин → 2 мин → 5 мин → дальше каждые 5 мин;
- админам приходит отдельное сообщение «⚠️ Playerok недоступен» с кнопками
  «🔄 Повторить подключение» и «❌ Закрыть»;
- «🔄 Повторить» обрывает текущую попытку (или паузу) и сразу начинает новую; расписание пауз
  продолжается с того же места;
- после подключения сообщение превращается в «✅ Успешное подключение» с «❌ Закрыть»
  (если его уже закрыли — приходит новое).

**Обрыв во время работы.** Раз в 15 с смотрим, когда Playerok последний раз отвечал
(`Account.last_response_at`). Если ответа нет больше 3 минут и за это время были сетевые
ошибки — «⚠️ Потеряна связь с Playerok» с кнопками «📄 Логи» и «❌ Закрыть». Переподключается
библиотека сама (поллинг и WebSocket); когда Playerok снова ответит, сообщение превращается
в «✅ Связь восстановлена» с «❌ Закрыть» (закрытое — новым сообщением).
"""
from __future__ import annotations

import asyncio
import contextlib
import time

from loguru import logger

#: Паузы между попытками подключения, с; после последней — она же до победного.
RECONNECT_DELAYS: tuple[int, ...] = (30, 60, 120, 300)
#: Сколько секунд без ответа Playerok считается обрывом связи.
LOST_AFTER = 180
#: Как часто проверять связь во время работы, с.
CHECK_EVERY = 15

Messages = list[tuple[int, int]]


class PlayerokLink:
    """Фоновое подключение к Playerok и уведомления о его состоянии."""

    def __init__(self, fixer):
        self.fixer = fixer
        self._loop_task: asyncio.Task | None = None
        self._attempt_task: asyncio.Task | None = None
        self._wake: asyncio.Event | None = None
        self._retry_requested = False
        #: Сообщения «⚠️ Playerok недоступен» — их правим на «✅ Успешное подключение».
        self.unavailable_messages: Messages = []
        #: Сообщения «⚠️ Потеряна связь» — их правим на «✅ Связь восстановлена».
        self.lost_messages: Messages = []
        self.lost_at: float | None = None

    # ------------------------------------------------------------------
    # Фоновое подключение
    # ------------------------------------------------------------------

    @property
    def reconnecting(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    def start_reconnect(self, reason: str | None = None, notify: bool = True) -> None:
        """Запускает фоновое подключение (если ещё не идёт)."""
        if self.reconnecting or self.fixer.playerok_connected:
            return
        self._wake = asyncio.Event()
        self._loop_task = self.fixer.spawn(self._reconnect_loop(reason, notify))

    async def _reconnect_loop(self, reason: str | None, notify: bool) -> None:
        notifier = self.fixer.notifier
        if notify and notifier is not None:
            try:
                self.unavailable_messages = await notifier.notify_playerok_unavailable(reason)
            except Exception:
                logger.exception("Не удалось отправить уведомление «Playerok недоступен»")

        step = 0
        while not self.fixer.playerok_connected:
            self._attempt_task = asyncio.ensure_future(self.fixer.connect_playerok(attempts=1))
            try:
                result = await self._attempt_task
            except asyncio.CancelledError:
                current = asyncio.current_task()
                if self._retry_requested and not (current and current.cancelling()):
                    # «🔄 Повторить»: прерванную попытку бросаем, новую — сразу и с новым Account
                    # (старый ещё может ждать ответа в своём потоке).
                    self._retry_requested = False
                    self.fixer.account = None
                    logger.info("Playerok: попытка прервана кнопкой «Повторить» — начинаю заново")
                    continue
                raise
            finally:
                self._attempt_task = None
            if result.get("ok"):
                break

            delay = RECONNECT_DELAYS[min(step, len(RECONNECT_DELAYS) - 1)]
            step += 1
            logger.info("Playerok недоступен — следующая попытка через {} с", delay)
            self._wake.clear()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._wake.wait(), delay)
            self._retry_requested = False

        logger.success("Playerok подключён после фоновых попыток")
        if notifier is not None:
            try:
                await notifier.resolve_playerok_alert(self.unavailable_messages, "notif_playerok_connected")
            except Exception:
                logger.exception("Не удалось отправить уведомление «Успешное подключение»")
        self.unavailable_messages = []

    def retry_now(self, origin: tuple[int, int] | None = None) -> str:
        """
        Кнопка «🔄 Повторить подключение».

        :param origin: (chat_id, message_id) сообщения с кнопкой — его и превратим в «✅».
        :return: "connected" — уже подключено; "retry" — попытка начата заново.
        """
        if self.fixer.playerok_connected:
            return "connected"
        if origin is not None and origin not in self.unavailable_messages:
            self.unavailable_messages.append(origin)
        if not self.reconnecting:
            # Например, бот перезапущен, а кнопку нажали в старом сообщении.
            self.start_reconnect(notify=False)
            return "retry"
        self._retry_requested = True
        if self._attempt_task is not None and not self._attempt_task.done():
            self._attempt_task.cancel()
        elif self._wake is not None:
            self._wake.set()
        return "retry"

    def on_connected(self) -> None:
        """Подключились (в том числе кнопкой в «Системе») — фоновый цикл выходит из паузы."""
        self.lost_at = None
        if self._wake is not None:
            self._wake.set()

    # ------------------------------------------------------------------
    # Слежение за связью во время работы
    # ------------------------------------------------------------------

    async def watch(self) -> None:
        """Бесконечная проверка связи (запускается один раз при старте Fixer)."""
        while True:
            await asyncio.sleep(CHECK_EVERY)
            try:
                await self.check()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ошибка проверки связи с Playerok")

    async def check(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        account = self.fixer.account
        notifier = self.fixer.notifier
        if not self.fixer.playerok_connected or account is None:
            # Отключились вручную или ждём фонового подключения — это не «обрыв».
            self.lost_at = None
            return
        ok_at = getattr(account, "last_response_at", None)
        err_at = getattr(account, "last_network_error_at", None)
        if ok_at is None:
            return

        if self.lost_at is None:
            if err_at is not None and err_at > ok_at and now - ok_at > LOST_AFTER:
                self.lost_at = now
                logger.warning("Нет ответа от Playerok больше {} с — сообщаю о потере связи", LOST_AFTER)
                if notifier is not None:
                    self.lost_messages = await notifier.notify_playerok_lost()
        elif ok_at > self.lost_at:
            self.lost_at = None
            logger.success("Связь с Playerok восстановлена")
            if notifier is not None:
                await notifier.resolve_playerok_alert(self.lost_messages, "notif_playerok_restored")
            self.lost_messages = []
