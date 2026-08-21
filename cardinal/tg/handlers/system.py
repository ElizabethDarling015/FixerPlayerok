"""Раздел «Система»: логи, бэкап, обновление с GitHub, тесты UI, выключение."""
from __future__ import annotations

import asyncio
import datetime
import html
import io
import os
import zipfile
import time

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from ...logging_setup import LOG_FILE
from ...self_update import DEFAULT_REPO, update_from_github
from ...settings import CONFIG_DIR, STORAGE_DIR, ConfigError
from .common import nav_row, safe_edit
from .menu import build_main_menu

router = Router(name="system")

#: Сколько последних строк лога показывать и лимит длины сообщения TG.
LOG_TAIL_LINES = 30
MAX_TEXT_LENGTH = 3500

#: Подпапки storage/, не попадающие в бэкап (логи большие и не нужны для восстановления).
BACKUP_EXCLUDE_DIRS = ("logs",)

def build_system_menu(cardinal) -> tuple[str, object]:
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()

    builder.button(text=l10n("sys_btn_logs"), callback_data="sys:logs")
    builder.button(text=l10n("sys_btn_backup"), callback_data="sys:backup")

    # Кнопка подключения/отключения + её описание в тексте
    if cardinal.playerok_connected:
        builder.button(text="🔌 Отключить Playerok", callback_data="sys:disconnect_playerok")
        conn_hint = "• 🔌 Отключить Playerok — остановить слежение за событиями и отключиться от API без перезапуска"
    else:
        builder.button(text="🔗 Подключиться к Playerok", callback_data="sys:connect_playerok")
        conn_hint = "• 🔗 Подключиться к Playerok — авторизоваться и запустить слежение за событиями без перезапуска"

    builder.button(text=l10n("sys_btn_tests"), callback_data="sys:tests")
    builder.button(text=l10n("sys_btn_restart"), callback_data="sys:restart")
    builder.button(text=l10n("btn_close"), callback_data="close")

    # Кнопка очистки уведомлений (открывает подменю с выбором периода)
    builder.button(text=l10n("sys_btn_clear"), callback_data="sys:clear_confirm")
    # Заглушка для чётной сетки 2x4
    builder.button(text="➖", callback_data="noop")

    builder.adjust(2)
    builder.row(*nav_row(l10n))

    # Подсказки: что делает каждая кнопка раздела
    text = (
        l10n("sys_title") + "\n\n"
        "• 📄 Логи — последние 30 строк журнала бота\n"
        "• 💾 Бэкап — ZIP-архив с конфигами и данными (склады, журналы)\n"
        f"{conn_hint}\n"
        "• 🧪 Тесты — отправить тестовые уведомления для настройки UI\n"
        "• 🔁 Перезапуск — полностью перезапустить бота\n"
        "• ❌ Закрыть — закрыть это меню\n"
        "• 🗑 Очистить — удалить уведомления из Telegram (логи сохранятся)"
    )

    return text, builder.as_markup()


