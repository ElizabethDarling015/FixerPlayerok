"""Раздел «Система»: логи, бэкап, обновление с GitHub, тесты UI, выключение."""
from __future__ import annotations

import asyncio
import html
import io
import os
import zipfile

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           LinkPreviewOptions)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from ...logging_setup import LOG_FILE
from ...self_update import DEFAULT_REPO, update_from_github
from ...settings import CONFIG_DIR, STORAGE_DIR, ConfigError
from ..chat_kinds import SUPPORT_TITLE
from ..notifications import build_new_deal_text, build_payout_details, build_started_text, started_keyboard
from .common import nav_row, pager_row, safe_edit
from .menu import build_main_menu

router = Router(name="system")

#: Сколько последних строк лога показывать и лимит длины сообщения TG.
LOG_TAIL_LINES = 30
MAX_TEXT_LENGTH = 3500

#: Подпапки storage/, не попадающие в бэкап (логи большие и не нужны для восстановления).
BACKUP_EXCLUDE_DIRS = ("logs",)

def build_system_menu(fixer) -> tuple[str, object]:
    l10n = fixer.l10n
    builder = InlineKeyboardBuilder()

    # Новые кнопки для перенесённых разделов
    builder.button(text=l10n("menu_section_toggles"), callback_data="gl")
    builder.button(text=l10n("menu_section_autodelivery"), callback_data="ad")
    builder.button(text=l10n("menu_section_autoresponse"), callback_data="ar")
    builder.button(text=l10n("menu_section_notifications"), callback_data="nt")

    builder.button(text=l10n("sys_btn_logs"), callback_data="sys:logs")
    builder.button(text=l10n("sys_btn_backup"), callback_data="sys:backup")

    # Кнопка подключения/отключения + её описание в тексте
    if fixer.playerok_connected:
        builder.button(text="🔌 Отключить Playerok", callback_data="sys:disconnect_playerok")
        conn_hint = "• 🔌 Отключить Playerok — остановить слежение за событиями и отключиться от API без перезапуска"
    else:
        builder.button(text="🔗 Подключиться к Playerok", callback_data="sys:connect_playerok")
        conn_hint = "• 🔗 Подключиться к Playerok — авторизоваться и запустить слежение за событиями без перезапуска"

    builder.button(text=l10n("sys_btn_tests"), callback_data="sys:tests")
    builder.button(text=l10n("sys_btn_update"), callback_data="sys:update")
    builder.button(text="🌐 Прокси", callback_data="px:menu")

    # Кнопка очистки уведомлений (открывает подменю с выбором периода)
    builder.button(text=l10n("sys_btn_clear"), callback_data="sys:clear_confirm")
    builder.button(text=l10n("btn_close"), callback_data="close")

    builder.adjust(2)
    builder.row(*nav_row(l10n))

    # Подсказки: что делает каждая кнопка раздела
    text = (
        l10n("settings_title") + "\n\n"
        "• 🎛 Глобальные переключатели — включение/выключение модулей бота\n"
        "• 📦 Авто-выдача — управление лотами и складами\n"
        "• 💬 Автоответчик — настройка автоответов на команды\n"
        "• 🔔 Уведомления — выбор типов уведомлений\n"
        "• 📄 Логи — последние 30 строк журнала бота\n"
        "• 💾 Бэкап — ZIP-архив с конфигами и данными (склады, журналы)\n"
        f"{conn_hint}\n"
        "• 🧪 Тесты — отправить тестовые уведомления для настройки UI\n"
        "• ⬇️ Обновить с GitHub — скачать последнюю версию и перезапустить бота\n"
        "• 🌐 Прокси — подключение Fixer к Playerok через прокси (REST + WebSocket)\n"
        "• 🗑 Очистить — удалить уведомления из Telegram (логи сохранятся)\n"
        "• ❌ Закрыть — закрыть это меню"
    )

    return text, builder.as_markup()


