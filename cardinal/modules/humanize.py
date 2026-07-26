"""
«Человеческие» задержки перед автоответами (секция `[humanize]` в `configs/main.toml`).

Живой продавец не отвечает мгновенно: он читает сообщение и печатает ответ — тем дольше,
чем ответ длиннее. Мгновенные ответы с точностью до миллисекунд в любое время суток —
характерный признак автоматизации. Хелперы ниже дают случайную задержку в пределах
`[reply_delay_min, reply_delay_max]`, смещённую пропорционально длине отправляемого текста.

Используется автоответчиком и приветствием. Авто-выдача товара задержку НЕ использует —
покупатель ждёт оплаченный товар, выдача должна быть мгновенной.
"""
from __future__ import annotations

import asyncio
import random

#: Длина текста (в символах), при которой опорная точка задержки достигает `reply_delay_max`.
FULL_DELAY_TEXT_LENGTH = 200

#: Относительный разброс случайности вокруг опорной точки (доля от диапазона max-min).
_SPREAD = 0.25


def compute_reply_delay(settings, text: str) -> float:
    """
    Считает задержку перед отправкой автоответа, в секундах.

    Формула: опорная точка `min + (max - min) * clamp(len(text) / 200, 0..1)` (короткий текст —
    ближе к `min`, длинный — ближе к `max`), случайность — `uniform` вокруг этой точки
    (±25% диапазона), итог зажимается в `[min, max]`.

    :param settings: `HumanizeSettings` (поля `reply_delay_min`/`reply_delay_max`) или `None`.
    :param text: Текст, который будет отправлен.
    :return: Задержка в секундах; `0.0`, если задержка выключена (`0`/`0` или нет настроек).
    """
    if settings is None:
        return 0.0
    delay_min = settings.reply_delay_min
    delay_max = settings.reply_delay_max
    if delay_max <= 0:
        return 0.0
    span = delay_max - delay_min
    anchor = delay_min + span * min(len(text or "") / FULL_DELAY_TEXT_LENGTH, 1.0)
    spread = span * _SPREAD
    delay = random.uniform(anchor - spread, anchor + spread)
    return max(delay_min, min(delay, delay_max))


async def sleep_before_reply(settings, text: str) -> float:
    """
    Выдерживает «человеческую» паузу перед отправкой автоответа (`asyncio.sleep`).

    :param settings: `HumanizeSettings` или `None` (нет настроек — без задержки).
    :param text: Текст, который будет отправлен (влияет на длину паузы).
    :return: Фактическая задержка в секундах (`0.0` — sleep не вызывался).
    """
    delay = compute_reply_delay(settings, text)
    if delay > 0:
        await asyncio.sleep(delay)
    return delay