def build_tests_menu(cardinal) -> tuple[str, object]:
    """Меню тестов UI для настройки внешнего вида уведомлений."""
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки тестов (8 кнопок — чётное количество, заглушка не нужна)
    builder.button(text=l10n("test_user_message"), callback_data="test:user_msg")
    builder.button(text=l10n("test_support_in_deal"), callback_data="test:support_in_deal")
    builder.button(text=l10n("test_support_message"), callback_data="test:support_msg")
    builder.button(text=l10n("test_new_deal"), callback_data="test:new_deal")
    builder.button(text=l10n("test_deal_confirmed"), callback_data="test:deal_confirmed")
    builder.button(text=l10n("test_new_review"), callback_data="test:new_review")
    builder.button(text=l10n("test_delivery_ok"), callback_data="test:delivery_ok")
    builder.button(text=l10n("test_error"), callback_data="test:error")
    builder.button(text=l10n("test_payout"), callback_data="test:payout")
    builder.button(text=l10n("test_item_expiring"), callback_data="test:item_expiring")
    builder.button(text=l10n("test_photo"), callback_data="test:photo")

    # Раскладываем кнопки в 2 колонки
    builder.adjust(2)
    builder.row(*nav_row(l10n, "sys"))

    text = (
        l10n("test_title") + "\n\n"
        "Отправьте тестовое уведомление, чтобы увидеть его внешний вид и настроить под себя.\n\n"
        "💡 <i>Совет: редактируйте строки в <code>cardinal/locales/ru.py</code> и перезапускайте тесты для живой настройки!</i>"
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
async def cb_menu(query: CallbackQuery, cardinal) -> None:
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


@router.callback_query(F.data == "sys:logs")
async def cb_logs(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
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
async def cb_backup(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    data = await asyncio.to_thread(build_backup_zip)
    filename = f"cardinal_backup_{datetime.datetime.now():%Y%m%d_%H%M}.zip"
    await query.message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=l10n("sys_backup_caption"),
    )
    await query.answer()

@router.callback_query(F.data == "sys:clear_confirm")
async def cb_clear_confirm(query: CallbackQuery, cardinal) -> None:
    """Подменю выбора периода очистки."""
    l10n = cardinal.l10n
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


async def _do_clear(query: CallbackQuery, cardinal, since_ts: float | None) -> None:
    """Общая логика очистки + возврат в меню Система."""
    result = await cardinal.notifier.clear_notifications(since_timestamp=since_ts)
    await query.answer(
        cardinal.l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True,
    )
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:clear:today")
async def cb_clear_today(query: CallbackQuery, cardinal) -> None:
    await _do_clear(query, cardinal, time.time() - 24 * 3600)


@router.callback_query(F.data == "sys:clear:week")
async def cb_clear_week(query: CallbackQuery, cardinal) -> None:
    await _do_clear(query, cardinal, time.time() - 7 * 24 * 3600)


@router.callback_query(F.data == "sys:clear:all")
async def cb_clear_all(query: CallbackQuery, cardinal) -> None:
    await _do_clear(query, cardinal, None)


@router.callback_query(F.data == "sys:clear24h")
async def cb_clear_24h(query: CallbackQuery, cardinal) -> None:
    """Единоразовое удаление за 24 часа (без подменю)."""
    await _do_clear(query, cardinal, time.time() - 24 * 3600)
    
    text = (
        l10n("clear_title") + "\n\n"
        "⚠️ <b>Внимание:</b> сообщения удалятся только из Telegram.\n"
        "Логи бота (<code>storage/logs/cardinal.log</code>) останутся нетронутыми.\n\n"
        "Выберите период:"
    )
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:clear:today")
async def cb_clear_today(query: CallbackQuery, cardinal) -> None:
    """Очистка уведомлений за сегодня."""
    l10n = cardinal.l10n
    
    # Начало текущего дня (00:00) в UTC
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_ts = today_start.timestamp()
    
    result = await cardinal.notifier.clear_notifications(since_timestamp=since_ts)
    
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True
    )
    
    # Возвращаемся в меню "Система"
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:clear:week")
async def cb_clear_week(query: CallbackQuery, cardinal) -> None:
    """Очистка уведомлений за последние 7 дней."""
    l10n = cardinal.l10n
    
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    since_ts = week_ago.timestamp()
    
    result = await cardinal.notifier.clear_notifications(since_timestamp=since_ts)
    
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True
    )
    
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:clear:all")
async def cb_clear_all(query: CallbackQuery, cardinal) -> None:
    """Очистка всех накопленных уведомлений."""
    l10n = cardinal.l10n
    
    result = await cardinal.notifier.clear_notifications(since_timestamp=None)
    
    await query.answer(
        l10n("clear_result", removed=result["removed"], failed=result["failed"]),
        show_alert=True
    )
    
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:tests")
async def cb_tests(query: CallbackQuery, cardinal) -> None:
    """Показать меню тестов UI."""
    text, markup = build_tests_menu(cardinal)
    await safe_edit(query.message, text, markup)
    await query.answer()


# ------------------------------------------------------------------
# Обработчики тестовых уведомлений (заменяют текущее сообщение)
# ------------------------------------------------------------------