#: Кнопки меню «Тесты» по страницам: (ключ локали, callback).
#: Стр. 1 — сообщения, поддержка и сделки; стр. 2 — проблемы, модули и служебные.
TEST_PAGES: list[list[tuple[str, str]]] = [
    [
        ("test_user_message", "test:user_msg"),
        ("test_support_message", "test:support_msg"),
        ("test_support_in_deal", "test:support_in_deal"),
        ("test_system_notice", "test:system_notice"),
        ("test_staff_event", "test:staff_event"),
        ("test_staff_finished", "test:staff_finished"),
        ("test_payout", "test:payout"),
        ("test_item_expiring", "test:item_expiring"),
        ("test_item_expiring_plain", "test:item_expiring_plain"),
        ("test_new_deal", "test:new_deal"),
        ("test_deal_confirmed", "test:deal_confirmed"),
        ("test_delivery_ok", "test:delivery_ok"),
        ("test_new_review", "test:new_review"),
    ],
    [
        ("test_deal_problem", "test:deal_problem"),
        ("test_problem_resolved", "test:problem_resolved"),
        ("test_rolled_back", "test:rolled_back"),
        ("test_blacklist", "test:blacklist"),
        ("test_item_raised", "test:item_raised"),
        ("test_no_balance", "test:no_balance"),
        ("test_stock_empty", "test:stock_empty"),
        ("test_restore_ok", "test:restore_ok"),
        ("test_restore_fail", "test:restore_fail"),
        ("test_restore_free", "test:restore_free"),
        ("test_error", "test:error"),
        ("test_started", "test:started"),
    ],
]


def _test_page_of(callback: str) -> int:
    for page, buttons in enumerate(TEST_PAGES):
        if any(cb == callback for _, cb in buttons):
            return page
    return 0


def _sample_markup(l10n, callback: str):
    """Кнопка «Назад» образца — на ту страницу тестов, где он лежит."""
    page = _test_page_of(callback)
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data=f"sys:tests:{page}" if page else "sys:tests")
    return builder.as_markup()


def build_tests_menu(fixer, page: int = 0) -> tuple[str, object]:
    """Меню тестов UI для настройки внешнего вида уведомлений (две страницы)."""
    l10n = fixer.l10n
    page = max(0, min(page, len(TEST_PAGES) - 1))
    builder = InlineKeyboardBuilder()
    for key, callback in TEST_PAGES[page]:
        builder.button(text=l10n(key), callback_data=callback)
    builder.adjust(2)
    pager = pager_row("sys:tests", page, len(TEST_PAGES))
    if pager:
        builder.row(*pager)
    builder.row(*nav_row(l10n, "sys"))

    text = (
        l10n("test_title") + "\n\n"
        + l10n("test_page_" + str(page + 1)) + "\n\n"
        "Отправьте тестовое уведомление, чтобы увидеть его внешний вид и настроить под себя.\n\n"
        "💡 <i>Совет: редактируйте строки в <code>fixer/locales/ru.py</code> и перезапускайте тесты для живой настройки!</i>"
    )

    return text, builder.as_markup()


# ------------------------------------------------------------------
# Обработчики раздела "Система"
# ------------------------------------------------------------------

