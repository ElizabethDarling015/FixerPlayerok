"""Автоподнятие отмеченных премиум-лотов (по образцу playerok-universal, с лимитами трат).

Поднятие — покупка премиум-статуса лота с баланса (`itemPriorityStatuses` →
`increaseItemPriorityStatus`), стоимость зависит от цены лота. Обычный лот так не поднять,
поэтому в автоподнятии участвуют только премиум-лоты, которые вы отметили.

Режимы (`[autoraise] mode`):

* ``position`` — раз в `check_interval` секунд бот смотрит место каждого отмеченного лота
  (поле `sequence` лота) и поднимает его, если он ниже `position` `streak` проверок подряд
  и с прошлого поднятия прошло не меньше `cooldown` секунд;
* ``interval`` — все отмеченные лоты поднимаются раз в `interval` секунд (отсчёт — с момента
  включения или переключения в этот режим).

Ночной режим (`night_enabled`, окно `night_from`–`night_to`, может переходить через полночь)
подменяет место / интервал / лимит ночными. Лимит трат — на текущее «окно»: днём `day_limit`,
ночью `night_limit`; без ночного режима окно — календарные сутки (лимит `day_limit`). 0 — без
лимита. Кроме лимита, бот не тратит последние `min_balance_reserve` ₽ баланса.
Время — часовой пояс продавца (`[digest] timezone`).

Состояние (траты, время поднятий, серии проверок, места) — в `storage/autoraise.json`,
поэтому лимит и кулдаун переживают перезапуск.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass

from loguru import logger

from .sales_stats import seller_tz
from .settings import STORAGE_DIR

STATE_FILE = os.path.join(STORAGE_DIR, "autoraise.json")
#: Как часто цикл просыпается проверить, не пора ли что-то делать.
TICK = 5.0
#: Пауза между запросами лотов при проверке мест (как в universal).
REQUEST_GAP = 1.0
#: Сколько дней хранить историю трат.
SPENDS_KEEP_DAYS = 14


# ----------------------------------------------------------------------
# Время: день / ночь и окно лимита
# ----------------------------------------------------------------------

def _hm(value: str) -> datetime.time:
    h, m = (int(x) for x in value.split(":"))
    return datetime.time(h, m)


def is_night(cfg, now: datetime.datetime) -> bool:
    if not cfg.night_enabled:
        return False
    start, end = _hm(cfg.night_from), _hm(cfg.night_to)
    t = now.time().replace(second=0, microsecond=0)
    if start == end:
        return False
    if start < end:
        return start <= t < end
    return t >= start or t < end


def _last_at(now: datetime.datetime, t: datetime.time) -> datetime.datetime:
    """Последний момент `t` (сегодня или вчера), не позже `now`."""
    at = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    return at if at <= now else at - datetime.timedelta(days=1)


def _next_at(now: datetime.datetime, t: datetime.time) -> datetime.datetime:
    at = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    return at if at > now else at + datetime.timedelta(days=1)


@dataclass
class Window:
    kind: str                     # "day" / "night" / "all"
    start: datetime.datetime
    end: datetime.datetime
    limit: int                    # 0 — без лимита


def current_window(cfg, now: datetime.datetime) -> Window:
    if not cfg.night_enabled or cfg.night_from == cfg.night_to:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return Window("all", start, start + datetime.timedelta(days=1), cfg.day_limit)
    if is_night(cfg, now):
        return Window("night", _last_at(now, _hm(cfg.night_from)), _next_at(now, _hm(cfg.night_to)),
                      cfg.night_limit)
    return Window("day", _last_at(now, _hm(cfg.night_to)), _next_at(now, _hm(cfg.night_from)), cfg.day_limit)


def target_position(cfg, now) -> int:
    return cfg.night_position if is_night(cfg, now) else cfg.position


def current_interval(cfg, now) -> float:
    return cfg.night_interval if is_night(cfg, now) else cfg.interval


def premium_status(statuses):
    """Статус «премиум» из `itemPriorityStatuses` (им и поднимают)."""
    for status in statuses or []:
        if getattr(getattr(status, "type", None), "name", None) == "PREMIUM":
            return status
    return next((s for s in statuses or [] if (getattr(s, "price", 0) or 0) > 0), None)


def _is_premium(item) -> bool:
    return getattr(getattr(item, "priority", None), "name", None) == "PREMIUM"


def _is_active(item) -> bool:
    return getattr(getattr(item, "status", None), "name", None) == "APPROVED"


def position_of(item) -> int | None:
    seq = getattr(item, "sequence", None)
    return seq if seq is not None else getattr(item, "priority_position", None)


# ----------------------------------------------------------------------
# Сервис
# ----------------------------------------------------------------------

class AutoRaise:
    def __init__(self, fixer, state_file: str | None = STATE_FILE):
        self.fixer = fixer
        self._state_file = state_file
        self.state = self._load()
        self._busy = False

    # --- состояние ---

    def _load(self) -> dict:
        data: dict = {}
        if self._state_file:
            with suppress(Exception):
                if os.path.isfile(self._state_file):
                    with open(self._state_file, encoding="utf-8") as f:
                        data = json.load(f) or {}
        data.setdefault("spends", [])            # [[ts, ₽, item_id], …]
        data.setdefault("last_raised", {})       # item_id → ts
        data.setdefault("positions", {})         # item_id → {name, pos, streak, note, checked_at}
        data.setdefault("names", {})             # item_id → название (для экрана)
        data.setdefault("last_check", 0.0)
        data.setdefault("last_interval_run", 0.0)
        data.setdefault("limit_notified", "")
        data.setdefault("balance_notified", 0.0)
        return data

    def save(self) -> None:
        if not self._state_file:
            return
        cutoff = time.time() - SPENDS_KEEP_DAYS * 86400
        self.state["spends"] = [s for s in self.state["spends"] if s[0] >= cutoff]
        with suppress(Exception):
            os.makedirs(os.path.dirname(self._state_file) or ".", exist_ok=True)
            tmp = self._state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False)
            os.replace(tmp, self._state_file)

    # --- удобства для экрана ---

    @property
    def cfg(self):
        return self.fixer.settings.autoraise

    @property
    def enabled(self) -> bool:
        return bool(self.fixer.settings.modules.autoraise)

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(seller_tz(self.fixer.settings)).replace(tzinfo=None)

    def local(self, ts: float) -> datetime.datetime:
        """Метка времени → время продавца (без пояса)."""
        return datetime.datetime.fromtimestamp(ts, seller_tz(self.fixer.settings)).replace(tzinfo=None)

    def _ts(self, dt: datetime.datetime) -> float:
        tz = seller_tz(self.fixer.settings)
        return dt.replace(tzinfo=tz).timestamp() if tz else dt.timestamp()

    def spent_in(self, window: Window) -> int:
        start = self._ts(window.start)
        return sum(int(s[1]) for s in self.state["spends"] if s[0] >= start)

    def window(self) -> Window:
        return current_window(self.cfg, self.now())

    def reset_interval_clock(self) -> None:
        """Отсчёт режима «по интервалу» — с этого момента (включение / смена режима)."""
        self.state["last_interval_run"] = time.time()
        self.save()

    def next_interval_run(self) -> datetime.datetime | None:
        last = self.state.get("last_interval_run") or 0
        if not last:
            return None
        return self.local(last + current_interval(self.cfg, self.now()))

    def set_marked(self, item_id: str, name: str | None, on: bool) -> None:
        items = list(self.cfg.items)
        if on and item_id not in items:
            items.append(item_id)
        if not on and item_id in items:
            items.remove(item_id)
            self.state["positions"].pop(item_id, None)
        self.cfg.items = items
        if name:
            self.state["names"][item_id] = name
        self.save()

    # --- цикл ---

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[autoraise] Ошибка цикла автоподнятия")
            await asyncio.sleep(TICK)

    async def tick(self) -> None:
        fixer = self.fixer
        if (not self.enabled or self._busy or fixer.account is None
                or not getattr(fixer, "playerok_connected", False) or not self.cfg.items):
            return
        self._busy = True
        try:
            now_ts = time.time()
            if self.cfg.mode == "position":
                if now_ts - (self.state["last_check"] or 0) >= self.cfg.check_interval:
                    await self.check_positions()
            else:
                last = self.state["last_interval_run"] or 0
                if not last:
                    self.reset_interval_clock()
                elif now_ts - last >= current_interval(self.cfg, self.now()):
                    await self.raise_by_interval()
        finally:
            self._busy = False

    async def _get_item(self, item_id: str):
        return await asyncio.to_thread(self.fixer.account.get_item, item_id)

    async def check_positions(self) -> None:
        cfg = self.cfg
        now = self.now()
        target = target_position(cfg, now)
        self.state["last_check"] = time.time()
        for index, item_id in enumerate(list(cfg.items)):
            if index:
                await asyncio.sleep(REQUEST_GAP)
            entry = self.state["positions"].setdefault(item_id, {"streak": 0})
            entry["checked_at"] = time.time()
            try:
                item = await self._get_item(item_id)
            except Exception as exc:
                logger.warning("[autoraise] Лот {} не загрузился: {}", item_id, exc)
                entry["note"] = "error"
                continue
            if item is None:
                entry.update(note="not_found", pos=None, streak=0)
                continue
            entry["name"] = item.name
            self.state["names"][item_id] = item.name
            if not _is_active(item):
                entry.update(note="not_active", pos=None, streak=0)
                continue
            if not _is_premium(item):
                entry.update(note="not_premium", pos=None, streak=0)
                continue
            pos = position_of(item)
            entry.update(note=None, pos=pos)
            if pos is None:
                entry["streak"] = 0
                continue
            entry["streak"] = entry.get("streak", 0) + 1 if pos > target else 0
            if entry["streak"] < cfg.streak:
                continue
            last = self.state["last_raised"].get(item_id, 0)
            if time.time() - last < cfg.cooldown:
                continue
            if await self.raise_item(item, before=pos):
                entry.update(streak=0, pos=1)
        self.save()

    async def raise_by_interval(self) -> None:
        self.state["last_interval_run"] = time.time()
        for index, item_id in enumerate(list(self.cfg.items)):
            if index:
                await asyncio.sleep(REQUEST_GAP)
            try:
                item = await self._get_item(item_id)
            except Exception as exc:
                logger.warning("[autoraise] Лот {} не загрузился: {}", item_id, exc)
                continue
            if item is None or not _is_active(item) or not _is_premium(item):
                continue
            self.state["names"][item_id] = item.name
            await self.raise_item(item, before=position_of(item))
        self.save()

    async def raise_item(self, item, before: int | None = None) -> bool:
        """Поднимает лот, если позволяют лимит окна и баланс. True — поднят."""
        fixer = self.fixer
        account = fixer.account
        notifier = getattr(fixer, "notifier", None)
        name = getattr(item, "name", None) or item.id
        try:
            statuses = await asyncio.to_thread(account.get_item_priority_statuses, item.id, item.price)
        except Exception as exc:
            logger.warning("[autoraise] Цены поднятия «{}» не загрузились: {}", name, exc)
            return False
        status = premium_status(statuses)
        if status is None:
            logger.warning("[autoraise] Для «{}» Playerok не предложил премиум-статус", name)
            return False
        price = int(getattr(status, "price", 0) or 0)

        window = self.window()
        spent = self.spent_in(window)
        if window.limit and spent + price > window.limit:
            key = f"{window.kind}:{window.start:%Y-%m-%d %H:%M}"
            if self.state["limit_notified"] != key:
                self.state["limit_notified"] = key
                self.save()
                logger.info("[autoraise] Лимит {} исчерпан: {} из {} ₽", window.kind, spent, window.limit)
                if notifier is not None:
                    await notifier.notify_raise_limit(spent=spent, limit=window.limit, kind=window.kind,
                                                      until=window.end.strftime("%H:%M"))
            return False

        with suppress(Exception):
            await asyncio.to_thread(account.get_balance)
        balance = getattr(getattr(account, "profile", None), "balance", None)
        available = getattr(balance, "available", None)
        if available is not None and available - self.cfg.min_balance_reserve < price:
            if time.time() - (self.state["balance_notified"] or 0) > 3600:
                self.state["balance_notified"] = time.time()
                self.save()
                if notifier is not None:
                    await notifier.notify_raise_no_balance(item=name, price=price, available=available)
            logger.info("[autoraise] Не хватает баланса на «{}»: нужно {} ₽, доступно {} ₽", name, price, available)
            return False

        try:
            await asyncio.to_thread(account.increase_item_priority_status, item.id, status.id,
                                    keep_in_sale=getattr(item, "keep_in_sale", None))
        except Exception as exc:
            logger.warning("[autoraise] «{}» не поднят: {}", name, exc)
            if notifier is not None:
                await notifier.notify_error(f"Автоподнятие «{name}»: {exc}")
            return False

        now_ts = time.time()
        self.state["spends"].append([now_ts, price, item.id])
        self.state["last_raised"][item.id] = now_ts
        self.save()
        spent += price
        logger.success("[autoraise] «{}» поднят ({} → 1) за {} ₽", name, before if before is not None else "?", price)
        if notifier is not None:
            await notifier.notify_item_raised(item=name, before=before, spent=price, total=spent,
                                              limit=window.limit, kind=window.kind)
        return True