@router.callback_query(F.data == "test:user_msg")
async def cb_test_user_msg(query: CallbackQuery, cardinal) -> None:
    """Тест: сообщение от обычного пользователя."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_new_message",
        username="loner42",
        section="World of Tanks → Аккаунты",
        text="Здравствуйте! Хочу узнать, можно ли получить скидку при покупке сразу нескольких аккаунтов?",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:support_msg")
async def cb_test_support_msg(query: CallbackQuery, cardinal) -> None:
    """Тест: сообщение из отдельного чата поддержки."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_new_message",
        username="🛠 Admin",
        section="🛠 Служба поддержки",
        text="Здравствуйте! Чем могу помочь? Опишите вашу проблему, и мы постараемся решить её как можно скорее.",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:support_in_deal")
async def cb_test_support_in_deal(query: CallbackQuery, cardinal) -> None:
    """Тест: поддержка в чате сделки (модератор заглянул в спор с покупателем)."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_support_in_deal_chat",
        username="🛠 Нина А.",
        section="ChatGPT → Аккаунты",
        buyer="loner42",
        item="🔑 ЧАТГПТ-5.6 PLUS ⭐️ ЛИЧНЫЙ АККАУНТ (1 МЕСЯЦ) ⚡️ АВТОВЫДАЧА",
        text="Здравствуйте. При продаже игрового аккаунта с полным доступом вы должны предоставить не только данные авторизации, но и все привязки или перепривязать на ресурсы покупателя, если этого сделано не было, то товар не считается предоставленным в полной мере.\n\nПожалуйста, предоставьте покупателю полный доступ к аккаунту в течение 24 часов — в противном случае мы будем вынуждены оформить возврат средств покупателю",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:new_deal")
async def cb_test_new_deal(query: CallbackQuery, cardinal) -> None:
    """Тест: новая сделка (объединённое уведомление)."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_new_deal",
        section="DataGrip → Лицензии",
        item="🗄 DataGrip — Бессрочная лицензия | Lifetime [Автовыдача 24/7]",
        buyer="loner42",
        status="PAID",
        price="1500",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:deal_confirmed")
async def cb_test_deal_confirmed(query: CallbackQuery, cardinal) -> None:
    """Тест: сделка подтверждена."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_deal_confirmed",
        section="World of Tanks → Валюта",
        item="Гем-пакет 1000 гемов",
        price="1500",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:new_review")
async def cb_test_new_review(query: CallbackQuery, cardinal) -> None:
    """Тест: новый отзыв."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_new_review",
        rating="5",
        author="HappyBuyer",
        text="Отличный продавец! Всё получил быстро, товар соответствует описанию. Рекомендую! 👍",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:delivery_ok")
async def cb_test_delivery_ok(query: CallbackQuery, cardinal) -> None:
    """Тест: успешная доставка."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_delivery_ok",
        section="Steam → Ключи",
        item="Ключ активации Windows 11",
        stock="42",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:error")
async def cb_test_error(query: CallbackQuery, cardinal) -> None:
    """Тест: ошибка."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_error",
        error="ConnectionError: Не удалось подключиться к серверу Playerok (timeout after 15s)",
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)
    
    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()