def build_backup_zip(config_dir: str = CONFIG_DIR, storage_dir: str = STORAGE_DIR) -> bytes:
    """
    Собирает zip-архив с конфигами и данными (склады, журналы SQLite) для переноса/восстановления.

    Подпапки из `BACKUP_EXCLUDE_DIRS` (логи) не включаются. Возвращает содержимое архива.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for base_dir in (config_dir, storage_dir):
            if not os.path.isdir(base_dir):
                continue
            base_name = os.path.basename(os.path.normpath(base_dir))
            for root, dirs, files in os.walk(base_dir):
                if root == base_dir:
                    dirs[:] = [d for d in dirs if d not in BACKUP_EXCLUDE_DIRS]
                for filename in sorted(files):
                    full_path = os.path.join(root, filename)
                    arcname = os.path.join(base_name, os.path.relpath(full_path, base_dir))
                    archive.write(full_path, arcname)
    return buffer.getvalue()

def read_log_tail(log_file: str = LOG_FILE, lines: int = LOG_TAIL_LINES) -> str:
    """Последние строки файла лога (пустая строка, если файла нет)."""
    if not os.path.isfile(log_file):
        return ""
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        return "".join(f.readlines()[-lines:])


@router.callback_query(F.data == "sys")
async def cb_menu(query: CallbackQuery, fixer) -> None:
    text, markup = build_system_menu(fixer)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "sys:logs")
async def cb_logs(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    tail = read_log_tail()
    if not tail.strip():
        body = l10n("sys_logs_empty")
    else:
        escaped = html.escape(tail)[-MAX_TEXT_LENGTH:]
        body = f"<pre>{escaped}</pre>"
    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(query.message, l10n("sys_logs_title") + "\n" + body, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:backup")
async def cb_backup(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    data = await asyncio.to_thread(build_backup_zip)
    filename = f"fixer_backup_{datetime.now():%Y%m%d_%H%M}.zip"
    await query.message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=l10n("sys_backup_caption"),
    )
    await query.answer()


@router.callback_query(F.data == "sys:clear_confirm")
async def cb_clear_confirm(query: CallbackQuery, fixer) -> None:
    """Подменю выбора периода очистки."""
    l10n = fixer.l10n
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("clear_today"), callback_data="sys:clear:today")
    builder.button(text=l10n("clear_week"), callback_data="sys:clear:week")
    builder.button(text=l10n("clear_all"), callback_data="sys:clear:all")
    builder.row(*nav_row(l10n, "sys"))
    text = (
        l10n("clear_title") + "\n\n"
        "⚠️ Сообщения удалятся только из Telegram.\n"
        "Логи бота останутся нетронутыми.\n\n"
        "Выберите период:"
    )
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:clear:today")
async def cb_clear_today(query: CallbackQuery, fixer) -> None:
    """Очистка уведомлений за сегодня (с 00:00 UTC)."""
    l10n = fixer.l10n
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await fixer.notifier.clear_notifications(since_timestamp=today_start.timestamp())
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True,
    )
    text, markup = build_system_menu(fixer)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:clear:week")
async def cb_clear_week(query: CallbackQuery, fixer) -> None:
    """Очистка уведомлений за последние 7 дней."""
    l10n = fixer.l10n
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await fixer.notifier.clear_notifications(since_timestamp=week_ago.timestamp())
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True,
    )
    text, markup = build_system_menu(fixer)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:clear:all")
async def cb_clear_all(query: CallbackQuery, fixer) -> None:
    """Очистка всех накопленных уведомлений."""
    l10n = fixer.l10n
    result = await fixer.notifier.clear_notifications(since_timestamp=None)
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True,
    )
    text, markup = build_system_menu(fixer)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data.regexp(r"^sys:tests(:\d+)?$"))
async def cb_tests(query: CallbackQuery, fixer) -> None:
    """Показать меню тестов UI (страница — после двоеточия)."""
    page = int(query.data.rsplit(":", 1)[1]) if query.data.count(":") == 2 else 0
    text, markup = build_tests_menu(fixer, page)
    await safe_edit(query.message, text, markup)
    await query.answer()


# ------------------------------------------------------------------
# Обработчики тестовых уведомлений (заменяют текущее сообщение)
# ------------------------------------------------------------------

@router.callback_query(F.data == "test:user_msg")
async def cb_test_user_msg(query: CallbackQuery, fixer) -> None:
    """Образец: сообщение покупателя."""
    l10n = fixer.l10n
    text = l10n(
        "notif_new_message",
        username="loner42",
        item="🌐 WebStorm — Лицензия навсегда | Lifetime [Автовыдача 24/7]",
        text="Здравствуйте! Подскажите, лицензия подойдёт для macOS?",
    )
    markup = _sample_markup(l10n, "test:user_msg")
    await safe_edit(query.message, text, markup)
    await query.answer()

@router.callback_query(F.data == "test:support_msg")
async def cb_test_support_msg(query: CallbackQuery, fixer) -> None:
    """Образец: сообщение в отдельном чате поддержки."""
    l10n = fixer.l10n
    text = l10n(
        "notif_support_message",
        staff="🔰 Лилия Д.",
        text="Здравствуйте!\n\nПередали вашу заявку на рассмотрение.",
    )
    markup = _sample_markup(l10n, "test:support_msg")
    await safe_edit(query.message, text, markup)
    await query.answer()

@router.callback_query(F.data == "test:support_in_deal")
async def cb_test_support_in_deal(query: CallbackQuery, fixer) -> None:
    """Образец: сотрудник Playerok пишет в чате сделки с покупателем."""
    l10n = fixer.l10n
    text = l10n(
        "notif_support_in_deal_chat",
        staff="⚖️ Виктор Г.",
        buyer="loner42",
        item="🔑 ЧАТГПТ-5.6 PLUS ⭐️ ЛИЧНЫЙ АККАУНТ (1 МЕСЯЦ) ⚡️ АВТОВЫДАЧА",
        text="Здравствуйте! Покупатель сообщил о проблеме. Пожалуйста, предоставьте полный доступ к аккаунту в течение 24 часов.",
    )
    markup = _sample_markup(l10n, "test:support_in_deal")
    await safe_edit(query.message, text, markup)
    await query.answer()

@router.callback_query(F.data == "test:new_deal")
async def cb_test_new_deal(query: CallbackQuery, fixer) -> None:
    """Образец: новая сделка — отдельным сообщением, как настоящая: с обложкой лота (берётся
    обложка первого лота аккаунта) и теми же кнопками («Подтвердить выдачу» в образце ничего
    не отправляет на Playerok). Если Playerok не подключён — без фото."""
    l10n = fixer.l10n
    text = build_new_deal_text(
        l10n,
        section="JetBrains → Подписки",
        item="🌐 WebStorm — Лицензия навсегда | Lifetime [Автовыдача 24/7]",
        buyer="homoSanyok",
        price="330",
        chat_id="123e4567-e89b-42d3-a456-426614174000",
        autodelivery=False,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=l10n("deal_btn_confirm"), callback_data="dl:test"),
        InlineKeyboardButton(text=l10n("deal_btn_collapse"), callback_data="dl:min"),
    ]])
    await _send_sample_with_photo(query, fixer, text, markup)
    await query.answer("🛒 Отправлено отдельным сообщением")


async def _test_photo_url(fixer) -> str | None:
    """Обложка первого лота аккаунта — для образцов с фото (None, если Playerok не подключён)."""
    account = getattr(fixer, "account", None)
    if account is None:
        return None
    try:
        page = await asyncio.to_thread(account.get_my_items, None, 1)
        for it in (page.items if page and page.items else []):
            url = _get_test_item_url(it)
            if url:
                return url
    except Exception:
        return None
    return None


async def _send_sample_with_photo(query: CallbackQuery, fixer, text: str, markup=None) -> None:
    """Образец отдельным сообщением с обложкой лота; без обложки — текстом."""
    url = await _test_photo_url(fixer)
    if url:
        try:
            await query.message.answer_photo(url, caption=text, reply_markup=markup)
            return
        except Exception as exc:
            logger.debug("Образец с фото не ушёл: {} — шлю текстом", exc)
    await query.message.answer(text, reply_markup=markup)


async def _photo_sample(query: CallbackQuery, fixer, callback: str, text: str) -> None:
    """Образец, который в жизни приходит с фото: с обложкой — отдельным сообщением,
    без неё (Playerok не подключён) — на месте меню с кнопкой «Назад»."""
    url = await _test_photo_url(fixer)
    if url:
        try:
            await query.message.answer_photo(url, caption=text)
            await query.answer("📸 Отправлено отдельным сообщением")
            return
        except Exception as exc:
            logger.debug("Образец с фото не ушёл: {} — показываю текстом", exc)
    await safe_edit(query.message, text, _sample_markup(fixer.l10n, callback))
    await query.answer()

@router.callback_query(F.data == "test:deal_confirmed")
async def cb_test_deal_confirmed(query: CallbackQuery, fixer) -> None:
    """Тест: сделка подтверждена."""
    l10n = fixer.l10n
    text = l10n(
        "notif_deal_confirmed",
        section="World of Tanks → Валюта",
        item="Гем-пакет 1000 гемов",
        buyer="loner42",
        price="1500",
        chat_id="123e4567-e89b-42d3-a456-426614174000",
    )
    await _photo_sample(query, fixer, "test:deal_confirmed", text)


@router.callback_query(F.data == "test:new_review")
async def cb_test_new_review(query: CallbackQuery, fixer) -> None:
    """Тест: новый отзыв."""
    l10n = fixer.l10n
    text = l10n(
        "notif_new_review",
        rating="5",
        author="HappyBuyer",
        text="Отличный продавец! Всё получил быстро, товар соответствует описанию. Рекомендую! 👍",
    )
    
    markup = _sample_markup(l10n, "test:new_review")
    
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "test:delivery_ok")
async def cb_test_delivery_ok(query: CallbackQuery, fixer) -> None:
    """Тест: успешная доставка."""
    l10n = fixer.l10n
    text = l10n(
        "notif_delivery_ok",
        section="Steam → Ключи",
        item="Ключ активации Windows 11",
        stock="42",
    )
    
    markup = _sample_markup(l10n, "test:delivery_ok")
    
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "test:error")
async def cb_test_error(query: CallbackQuery, fixer) -> None:
    """Тест: ошибка."""
    l10n = fixer.l10n
    text = l10n(
        "notif_error",
        error="ConnectionError: Не удалось подключиться к серверу Playerok (timeout after 15s)",
    )
    
    markup = _sample_markup(l10n, "test:error")
    
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "test:payout")
async def cb_test_payout(query: CallbackQuery, fixer) -> None:
    """Образец: выплата с баланса (неизвестные поля в настоящем уведомлении не выводятся)."""
    l10n = fixer.l10n
    details = build_payout_details(
        l10n, amount=5100, method="СБП", status="✅ Успешно", date="19.08.2026, 11:58", balance=15230,
    )
    text = l10n(
        "notif_payout",
        details=details,
        text="Ваша выплата успешно проведена.\nСумма отправлена на указанные реквизиты",
    )
    markup = _sample_markup(l10n, "test:payout")
    await safe_edit(query.message, text, markup)
    await query.answer()

@router.callback_query(F.data == "test:item_expiring")
async def cb_test_item_expiring(query: CallbackQuery, fixer) -> None:
    """Тест: лот скоро снимут с продажи."""
    l10n = fixer.l10n
    text = l10n(
        "notif_item_expiring",
        item="🔥 Adobe Photoshop 2026 — Бессрочная лицензия | Автовыдача",
        section="Adobe → Софт",
        price="299 ₽",
        text="Ваш товар будет снят с продажи через 7 дней по истечении срока выставления.\n\nОбновите статус товара, чтобы продлить срок выставления",
    )
    await _photo_sample(query, fixer, "test:item_expiring", text)


@router.callback_query(F.data == "test:staff_event")
async def cb_test_staff_event(query: CallbackQuery, fixer) -> None:
    """Образец: сотрудник открыл чат («Смотрим чат…»); «Чат завершён» выглядит так же."""
    l10n = fixer.l10n
    text = l10n("notif_staff_started", staff="⚖️ Виктор Г.", place=html.escape(SUPPORT_TITLE))
    markup = _sample_markup(l10n, "test:staff_event")
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "test:system_notice")
async def cb_test_system_notice(query: CallbackQuery, fixer) -> None:
    """Образец: уведомление площадки из чата «Уведомления Playerok»."""
    l10n = fixer.l10n
    lot = l10n("notif_system_lot",
               lot='<a href="https://playerok.com/products/example">📊 DataSpell — Лицензия навсегда | Lifetime</a>')
    text = l10n(
        "notif_system_message",
        text="Ваш товар заблокирован.\nПричина: ваше объявление о товаре размещено не в той категории.",
        lot=lot,
    )
    markup = _sample_markup(l10n, "test:system_notice")
    await query.message.edit_text(text, reply_markup=markup,
                                  link_preview_options=LinkPreviewOptions(is_disabled=True))
    await query.answer()


@router.callback_query(F.data == "test:blacklist")
async def cb_test_blacklist(query: CallbackQuery, fixer) -> None:
    """Образец: покупка покупателем из чёрного списка."""
    l10n = fixer.l10n
    text = l10n("notif_blacklist_deal", section="JetBrains → Подписки", buyer="cheater",
                item="🌐 WebStorm — Лицензия навсегда | Lifetime")
    markup = _sample_markup(l10n, "test:blacklist")
    await safe_edit(query.message, text, markup)
    await query.answer()



# ------------------------------------------------------------------
# Образцы второй страницы и недостающие с первой
# ------------------------------------------------------------------

async def _show_sample(query: CallbackQuery, fixer, callback: str, text: str, markup=None) -> None:
    await safe_edit(query.message, text, markup or _sample_markup(fixer.l10n, callback))
    await query.answer()


@router.callback_query(F.data == "test:staff_finished")
async def cb_test_staff_finished(query: CallbackQuery, fixer) -> None:
    """Образец: сотрудник завершил чат."""
    text = fixer.l10n("notif_staff_finished", staff="⚖️ Виктор Г.", place=html.escape(SUPPORT_TITLE))
    await _show_sample(query, fixer, "test:staff_finished", text)


@router.callback_query(F.data == "test:item_expiring_plain")
async def cb_test_item_expiring_plain(query: CallbackQuery, fixer) -> None:
    """Образец: «лот скоро снимут», когда бот не смог определить, какой это лот."""
    text = fixer.l10n(
        "notif_item_expiring_plain",
        text="Ваш товар будет снят с продажи через 7 дней по истечении срока выставления.",
    )
    await _show_sample(query, fixer, "test:item_expiring_plain", text)


@router.callback_query(F.data == "test:deal_problem")
async def cb_test_deal_problem(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_deal_problem", section="JetBrains → Подписки",
                      item="🌐 WebStorm — Лицензия навсегда | Lifetime",
                      deal_id="1f1c3b0d-05ec-6c10-17d6-9d024a8906ae")
    await _show_sample(query, fixer, "test:deal_problem", text)


@router.callback_query(F.data == "test:problem_resolved")
async def cb_test_problem_resolved(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_deal_problem_resolved", section="JetBrains → Подписки",
                      deal_id="1f1c3b0d-05ec-6c10-17d6-9d024a8906ae")
    await _show_sample(query, fixer, "test:problem_resolved", text)


@router.callback_query(F.data == "test:rolled_back")
async def cb_test_rolled_back(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_deal_rolled_back", section="JetBrains → Подписки",
                      item="🌐 WebStorm — Лицензия навсегда | Lifetime")
    await _show_sample(query, fixer, "test:rolled_back", text)


@router.callback_query(F.data == "test:item_raised")
async def cb_test_item_raised(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_item_raised", item="🔥 Adobe Photoshop 2026 — Бессрочная лицензия", spent="15")
    await _show_sample(query, fixer, "test:item_raised", text)


@router.callback_query(F.data == "test:no_balance")
async def cb_test_no_balance(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_insufficient_balance", item="🔥 Adobe Photoshop 2026 — Бессрочная лицензия",
                      price="15", available="7.5")
    await _show_sample(query, fixer, "test:no_balance", text)


@router.callback_query(F.data == "test:stock_empty")
async def cb_test_stock_empty(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_stock_empty", item="Ключ активации Windows 11")
    await _show_sample(query, fixer, "test:stock_empty", text)


@router.callback_query(F.data == "test:restore_ok")
async def cb_test_restore_ok(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_restore_ok", item="🌐 WebStorm — Лицензия навсегда | Lifetime",
                      item_id="9a8b7c6d-5e4f-4a3b-2c1d-0e9f8a7b6c5d")
    await _show_sample(query, fixer, "test:restore_ok", text)


@router.callback_query(F.data == "test:restore_fail")
async def cb_test_restore_fail(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_restore_fail", item="🌐 WebStorm — Лицензия навсегда | Lifetime",
                      error="Playerok: превышен лимит активных лотов в категории")
    await _show_sample(query, fixer, "test:restore_fail", text)


@router.callback_query(F.data == "test:restore_free")
async def cb_test_restore_free(query: CallbackQuery, fixer) -> None:
    text = fixer.l10n("notif_restore_premium_fallback", item="🌐 WebStorm — Лицензия навсегда | Lifetime",
                      item_id="9a8b7c6d-5e4f-4a3b-2c1d-0e9f8a7b6c5d",
                      reason="недостаточно средств на балансе")
    await _show_sample(query, fixer, "test:restore_free", text)


@router.callback_query(F.data == "test:started")
async def cb_test_started(query: CallbackQuery, fixer) -> None:
    """Образец: «FixerPlayerok запущен» — отдельным сообщением, как настоящее (с кнопкой «Главное меню»)."""
    l10n = fixer.l10n
    text = build_started_text(
        l10n, username="seller", balance="15 230 ₽", missed_deals=2, unread_messages=3,
        modules="autodelivery, autoraise, digest", connected=True,
    )
    await query.message.answer(text, reply_markup=started_keyboard(l10n))
    await query.answer("🐦 Отправлено отдельным сообщением")


def _get_test_item_url(item) -> str | None:
    att = getattr(item, "attachment", None)
    if att and getattr(att, "url", None):
        return att.url
    for a in getattr(item, "attachments", None) or []:
        if getattr(a, "url", None):
            return a.url
    return None

# ------------------------------------------------------------------
# Остальные обработчики раздела "Система"
# ------------------------------------------------------------------

@router.callback_query(F.data == "sys:update")
async def cb_update_confirm(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("sys_btn_update_yes"), callback_data="sys:update:yes"))
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(
        query.message,
        l10n("sys_update_confirm", repo=DEFAULT_REPO),
        builder.as_markup(),
    )
    await query.answer()


@router.callback_query(F.data == "sys:update:yes")
async def cb_update(query: CallbackQuery, fixer) -> None:
    l10n = fixer.l10n
    await safe_edit(query.message, l10n("sys_update_running"))
    await query.answer()

    result = await asyncio.to_thread(update_from_github)
    if not result.ok:
        logger.warning("Обновление с GitHub не удалось ({}): {}", result.method, result.detail or result.message)
        detail = html.escape((result.detail or "")[:500])
        body = l10n("sys_update_failed", message=html.escape(result.message))
        if detail:
            body += f"\n<pre>{detail}</pre>"
        builder = InlineKeyboardBuilder()
        builder.row(*nav_row(l10n, "sys"))
        await safe_edit(query.message, body, builder.as_markup())
        return

    logger.info("Обновление с GitHub: {} — {}", result.message, result.detail)
    if result.changed:
        await safe_edit(
            query.message,
            l10n(
                "sys_update_ok_restart",
                message=html.escape(result.message),
                detail=html.escape((result.detail or "")[:400]),
            ),
        )
        fixer.request_restart()
        return

    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(
        query.message,
        l10n("sys_update_ok", message=html.escape(result.message)),
        builder.as_markup(),
    )


@router.callback_query(F.data == "sys:connect_playerok")
async def cb_connect_playerok(query: CallbackQuery, fixer) -> None:
    """Подключение к Playerok: статус в сообщении, успех → главное меню, ошибка → alert + «Система»."""
    await safe_edit(query.message, "🔌 Подключаюсь…")

    result = await fixer.connect_playerok()

    if result["ok"]:
        await query.answer("✅ Подключено к Playerok")
        # Сообщение превращается в стартовое (как при онлайн-запуске)
        text, markup = build_main_menu(fixer)
        await safe_edit(query.message, text, markup)
    else:
        error_text = str(result["message"])
        # Для всплывающего алерта достаточно первого предложения — оно обычно и есть
        # суть ошибки ("Бот-проверка заметила..."), а инструкции после первой точки
        # ("Чтобы продолжить работу...") только загромождают маленькое окно алерта.
        # Полный текст без сокращений всё равно уходит в тело сообщения ниже.
        first_sentence = error_text.split(". ", 1)[0].rstrip(".") + "."
        alert_text = f"❌ Ошибка подключения: {first_sentence}"
        # answerCallbackQuery ограничен Telegram ~200 символами — на случай, если даже
        # одно предложение окажется длиннее, подстраховываемся обрезкой по символам.
        # Раньше это ограничение никак не проверялось, из-за чего запрос падал с
        # MESSAGE_TOO_LONG ДО восстановления меню ниже, и сообщение "🔌 Подключаюсь…"
        # оставалось висеть в чате навсегда.
        if len(alert_text) > 200:
            alert_text = alert_text[:197] + "…"
        try:
            await query.answer(alert_text, show_alert=True)
        except TelegramBadRequest as e:
            logger.warning("Не удалось показать алерт с ошибкой подключения: {}", e)
        text, markup = build_system_menu(fixer)
        # Полный (не обрезанный) текст ошибки — в тело сообщения, лимит там намного больше.
        text = f"❌ <b>Ошибка подключения к Playerok:</b>\n{html.escape(error_text)}\n\n{text}"
        await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:disconnect_playerok")
async def cb_disconnect_playerok(query: CallbackQuery, fixer) -> None:
    """Отключение от Playerok: статус в сообщении, затем снова меню «Система»."""
    await safe_edit(query.message, "🔌 Отключаюсь…")

    result = await fixer.disconnect_playerok()

    await query.answer(result["message"], show_alert=not result["ok"])
    text, markup = build_system_menu(fixer)
    await safe_edit(query.message, text, markup)

# ------------------------------------------------------------------
# Обработчик кнопки "До завтра" из уведомления о выключении
# ------------------------------------------------------------------

@router.callback_query(F.data == "shutdown_ack")
async def cb_shutdown_ack(query: CallbackQuery, fixer) -> None:
    """Удаляет уведомление о выключении и очищает файл с сохранёнными ID сообщений."""
    # Удаляем сообщение с кнопкой
    try:
        await query.message.delete()
    except Exception:
        pass
    
    # Удаляем файл с сохранёнными ID сообщений
    shutdown_file = fixer.SHUTDOWN_MSG_FILE
    try:
        if os.path.isfile(shutdown_file):
            os.remove(shutdown_file)
            logger.info("Удалён файл уведомления о выключении: {}", shutdown_file)
    except Exception:
        pass
    
    # Пытаемся ответить на callback, но игнорируем ошибку "query is too old"
    try:
        await query.answer("Сообщение удалено")
    except Exception:
        pass