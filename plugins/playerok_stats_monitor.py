"""
Плагин мониторинга ниш Playerok: отслеживание товаров, анализ топ продавцов.
"""
from __future__ import annotations

import asyncio
import contextlib
import csv
import html
import io
import json
import os
import re
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from playerokapi.account import Account
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

# Метаданные плагина
NAME = "Мониторинг ниш Playerok"
VERSION = "1.0.0"
DESCRIPTION = "Отслеживание товаров в нишах, анализ топ продавцов"
CREDITS = "FixerPlayerok"
UUID = "b7f9b6f0-3e2f-4c9b-8a1e-statsmonitor01"

# Действия в меню работы с плагином
MENU_ACTIONS = [
    ("▶️ Начать работу", "stats:start"),
    ("🧪 Тест плагина", "stats:test"),
    ("⚙️ Настройки", "stats:settings"),
    ("📋 Активные задачи", "stats:jobs"),
]

# Глобальные переменные модуля
_bot = None
_monitor: Optional["StatsMonitor"] = None
_manager = None

# Пути для хранения данных
STORAGE_DIR = Path("storage/stats_monitor")
JOBS_DIR = STORAGE_DIR / "jobs"


# ---------------------------------------------------------------------------
# Модели данных
# ---------------------------------------------------------------------------

@dataclass
class MonitoringJob:
    """Задача мониторинга ниши."""
    job_id: str
    chat_id: int
    niche_url: str
    game_slug: str
    category_slug: Optional[str]
    duration_hours: int
    start_time: datetime
    end_time: datetime
    status: str
    products: dict[str, dict] = field(default_factory=dict)
    sellers: dict[str, dict] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status == "running" and datetime.now() < self.end_time


# ---------------------------------------------------------------------------
# Хранилище задач
# ---------------------------------------------------------------------------