@router.callback_query(F.data == "test:payout")
async def cb_test_payout(query: CallbackQuery, cardinal) -> None:
    """Тест: выплата с баланса (с суммой)."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_payout",
        amount="5 100",
        method="СБП",
        status="✅ Успешно",
        date="19.08.2026, 11:58",
        text="Ваша выплата успешно проведена.\nСумма отправлена на указанные реквизиты",
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)

    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:item_expiring")
async def cb_test_item_expiring(query: CallbackQuery, cardinal) -> None:
    """Тест: лот скоро снимут с продажи."""
    l10n = cardinal.l10n
    text = l10n(
        "notif_item_expiring",
        item="🔥 Adobe Photoshop 2026 — Бессрочная лицензия | Автовыдача",
        section="Adobe → Софт",
        price="299 ₽",
        text="Ваш товар будет снят с продажи через 7 дней по истечении срока выставления.\n\nОбновите статус товара, чтобы продлить срок выставления",
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=l10n("btn_back"), callback_data="sys:tests")
    builder.adjust(1)

    await safe_edit(query.message, text, builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "test:photo")
async def cb_test_photo(query: CallbackQuery, cardinal) -> None:
    """Тест: уведомление с фото лота (берётся обложка первого лота аккаунта)."""
    l10n = cardinal.l10n
    account = getattr(cardinal, "account", None)
    url = None
    if account is not None:
        try:
            page = await asyncio.to_thread(account.get_my_items, 1)
            for it in (page.items if page and page.items else []):
                url = _get_test_item_url(it)
                if url:
                    break
        except Exception:
            url = None
    if not url:
        await query.answer("❌ Нет фото: Playerok не подключён или у лотов нет картинок", show_alert=True)
        return

    caption = l10n(
        "notif_new_deal",
        section="Adobe → Софт",
        item="🔥 Adobe Photoshop 2026 — Бессрочная лицензия | Автовыдача",
        buyer="loner42",
        status="PAID",
        price="299",
    )
    await query.message.answer_photo(url, caption=caption)
    await query.answer("📸 Отправлено отдельным сообщением")


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
async def cb_update_confirm(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
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
async def cb_update(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
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
        cardinal.request_restart()
        return

    builder = InlineKeyboardBuilder()
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(
        query.message,
        l10n("sys_update_ok", message=html.escape(result.message)),
        builder.as_markup(),
    )


@router.callback_query(F.data == "sys:restart")
async def cb_restart_confirm(query: CallbackQuery, cardinal) -> None:
    l10n = cardinal.l10n
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=l10n("sys_btn_restart_yes"), callback_data="sys:restart:yes"))
    builder.row(*nav_row(l10n, "sys"))
    await safe_edit(query.message, l10n("sys_restart_confirm"), builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "sys:restart:yes")
async def cb_restart(query: CallbackQuery, cardinal) -> None:
    await safe_edit(query.message, cardinal.l10n("sys_restart_done"))
    await query.answer()
    cardinal.request_restart()


@router.callback_query(F.data == "sys:connect_playerok")
async def cb_connect_playerok(query: CallbackQuery, cardinal) -> None:
    """Подключение к Playerok: статус в сообщении, успех → главное меню, ошибка → alert + «Система»."""
    await safe_edit(query.message, "🔌 Подключаюсь…")

    result = await cardinal.connect_playerok()

    if result["ok"]:
        await query.answer("✅ Подключено к Playerok")
        # Сообщение превращается в стартовое (как при онлайн-запуске)
        text, markup = build_main_menu(cardinal)
        await safe_edit(query.message, text, markup)
    else:
        await query.answer(f"❌ Ошибка подключения: {result['message']}", show_alert=True)
        text, markup = build_system_menu(cardinal)
        await safe_edit(query.message, text, markup)


@router.callback_query(F.data == "sys:disconnect_playerok")
async def cb_disconnect_playerok(query: CallbackQuery, cardinal) -> None:
    """Отключение от Playerok: статус в сообщении, затем снова меню «Система»."""
    await safe_edit(query.message, "🔌 Отключаюсь…")

    result = await cardinal.disconnect_playerok()

    await query.answer(result["message"], show_alert=not result["ok"])
    text, markup = build_system_menu(cardinal)
    await safe_edit(query.message, text, markup)

# ------------------------------------------------------------------
# Обработчик кнопки "До завтра" из уведомления о выключении
# ------------------------------------------------------------------

@router.callback_query(F.data == "shutdown_ack")
async def cb_shutdown_ack(query: CallbackQuery, cardinal) -> None:
    """Удаляет уведомление о выключении и очищает файл с сохранёнными ID сообщений."""
    # Удаляем сообщение с кнопкой
    try:
        await query.message.delete()
    except Exception:
        pass
    
    # Удаляем файл с сохранёнными ID сообщений
    shutdown_file = cardinal.SHUTDOWN_MSG_FILE
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