class MonitoringStorage:
    """Управление задачами мониторинга."""

    def __init__(self):
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        JOBS_DIR.mkdir(exist_ok=True)
        self._jobs: dict[str, MonitoringJob] = {}
        self._load_jobs()

    def _load_jobs(self):
        """Загрузка активных задач из файлов."""
        for job_file in JOBS_DIR.glob("*.json"):
            try:
                with open(job_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                job = MonitoringJob(
                    job_id=data["job_id"],
                    chat_id=data["chat_id"],
                    niche_url=data["niche_url"],
                    game_slug=data["game_slug"],
                    category_slug=data.get("category_slug"),
                    duration_hours=data["duration_hours"],
                    start_time=datetime.fromisoformat(data["start_time"]),
                    end_time=datetime.fromisoformat(data["end_time"]),
                    status=data["status"],
                    products=data.get("products", {}),
                    sellers=data.get("sellers", {}),
                )
                if job.is_active():
                    self._jobs[job.job_id] = job
            except Exception as e:
                logger.exception(f"Ошибка загрузки задачи {job_file}: {e}")

    def _save_job(self, job: MonitoringJob):
        """Сохранение задачи в файл."""
        job_file = JOBS_DIR / f"{job.job_id}.json"
        data = {
            "job_id": job.job_id,
            "chat_id": job.chat_id,
            "niche_url": job.niche_url,
            "game_slug": job.game_slug,
            "category_slug": job.category_slug,
            "duration_hours": job.duration_hours,
            "start_time": job.start_time.isoformat(),
            "end_time": job.end_time.isoformat(),
            "status": job.status,
            "products": job.products,
            "sellers": job.sellers,
        }
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_job(self, chat_id: int, niche_url: str, game_slug: str, 
                   category_slug: Optional[str], duration_hours: int) -> MonitoringJob:
        """Создание новой задачи мониторинга."""
        job_id = f"job_{int(time.time())}_{chat_id}"
        now = datetime.now()
        job = MonitoringJob(
            job_id=job_id,
            chat_id=chat_id,
            niche_url=niche_url,
            game_slug=game_slug,
            category_slug=category_slug,
            duration_hours=duration_hours,
            start_time=now,
            end_time=now + timedelta(hours=duration_hours),
            status="running",
        )
        self._jobs[job.job_id] = job
        self._save_job(job)
        return job

    def get_job(self, job_id: str) -> Optional[MonitoringJob]:
        return self._jobs.get(job_id)

    def get_active_jobs_for_chat(self, chat_id: int) -> list[MonitoringJob]:
        return [j for j in self._jobs.values() if j.chat_id == chat_id and j.is_active()]

    def update_job(self, job: MonitoringJob):
        self._save_job(job)

    def complete_job(self, job: MonitoringJob):
        job.status = "completed"
        self._save_job(job)
        self._jobs.pop(job.job_id, None)

    def cancel_job(self, job: MonitoringJob):
        job.status = "cancelled"
        self._save_job(job)
        self._jobs.pop(job.job_id, None)

    def delete_job(self, job_id: str) -> bool:
        """Полностью удаляет задачу, включая файл на диске."""
        self._jobs.pop(job_id, None)
        job_file = JOBS_DIR / f"{job_id}.json"
        if job_file.exists():
            job_file.unlink()
            return True
        return False



# ---------------------------------------------------------------------------
# Парсер ниши через playerokapi
# ---------------------------------------------------------------------------

class NicheParser:
    """
    Парсинг каталога ниши через публичный GraphQL-запрос `items`.

    Архитектура:
      1. Загружаем кэш запроса (текст + sha256 + URL бандла) из
         storage/stats_monitor/items_query_cache.json.
      2. Если кэша нет или он устарел (CACHE_TTL) — обновляем:
         - качаем HTML страницы каталога,
         - находим URL JS-бандла _app-...js,
         - скачиваем бандл и извлекаем из него текст `query items(...) {...}`,
         - считаем sha256 и сохраняем в кэш.
      3. При ошибке PersistedQueryNotFound / 403 принудительно обновляем кэш
         (значит Playerok задеплоил новый фронтенд).

    Хэш нигде не захардкожен — вычисляется на лету из живого текста запроса,
    поэтому решение переживает любые обновления сайта.
    """

    CACHE_FILE = STORAGE_DIR / "items_query_cache.json"
    CACHE_TTL_HOURS = 24          # плановое обновление раз в сутки
    BUNDLE_NAME_RE = r"/_next/static/chunks/pages/_app-[^\"']+\.js"
    QUERY_NAME = "items"

    def __init__(self, account):
        self.account = account
        self._cache = self._load_cache()
        if self._cache is None or self._cache_is_stale():
            try:
                asyncio.get_event_loop().create_task(self._refresh_cache())
            except RuntimeError:
                pass  # event loop ещё нет — обновим лениво при первом запросе

    # ------------------------------------------------------------------
    # Кэш
    # ------------------------------------------------------------------

    def _load_cache(self) -> Optional[dict]:
        if not self.CACHE_FILE.exists():
            return None
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[NicheParser] не удалось загрузить кэш запроса: {e}")
            return None

    def _cache_is_stale(self) -> bool:
        if not self._cache:
            return True
        try:
            updated = datetime.fromisoformat(self._cache.get("updated_at", "1970-01-01"))
            return (datetime.now() - updated).total_seconds() > self.CACHE_TTL_HOURS * 3600
        except Exception:
            return True

    def _save_cache(self, text: str, sha256: str, bundle_url: str) -> None:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "query_text": text,
            "sha256": sha256,
            "bundle_url": bundle_url,
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._cache = payload
            logger.info(f"[NicheParser] кэш запроса обновлён (sha256={sha256[:12]}…)")
        except Exception as e:
            logger.warning(f"[NicheParser] не удалось сохранить кэш: {e}")

    # ------------------------------------------------------------------
    # Извлечение запроса из JS-бандла
    # ------------------------------------------------------------------

    async def _refresh_cache(self) -> None:
        """Скачивает HTML каталога → находит _app-бандл → извлекает текст query items."""
        try:
            # Берём любую реальную страницу каталога — бандл на всех один
            sample_url = "https://playerok.com/cgpt/subscription"
            page = await asyncio.to_thread(
                self.account.request, "get", sample_url,
                {"accept": "text/html,application/xhtml+xml"},
            )
            page_text = page.text
        except Exception as e:
            logger.warning(f"[NicheParser] не удалось скачать HTML: {e}")
            return

        bundle_path = self._find_bundle(page_text)
        if not bundle_path:
            logger.warning("[NicheParser] не нашёл _app-бандл на странице")
            return

        try:
            bundle_url = ("https://playerok.com" + bundle_path
                          if bundle_path.startswith("/") else bundle_path)
            js = (await asyncio.to_thread(
                self.account.request, "get", bundle_url, {"accept": "*/*"},
            )).text
        except Exception as e:
            logger.warning(f"[NicheParser] не удалось скачать бандл: {e}")
            return

        query_text = self._extract_query(js, self.QUERY_NAME)
        if not query_text:
            logger.warning(f"[NicheParser] не нашёл `query {self.QUERY_NAME}` в бандле {bundle_path}")
            return

        sha = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        self._save_cache(query_text, sha, bundle_url)

    def _find_bundle(self, html: str) -> Optional[str]:
        m = re.search(self.BUNDLE_NAME_RE, html)
        return m.group(0) if m else None

    @staticmethod
    def _extract_query(js: str, name: str) -> Optional[str]:
        """
        Находит в минифицированном JS полный текст `query <name>(...) { ... }`
        с правильным учётом вложенных скобок (включая `(...)` параметров и `{...}` тела).
        """
        marker = f"query {name}"
        i = js.find(marker)
        if i < 0:
            return None
        # Идём вперёд до первой открывающей скобки — она либо у параметров, либо у тела.
        j = i + len(marker)
        # Пропускаем параметры (...) если они есть.
        if j < len(js) and js[j] == "(":
            depth = 1
            j += 1
            while j < len(js) and depth:
                ch = js[j]
                if ch == "(": depth += 1
                elif ch == ")": depth -= 1
                j += 1
        # Теперь должно быть тело { ... }
        while j < len(js) and js[j] in " \t\n\r":
            j += 1
        if j >= len(js) or js[j] != "{":
            return None
        depth = 1
        k = j + 1
        while k < len(js) and depth:
            ch = js[k]
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            k += 1
        return js[i:k]

    # ------------------------------------------------------------------
    # Основной парсинг
    # ------------------------------------------------------------------

    async def parse_niche(self, game_slug: str, category_slug: Optional[str] = None,
                          max_pages: int = 3) -> list[dict]:
        logger.info(f"[NicheParser] аккаунт={self.account.username}, "
                    f"ниша={game_slug}/{category_slug or '-'}")
        if self._cache is None or self._cache_is_stale():
            await self._refresh_cache()
        if self._cache is None:
            logger.error("[NicheParser] нет кэша запроса — парсинг невозможен")
            return []

        products: list[dict] = []
        try:
            game = await asyncio.to_thread(self.account.get_game, slug=game_slug)
            if not game:
                logger.error(f"Игра не найдена: {game_slug}")
                return []

            category_id = None
            if category_slug:
                category = await asyncio.to_thread(
                    self.account.get_game_category, game_id=game.id, slug=category_slug
                )
                if category:
                    category_id = category.id

            after = None
            for page in range(1, max_pages + 1):
                try:
                    nodes, after, has_next = await self._fetch_public_items(
                        game.id, category_id, after, force_refresh=False
                    )
                except Exception as e:
                    err = str(e)
                    if "PersistedQueryNotFound" in err or "403" in err:
                        logger.warning("[NicheParser] сервер не узнал хэш — обновляю кэш из бандла")
                        await self._refresh_cache()
                        if self._cache is None:
                            raise
                        nodes, after, has_next = await self._fetch_public_items(
                            game.id, category_id, after, force_refresh=False
                        )
                    else:
                        raise

                for node in nodes:
                    item = self._normalize_node(node, game_slug, category_slug)
                    if item:
                        products.append(item)
                logger.info(f"[public items] стр. {page}: {len(nodes)} лотов (всего {len(products)})")
                if not has_next or not after:
                    break
                await asyncio.sleep(1)
        except Exception as e:
            logger.exception(f"Ошибка парсинга ниши {game_slug}/{category_slug}: {e}")

        logger.info(f"Всего найдено товаров: {len(products)}")
        return products

    async def _fetch_public_items(self, game_id, category_id, after, force_refresh=False):
        """Использует библиотеку playerokapi для отправки persisted-запроса."""
        variables = {
            "pagination": {"first": 24},
            "filter": {"gameId": game_id, "status": ["APPROVED"]},
            "sort": None,
        }
        if category_id:
            variables["filter"]["gameCategoryId"] = category_id
        if after:
            variables["pagination"]["after"] = after

        data = await asyncio.to_thread(
            self.account._persisted_query, "items", variables
        )
        
        items_data = data.get("items") or {}
        edges = items_data.get("edges") or []
        nodes = [e.get("node") for e in edges if e.get("node")]
        page_info = items_data.get("pageInfo") or {}
        return nodes, page_info.get("endCursor"), bool(page_info.get("hasNextPage"))

        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self._cache["sha256"],
            }
        }
        payload = {
            "operationName": "items",
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(extensions, separators=(",", ":")),
        }
        headers = {
            "x-gql-op": "items",
            "x-gql-path": "/[brand-slug]/[brand-category-slug]",
            "apollographql-client-name": "web",
            "apollo-require-preflight": "true",
            "accept": "*/*",
        }
        resp = await asyncio.to_thread(
            self.account.request, "get", "https://playerok.com/graphql", headers, payload
        )
        data = (resp.json().get("data") or {}).get("items") or {}
        edges = data.get("edges") or []
        nodes = [e.get("node") for e in edges if e.get("node")]
        page_info = data.get("pageInfo") or {}
        return nodes, page_info.get("endCursor"), bool(page_info.get("hasNextPage"))

    def _normalize_node(self, node: dict, game_slug: str, category_slug: Optional[str]) -> Optional[dict]:
        pid = node.get("id")
        if not pid:
            return None
        user = node.get("user") or {}
        username = user.get("username")
        slug = node.get("slug")
        return {
            "product_id": pid,
            "slug": slug,
            "url": f"https://playerok.com/{game_slug}/{category_slug + '/' if category_slug else ''}{slug}",
            "title": node.get("name") or "Без названия",
            "price": node.get("price") or 0,
            "raw_price": node.get("rawPrice") or 0,
            "seller_id": user.get("id"),
            "seller_name": username or "Неизвестно",
            "seller_url": f"https://playerok.com/profile/{username}" if username else "",
            "seller_rating": user.get("rating"),
            "seller_reviews": user.get("testimonialCounter"),
            "status": node.get("status") or "APPROVED",
            "created_at": node.get("createdAt"),
            "approval_date": node.get("approvalDate"),
            "first_seen": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Фоновая задача мониторинга
# ---------------------------------------------------------------------------

class MonitoringTask:
    """Фоновая задача мониторинга ниши."""

    def __init__(self, job: MonitoringJob, parser: NicheParser, bot: Bot, storage: MonitoringStorage):
        self.job = job
        self.parser = parser
        self.bot = bot
        self.storage = storage
        self._task: Optional[asyncio.Task] = None

    async def run(self):
        """Основной цикл мониторинга."""
        logger.info(f"Запущен мониторинг {self.job.job_id}: {self.job.niche_url}")

        await self._scan_niche()

        check_interval = 300
        while self.job.is_active():
            await asyncio.sleep(check_interval)
            
            if not self.job.is_active():
                break

            await self._check_updates()
            self.storage.update_job(self.job)

        self.storage.complete_job(self.job)
        await self._send_report()
        logger.info(f"Завершён мониторинг {self.job.job_id}")

    async def _scan_niche(self):
        """Начальный парсинг ниши."""
        products = await self.parser.parse_niche(
            self.job.game_slug, 
            self.job.category_slug
        )
        
        for product in products:
            pid = product["product_id"]
            self.job.products[pid] = product
            
            seller_id = product["seller_id"]
            if seller_id and seller_id not in self.job.sellers:
                self.job.sellers[seller_id] = {
                    "seller_id": seller_id,
                    "seller_name": product["seller_name"],
                    "seller_url": product["seller_url"],
                    "total_products": 0,
                    "sold_products": 0,
                }
            if seller_id:
                self.job.sellers[seller_id]["total_products"] += 1

    async def _check_updates(self):
        """Проверка изменений в нише."""
        current_products = await self.parser.parse_niche(
            self.job.game_slug,
            self.job.category_slug,
            max_pages=2
        )
        current_ids = {p["product_id"] for p in current_products}
        
        for pid, product in list(self.job.products.items()):
            if pid not in current_ids and product["status"] != "SOLD":
                product["status"] = "SOLD"
                product["sold_time"] = datetime.now().isoformat()

                seller_id = product["seller_id"]
                if seller_id and seller_id in self.job.sellers:
                    self.job.sellers[seller_id]["sold_products"] += 1

        for product in current_products:
            pid = product["product_id"]
            if pid not in self.job.products:
                self.job.products[pid] = product
                
                seller_id = product["seller_id"]
                if seller_id and seller_id not in self.job.sellers:
                    self.job.sellers[seller_id] = {
                        "seller_id": seller_id,
                        "seller_name": product["seller_name"],
                        "seller_url": product["seller_url"],
                        "total_products": 0,
                        "sold_products": 0,
                    }
                if seller_id:
                    self.job.sellers[seller_id]["total_products"] += 1

    async def _send_report(self):
        """Отправка отчёта после завершения мониторинга."""
        report = self._build_report()
        
        await self.bot.send_message(
            self.job.chat_id,
            report["text"],
            parse_mode="HTML"
        )
        
        if report["csv_bytes"]:
            document = BufferedInputFile(
                report["csv_bytes"],
                filename=f"stats_{self.job.job_id}.csv"
            )
            await self.bot.send_document(
                self.job.chat_id,
                document,
                caption="Полный список товаров и статистика"
            )

    def _build_report(self) -> dict:
        """Формирование текстового отчёта и CSV."""
        total_products = len(self.job.products)
        sold_products = sum(1 for p in self.job.products.values() if p["status"] == "SOLD")
        
        top_sellers = sorted(
            self.job.sellers.values(),
            key=lambda s: s["sold_products"],
            reverse=True
        )[:10]
        
        lines = [
            f"📊 <b>Отчёт по мониторингу</b>",
            f"",
            f"<b>Ниша:</b> {html.escape(self.job.niche_url)}",
            f"<b>Период:</b> {self.job.start_time:%Y-%m-%d %H:%M} — {self.job.end_time:%Y-%m-%d %H:%M}",
            f"",
            f"<b>Всего товаров:</b> {total_products}",
            f"<b>Продано:</b> {sold_products}",
            f"<b>Уникальных продавцов:</b> {len(self.job.sellers)}",
            f"",
            f"<b>🏆 Топ продавцов:</b>",
        ]
        
        for i, seller in enumerate(top_sellers, 1):
            lines.append(
                f"{i}. <b>{html.escape(seller['seller_name'])}</b> — "
                f"продано {seller['sold_products']} из {seller['total_products']}"
            )
            if seller["seller_url"]:
                lines.append(f"   <a href='{seller['seller_url']}'>Профиль</a>")
        
        text = "\n".join(lines)
        csv_bytes = self._build_csv()
        
        return {"text": text, "csv_bytes": csv_bytes}

    def _build_csv(self) -> bytes:
        """Формирование CSV с данными."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "product_id",
            "title",
            "price",
            "status",
            "seller_name",
            "seller_url",
            "first_seen",
        ])
        
        for product in self.job.products.values():
            writer.writerow([
                product["product_id"],
                product["title"],
                product["price"],
                product["status"],
                product["seller_name"],
                product["seller_url"],
                product["first_seen"],
            ])
        
        return output.getvalue().encode("utf-8-sig")

    def start(self):
        """Запуск фоновой задачи."""
        self._task = asyncio.create_task(self.run())

    def cancel(self):
        """Отмена задачи."""
        if self._task:
            self._task.cancel()


# ---------------------------------------------------------------------------
# Manager для управления всеми задачами
# ---------------------------------------------------------------------------

class StatsMonitor:
    """Менеджер всех задач мониторинга."""

    def __init__(self, account, bot: Bot):
        self.account = account  # Основной аккаунт бота (seller)
        self.parser_account = None  # Отдельный аккаунт для парсинга (buyer)
        self.bot = bot
        self.storage = MonitoringStorage()
        
        # Сначала пытаемся загрузить parser_account синхронно
        self._load_parser_account_sync()
        
        # Создаём парсер с правильным аккаунтом
        parser_acc = self.parser_account if self.parser_account else self.account
        self.parser = NicheParser(parser_acc)
        self._tasks: dict[str, MonitoringTask] = {}
        
        self._restore_active_jobs()

    def _load_parser_account_sync(self):
        """Синхронная загрузка cookies (без network-запросов, только чтение файла)."""
        cookies_file = STORAGE_DIR / "parser_cookies.txt"
        if not cookies_file.exists():
            return
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = f.read().strip()
            
            logger.info(f"[{NAME}] Загружаем сохранённый аккаунт парсера...")
            self.parser_account = Account(cookies=cookies)
            
            # Попытка авторизации (может упасть, тогда используем основной)
            try:
                self.parser_account.get()
                logger.info(f"[{NAME}] Аккаунт парсера загружен: {self.parser_account.username}")
            except Exception as e:
                logger.warning(f"[{NAME}] Не удалось авторизовать сохранённый аккаунт: {e}")
                self.parser_account = None
        except Exception as e:
            logger.exception(f"[{NAME}] Ошибка загрузки cookies парсера: {e}")

    def _load_parser_account(self):
        """Откладывает загрузку cookies до запуска event loop."""
        cookies_file = STORAGE_DIR / "parser_cookies.txt"
        if not cookies_file.exists():
            return
        # Запускаем асинхронную загрузку в фоне, не блокируя __init__
        try:
            asyncio.get_event_loop().create_task(self._async_load_parser_account())
        except RuntimeError:
            # Если event loop ещё нет — загрузим позже в _get_monitor
            pass
    
    async def _async_load_parser_account(self):
        """Асинхронная загрузка аккаунта парсера из сохранённых cookies."""
        cookies_file = STORAGE_DIR / "parser_cookies.txt"
        if not cookies_file.exists():
            return
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = f.read().strip()
            
            logger.info(f"[{NAME}] Загружаем сохранённый аккаунт парсера...")
            parser_account = Account(cookies=cookies)
            await asyncio.to_thread(parser_account.get)
            
            self.parser_account = parser_account
            self.parser = NicheParser(self.parser_account)
            logger.info(f"[{NAME}] Аккаунт парсера загружен: {self.parser_account.username}")
        except Exception as e:
            logger.warning(f"[{NAME}] Не удалось авторизовать сохранённый аккаунт парсера: {e}")

    def save_parser_cookies(self, cookies: str) -> bool:
        """Сохраняет cookies аккаунта парсера."""
        try:
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            cookies_file = STORAGE_DIR / "parser_cookies.txt"
            with open(cookies_file, "w", encoding="utf-8") as f:
                f.write(cookies)
            return True
        except Exception as e:
            logger.exception(f"[{NAME}] Ошибка сохранения cookies: {e}")
            return False

    def delete_parser_account(self) -> bool:
        """Удаляет аккаунт парсера и сохранённые cookies."""
        try:
            cookies_file = STORAGE_DIR / "parser_cookies.txt"
            if cookies_file.exists():
                cookies_file.unlink()
            
            self.parser_account = None
            self.parser = NicheParser(self.account)  # Возвращаемся к основному
            
            logger.info(f"[{NAME}] Аккаунт парсера удалён")
            return True
        except Exception as e:
            logger.exception(f"[{NAME}] Ошибка удаления аккаунта: {e}")
            return False

    async def setup_parser_account(self, cookies: str) -> tuple[bool, str]:
        """
        Настраивает аккаунт парсера. При успехе — заменяет текущий.
        При неудаче — старый аккаунт НЕ удаляется.
        Добавлен retry для нестабильной сети.
        """
        max_attempts = 2
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                parser_account = Account(cookies=cookies)
                await asyncio.to_thread(parser_account.get)
                
                if not parser_account.username:
                    last_error = "Не удалось получить данные аккаунта"
                    if attempt < max_attempts:
                        await asyncio.sleep(1)
                        continue
                    return False, f"❌ {last_error}"
                
                # Только после успешной авторизации применяем изменения
                if not self.save_parser_cookies(cookies):
                    return False, "❌ Не удалось сохранить cookies."
                
                self.parser_account = parser_account
                self.parser = NicheParser(self.parser_account)
                for task in self._tasks.values():
                    task.parser = self.parser
                
                logger.info(f"[{NAME}] Аккаунт парсера настроен: {self.parser_account.username}")
                return True, f"✅ Аккаунт парсера настроен: <b>{html.escape(self.parser_account.username)}</b>"
            
            except Exception as e:
                last_error = str(e)[:300]
                logger.warning(f"[{NAME}] Попытка {attempt}/{max_attempts} настроить аккаунт парсера: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(1)
        
        # Не удаляем старый аккаунт при неудаче
        return False, f"❌ Ошибка авторизации после {max_attempts} попыток: {html.escape(last_error or 'неизвестная ошибка')}"

    def _restore_active_jobs(self):
        """Восстановление активных задач после перезапуска."""
        for job in self.storage._jobs.values():
            if job.is_active():
                task = MonitoringTask(job, self.parser, self.bot, self.storage)
                self._tasks[job.job_id] = task
                task.start()
                logger.info(f"Восстановлена задача {job.job_id}")

    async def start_monitoring(self, chat_id: int, niche_url: str, 
                               game_slug: str, category_slug: Optional[str],
                               duration_hours: int) -> MonitoringJob:
        """Запуск нового мониторинга."""
        active_jobs = self.storage.get_active_jobs_for_chat(chat_id)
        for job in active_jobs:
            if job.niche_url == niche_url:
                raise ValueError(f"Мониторинг этой ниши уже запущен (задача {job.job_id})")

        job = self.storage.create_job(chat_id, niche_url, game_slug, category_slug, duration_hours)
        task = MonitoringTask(job, self.parser, self.bot, self.storage)
        self._tasks[job.job_id] = task
        task.start()
        
        return job

    async def cancel_monitoring(self, job_id: str) -> bool:
        """Отмена мониторинга."""
        task = self._tasks.get(job_id)
        if task:
            task.cancel()
            self.storage.cancel_job(task.job)
            del self._tasks[job_id]
            return True
        return False

    def get_active_jobs(self, chat_id: int) -> list[MonitoringJob]:
        """Получение активных задач для чата."""
        return self.storage.get_active_jobs_for_chat(chat_id)
        
    def delete_task(self, job_id: str) -> bool:
        """Останавливает и полностью удаляет задачу."""
        task = self._tasks.pop(job_id, None)
        if task:
            task.cancel()
        return self.storage.delete_job(job_id)


# ---------------------------------------------------------------------------
# FSM для ввода данных
# ---------------------------------------------------------------------------

class MonitorForm(StatesGroup):
    url = State()
    duration = State()

class ParserSettings(StatesGroup):
    wait_cookies = State()

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def parse_niche_url(url: str) -> tuple[str, Optional[str]]:
    """Извлекает game_slug и category_slug из URL ниши."""
    path = url.replace("https://playerok.com/", "").replace("http://playerok.com/", "").strip("/")
    parts = path.split("/")
    
    if not parts or not parts[0]:
        raise ValueError("Некорректный URL: не указан slug игры")
    
    game_slug = parts[0]
    category_slug = parts[1] if len(parts) > 1 and parts[1] else None
    
    return game_slug, category_slug

def _get_monitor() -> Optional["StatsMonitor"]:
    """Лениво создаёт StatsMonitor, когда аккаунт становится доступен."""
    global _monitor

    if _manager is None or _manager.account is None or _bot is None:
        return None

    if _monitor is None or _monitor.account is not _manager.account:
        _monitor = StatsMonitor(_manager.account, _bot)
        logger.info(f"[{NAME}] StatsMonitor создан (аккаунт: {_manager.account.username})")

    return _monitor


# ---------------------------------------------------------------------------
# Точка входа плагина
# ---------------------------------------------------------------------------

def init(manager):
    """Инициализация плагина — вызывается PluginManager при загрузке."""
    global _manager
    _manager = manager
    
    logger.info(f"[{NAME}] ===== INIT ВЫЗВАН =====")
    logger.info(f"[{NAME}] Manager сохранён: True")
    logger.info(f"[{NAME}] Account доступен: {manager.account is not None}")
    logger.info(f"[{NAME}] ==========================")


def init_tg(dispatcher: Dispatcher, bot: Bot):
    """Регистрация TG хендлеров — вызывается после создания Telegram-бота."""
    global _bot
    _bot = bot
    
    logger.info(f"[{NAME}] ===== INIT_TG ВЫЗВАН =====")
    logger.info(f"[{NAME}] Bot доступен: {bot is not None}")
    logger.info(f"[{NAME}] ===========================")
    
    router = Router(name="stats_monitor")

    # ------------------------------------------------------------------
    # Хелперы: редактирование на месте
    # ------------------------------------------------------------------

    async def _edit_msg(bot, chat_id: int, message_id: int, text: str, markup=None) -> None:
        """Редактирует сообщение по ID. Если сообщения нет — шлёт новое."""
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML"
            )
        except Exception as exc:
            if "message is not modified" in str(exc):
                return
            await bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

    async def _show_plugin_card(query: CallbackQuery, cardinal, index: str | None) -> None:
        """Перерисовывает карточку плагина в текущем сообщении."""
        if index is not None:
            try:
                from cardinal.tg.handlers.plugins_panel import build_plugin_menu
                view = build_plugin_menu(cardinal, int(index))
            except Exception:
                view = None
            if view is not None:
                await _edit_msg(query.message.bot, query.message.chat.id,
                                query.message.message_id, *view)
                return
        try:
            from cardinal.tg.handlers.plugins_panel import build_plugins_menu
            view = build_plugins_menu(cardinal)
        except Exception:
            return
        await _edit_msg(query.message.bot, query.message.chat.id,
                        query.message.message_id, *view)

    async def _edit_prompt(state: FSMContext, bot, text: str, markup=None,
                           fallback_chat_id: int | None = None) -> None:
        """Редактирует сообщение-«диалог», сохранённое в state."""
        data = await state.get_data()
        chat_id = data.get("prompt_chat_id") or fallback_chat_id
        message_id = data.get("prompt_message_id")
        if not message_id:
            await bot.send_message(fallback_chat_id, text, reply_markup=markup, parse_mode="HTML")
            return
        await _edit_msg(bot, chat_id, message_id, text, markup)

    def _back_markup(index: str | None) -> object:
        """Кнопка назад: в карточку плагина или в список."""
        builder = InlineKeyboardBuilder()
        if index is not None:
            builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pl:menu:{index}"))
        else:
            builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="pl"))
        return builder.as_markup()

    async def _start_flow(message: Message, state: FSMContext, index: str | None) -> None:
        await state.set_state(MonitorForm.url)
        await state.update_data(
            prompt_chat_id=message.chat.id,
            prompt_message_id=message.message_id,
            plugin_index=index,
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="⬅️ Назад в категорию",
            callback_data=f"stats:back:{index}" if index is not None else "pl",
        ))
        await _edit_msg(
            message.bot, message.chat.id, message.message_id,
            "📊 <b>Мониторинг ниши Playerok</b>\n\n"
            "Отправьте URL ниши для мониторинга.\n\n"
            "<b>Примеры:</b>\n"
            "• https://playerok.com/wow\n"
            "• https://playerok.com/wow/keys\n"
            "• https://playerok.com/jetbrains/other",
            builder.as_markup(),
        )

    # ------------------------------------------------------------------
    # Хендлеры команд и кнопок
    # ------------------------------------------------------------------

    @router.message(Command("stats_start"))
    async def cmd_stats_start(message: Message, state: FSMContext):
        sent = await message.answer("⏳")
        await _start_flow(sent, state, None)

    @router.callback_query(F.data.startswith("stats:start:"))
    async def cb_stats_start(query: CallbackQuery, state: FSMContext):
        await _start_flow(query.message, state, query.data.rsplit(":", 1)[1])
        await query.answer()

    @router.callback_query(F.data.startswith("stats:back:"))
    async def cb_back_to_card(query: CallbackQuery, state: FSMContext, cardinal):
        """«Назад в категорию»: сбрасывает FSM и перерисовывает карточку."""
        await state.clear()
        await _show_plugin_card(query, cardinal, query.data.rsplit(":", 1)[1])
        await query.answer()

    @router.message(MonitorForm.url, F.text)
    async def process_url(message: Message, state: FSMContext):
        url = (message.text or "").strip()

        with contextlib.suppress(Exception):
            await message.delete()

        data = await state.get_data()
        index = data.get("plugin_index")

        back_builder = InlineKeyboardBuilder()
        back_builder.row(InlineKeyboardButton(
            text="⬅️ Назад в категорию",
            callback_data=f"stats:back:{index}" if index is not None else "pl",
        ))
        back_markup = back_builder.as_markup()

        if not url.startswith("https://playerok.com/"):
            await _edit_prompt(
                state, message.bot,
                "❌ Некорректный URL. Должен начинаться с https://playerok.com/\n\n"
                "Отправьте URL ниши:",
                markup=back_markup,
                fallback_chat_id=message.chat.id,
            )
            return

        try:
            game_slug, category_slug = parse_niche_url(url)
        except ValueError as e:
            await _edit_prompt(state, message.bot, f"❌ {e}\n\nОтправьте другой URL:",
                               markup=back_markup,
                               fallback_chat_id=message.chat.id)
            return

        await state.update_data(url=url, game_slug=game_slug, category_slug=category_slug)
        await state.set_state(MonitorForm.duration)

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="1 час", callback_data="monitor:duration:1"),
            InlineKeyboardButton(text="6 часов", callback_data="monitor:duration:6"),
        )
        builder.row(
            InlineKeyboardButton(text="12 часов", callback_data="monitor:duration:12"),
            InlineKeyboardButton(text="24 часа", callback_data="monitor:duration:24"),
        )
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="monitor:cancel"))

        await _edit_prompt(
            state, message.bot,
            f"✅ <b>Ниша:</b> {html.escape(url)}\n"
            f"<b>Игра:</b> {html.escape(game_slug)}\n"
            f"<b>Категория:</b> {html.escape(category_slug or 'все')}\n\n"
            f"Выберите длительность мониторинга:",
            builder.as_markup(),
            fallback_chat_id=message.chat.id,
        )

    @router.callback_query(F.data.startswith("monitor:duration:"))
    async def process_duration(query: CallbackQuery, state: FSMContext):
        monitor = _get_monitor()
        if monitor is None:
            await query.answer(
                "❌ Playerok не подключён.\nПодключи через /menu → Система → Подключить Playerok",
                show_alert=True,
            )
            return

        duration_hours = int(query.data.split(":")[-1])
        data = await state.get_data()
        url = data["url"]
        game_slug = data["game_slug"]
        category_slug = data.get("category_slug")
        index = data.get("plugin_index")

        await state.clear()

        try:
            job = await monitor.start_monitoring(
                query.message.chat.id, url, game_slug, category_slug, duration_hours
            )
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text="⬅️ Назад в категорию",
                callback_data=f"pl:menu:{index}" if index is not None else "pl",
            ))
            await _edit_msg(
                query.message.bot, query.message.chat.id, query.message.message_id,
                f"✅ <b>Мониторинг запущен</b>\n\n"
                f"ID задачи: {job.job_id}\n"
                f"Ниша: {html.escape(url)}\n"
                f"Длительность: {duration_hours} ч.\n"
                f"Завершится: {job.end_time:%Y-%m-%d %H:%M}\n\n"
                f"Статус: /stats_status",
                builder.as_markup(),
            )
        except ValueError as e:
            await _edit_msg(query.message.bot, query.message.chat.id,
                            query.message.message_id, f"❌ {e}")

        await query.answer()

    @router.callback_query(F.data == "monitor:cancel")
    async def cancel_monitoring_form(query: CallbackQuery, state: FSMContext, cardinal):
        """«Отмена»: сразу возвращаемся в меню плагина."""
        data = await state.get_data()
        index = data.get("plugin_index")
        await state.clear()
        await _show_plugin_card(query, cardinal, index)
        await query.answer()

    @router.callback_query(F.data.startswith("stats:test:"))
    async def cb_stats_test(query: CallbackQuery):
        index = query.data.rsplit(":", 1)[1]
        account_status = _manager is not None and _manager.account is not None
        username = _manager.account.username if _manager and _manager.account else None
        monitor = _get_monitor()

        lines = [
            "🧪 <b>Тест плагина мониторинга</b>",
            "",
            f"Manager доступен: {_manager is not None}",
            f"Account доступен: {account_status}",
            f"Monitor доступен: {monitor is not None}",
            f"Bot доступен: {_bot is not None}",
        ]
        if account_status:
            lines.append(f"Username: {username}")
        if monitor is not None:
            lines.append(f"Активных задач: {len(monitor.get_active_jobs(query.message.chat.id))}")

        await _edit_msg(
            query.message.bot, query.message.chat.id, query.message.message_id,
            "\n".join(lines), _back_markup(index)
        )
        await query.answer()

    @router.callback_query(F.data.startswith("stats:settings:"))
    async def cb_stats_settings(query: CallbackQuery, state: FSMContext):
        """Меню настроек аккаунта парсера (заодно сбрасывает FSM ввода cookies)."""
        await state.clear()
        index = query.data.rsplit(":", 1)[1]
        monitor = _get_monitor()
        if monitor is None:
            await query.answer("❌ Playerok не подключён", show_alert=True)
            return

        parser_account = monitor.parser_account
        lines = ["⚙️ <b>Настройки мониторинга</b>", ""]
        if parser_account:
            lines += [
                "🟢 <b>Аккаунт для парсинга:</b>",
                f"Username: {html.escape(parser_account.username or '?')}",
                "Статус: подключён",
            ]
        else:
            lines += [
                "🔴 <b>Аккаунт для парсинга:</b> не задан",
                "Используется основной аккаунт (seller)",
                "",
                "⚠️ <i>Seller-аккаунт может получать 403 при парсинге. "
                "Рекомендуется добавить аккаунт покупателя.</i>",
            ]

        builder = InlineKeyboardBuilder()
        if parser_account:
            builder.row(InlineKeyboardButton(text="🔄 Изменить аккаунт", callback_data=f"stats:parser:change:{index}"))
            builder.row(InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data=f"stats:parser:delete:{index}"))
        else:
            builder.row(InlineKeyboardButton(text="➕ Добавить аккаунт покупателя", callback_data=f"stats:parser:add:{index}"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pl:menu:{index}"))

        await _edit_msg(query.message.bot, query.message.chat.id, query.message.message_id,
                        "\n".join(lines), builder.as_markup())
        await query.answer()

    async def _ask_cookies(query: CallbackQuery, state: FSMContext, index: str, title: str) -> None:
        await state.set_state(ParserSettings.wait_cookies)
        await state.update_data(
            plugin_index=index,
            prompt_chat_id=query.message.chat.id,
            prompt_message_id=query.message.message_id,
        )
        text = (
            f"{title}\n\n"
            "Отправьте cookies от аккаунта покупателя (не seller) одним сообщением.\n\n"
            "<b>Как получить cookies:</b>\n"
            "1. Зайдите на playerok.com с аккаунта покупателя\n"
            "2. Откройте DevTools (F12) → Network\n"
            "3. Обновите страницу\n"
            "4. Скопируйте значение заголовка Cookie:\n"
            "<code>token=eyJ...; __ddg5_=...</code>"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"stats:settings:{index}"))
        await _edit_msg(query.message.bot, query.message.chat.id, query.message.message_id,
                        text, builder.as_markup())

    @router.callback_query(F.data.startswith("stats:parser:add:"))
    async def cb_add_parser_account(query: CallbackQuery, state: FSMContext):
        await _ask_cookies(query, state, query.data.rsplit(":", 1)[1], "➕ <b>Добавление аккаунта покупателя</b>")
        await query.answer()

    @router.callback_query(F.data.startswith("stats:parser:change:"))
    async def cb_change_parser_account(query: CallbackQuery, state: FSMContext):
        await _ask_cookies(query, state, query.data.rsplit(":", 1)[1], "🔄 <b>Изменение аккаунта покупателя</b>")
        await query.answer()

    @router.callback_query(F.data.startswith("stats:parser:delete:"))
    async def cb_delete_parser_account(query: CallbackQuery):
        monitor = _get_monitor()
        if monitor is None:
            await query.answer("❌ Playerok не подключён", show_alert=True)
            return
        index = query.data.rsplit(":", 1)[1]
        ok = monitor.delete_parser_account()
        msg = "✅ Аккаунт парсера удалён. Используется основной аккаунт." if ok else "❌ Ошибка удаления аккаунта"
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stats:settings:{index}"))
        await _edit_msg(query.message.bot, query.message.chat.id, query.message.message_id,
                        msg, builder.as_markup())
        await query.answer()

    @router.message(ParserSettings.wait_cookies, F.text)
    async def process_parser_cookies(message: Message, state: FSMContext):
        """Обработка cookies аккаунта парсера."""
        monitor = _get_monitor()
        data = await state.get_data()
        index = data.get("plugin_index")
        chat_id = data.get("prompt_chat_id")
        message_id = data.get("prompt_message_id")
        
        # Диагностика: если ID потерялся — fallback на текущее сообщение
        logger.info(f"[{NAME}] cookies-ввод: chat={chat_id} msg={message_id} (текущее: {message.chat.id}/{message.message_id})")
        if not chat_id or not message_id:
            chat_id = message.chat.id
            message_id = message.message_id
        await state.clear()

        if monitor is None:
            await message.answer("❌ Playerok не подключён.")
            return

        cookies = (message.text or "").strip()
        with contextlib.suppress(Exception):
            await message.delete()

        success, msg = await monitor.setup_parser_account(cookies)

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад в настройки", callback_data=f"stats:settings:{index}" if index else "pl"))
        if not success:
            builder.row(InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"stats:parser:add:{index}"))

        # Результат показываем в том же сообщении, где была инструкция
        if chat_id and message_id:
            await _edit_msg(message.bot, chat_id, message_id, msg, builder.as_markup())
        else:
            await message.answer(msg, reply_markup=builder.as_markup())
            
    # ------------------------------------------------------------------
    # Активные задачи
    # ------------------------------------------------------------------

    async def _render_jobs(query: CallbackQuery, index: str) -> None:
        monitor = _get_monitor()
        lines = ["📋 <b>Активные задачи</b>", ""]
        builder = InlineKeyboardBuilder()
        jobs = monitor.get_active_jobs(query.message.chat.id) if monitor else []
        if not jobs:
            lines.append("Активных задач нет.")
            lines.append("Запустите через «▶️ Начать работу».")
        else:
            for job in jobs:
                remaining = job.end_time - datetime.now()
                rem = f"{remaining.seconds // 3600}ч {(remaining.seconds // 60) % 60}м"
                niche = job.game_slug + (f"/{job.category_slug}" if job.category_slug else "")
                lines.append(f"• <b>{html.escape(niche)}</b> — товаров: {len(job.products)}, осталось: {rem}")
                builder.row(
                    InlineKeyboardButton(text="👁", callback_data=f"stats:job:view:{index}:{job.job_id}"),
                    InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stats:job:stop:{index}:{job.job_id}"),
                    InlineKeyboardButton(text="🗑", callback_data=f"stats:job:del:{index}:{job.job_id}"),
                )
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pl:menu:{index}"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"))
        await _edit_msg(query.message.bot, query.message.chat.id, query.message.message_id,
                        "\n".join(lines), builder.as_markup())

    @router.callback_query(F.data.startswith("stats:jobs:"))
    async def cb_stats_jobs(query: CallbackQuery):
        await _render_jobs(query, query.data.rsplit(":", 1)[1])
        await query.answer()

    @router.callback_query(F.data.startswith("stats:job:view:"))
    async def cb_job_view(query: CallbackQuery):
        rest = query.data.split(":", 3)[3]
        index, job_id = rest.split(":", 1)
        monitor = _get_monitor()
        job = monitor.storage.get_job(job_id) if monitor else None
        if job is None or not job.is_active():
            await query.answer("Задача больше не существует", show_alert=True)
            await _render_jobs(query, index)
            return

        sold = sum(1 for p in job.products.values() if p["status"] == "SOLD")
        lines = [
            "📦 <b>Задача мониторинга</b>",
            "",
            f"<b>Ниша:</b> {html.escape(job.niche_url)}",
            f"<b>Старт:</b> {job.start_time:%d.%m %H:%M}",
            f"<b>Финиш:</b> {job.end_time:%d.%m %H:%M}",
            "",
            f"<b>Товаров:</b> {len(job.products)}",
            f"<b>Продано:</b> {sold}",
            f"<b>Продавцов:</b> {len(job.sellers)}",
        ]
        top = sorted(job.sellers.values(), key=lambda s: s["sold_products"], reverse=True)[:5]
        if top:
            lines += ["", "<b>Топ продавцов:</b>"]
            for i, s in enumerate(top, 1):
                lines.append(f"{i}. {html.escape(s['seller_name'])} — продано {s['sold_products']} из {s['total_products']}")

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stats:job:stop:{index}:{job.job_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"stats:job:del:{index}:{job.job_id}"),
        )
        builder.row(InlineKeyboardButton(text="⬅️ К списку задач", callback_data=f"stats:jobs:{index}"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"))
        await _edit_msg(query.message.bot, query.message.chat.id, query.message.message_id,
                        "\n".join(lines), builder.as_markup())
        await query.answer()

    @router.callback_query(F.data.startswith("stats:job:stop:"))
    async def cb_job_stop(query: CallbackQuery):
        rest = query.data.split(":", 3)[3]
        index, job_id = rest.split(":", 1)
        monitor = _get_monitor()
        if monitor and await monitor.cancel_monitoring(job_id):
            await query.answer("Задача остановлена")
        else:
            await query.answer("Задача не найдена")
        await _render_jobs(query, index)

    @router.callback_query(F.data.startswith("stats:job:del:"))
    async def cb_job_del(query: CallbackQuery):
        rest = query.data.split(":", 3)[3]
        index, job_id = rest.split(":", 1)
        monitor = _get_monitor()
        if monitor:
            monitor.delete_task(job_id)
            await query.answer("Задача удалена")
        await _render_jobs(query, index)

    # ------------------------------------------------------------------
    # Текстовые команды (дублируют UI)
    # ------------------------------------------------------------------

    @router.message(Command("stats_status"))
    async def cmd_stats_status(message: Message):
        monitor = _get_monitor()
        if monitor is None:
            await message.answer("❌ Playerok не подключён.")
            return
        jobs = monitor.get_active_jobs(message.chat.id)
        if not jobs:
            await message.answer("📊 Нет активных задач мониторинга.")
            return
        lines = ["📊 <b>Активные задачи мониторинга:</b>", ""]
        for job in jobs:
            remaining = job.end_time - datetime.now()
            rem = f"{remaining.seconds // 3600}ч {(remaining.seconds // 60) % 60}м"
            lines.append(
                f"• <b>{html.escape(job.niche_url)}</b>\n"
                f"  Товаров: {len(job.products)} · Осталось: {rem}\n"
                f"  Стоп: /stats_cancel {job.job_id}"
            )
        await message.answer("\n".join(lines), parse_mode="HTML")

    @router.message(Command("stats_cancel"))
    async def cmd_stats_cancel(message: Message):
        monitor = _get_monitor()
        if monitor is None:
            await message.answer("❌ Playerok не подключён.")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /stats_cancel <job_id>")
            return
        job_id = parts[1]
        if await monitor.cancel_monitoring(job_id):
            await message.answer(f"✅ Задача {job_id} остановлена.")
        else:
            # Проверяем — может задача уже завершена/удалена
            job = monitor.storage.get_job(job_id)
            if job and not job.is_active():
                await message.answer(f"ℹ️ Задача {job_id} уже завершена или отменена.")
            else:
                await message.answer(f"❌ Задача {job_id} не найдена среди активных.")

    dispatcher.include_router(router)
