"""Русская локаль PlayerokCardinal."""

STRINGS = {
    # --- Общие / авторизация в TG ---
    "unauthorized": "⛔ Вы не авторизованы. Отправьте секретный код из консоли Cardinal, чтобы привязать себя как администратора.",
    "auth_success": "✅ Вы привязаны как администратор PlayerokCardinal.",
    "auth_wrong_code": "❌ Неверный код. Актуальный код напечатан в консоли Cardinal.",
    "btn_back": "◀️ Назад",
    "btn_home": "🏠 Главное меню",
    "btn_chats": "💬 Чаты с покупателями",
    "chats_empty": "Нет активных чатов.",
    "chats_view_title": "💬 <b>Чат с {username}</b>\n\n",
    "chats_btn_reply": "✏️ Ответить в чат",
    "chats_reply_sent": "✅ Сообщение успешно отправлено покупателю!",
    "chats_title": "💬 <b>Чаты с покупателями</b>\n\nСписок чатов (обновлено при нажатии):",
    "chats_btn_prev_page": "⬅️ Назад",
    "chats_btn_next_page": "➡️ Далее",
    "chats_btn_older": "⬆️ Старые",
    "chats_btn_newer": "⬇️ Новые",
    "chats_btn_read": "✅ Прочитано",
    "chats_btn_refresh": "🔄 Обновить",
    "chats_btn_cancel": "✖️ Завершить диалог",
    "chats_enter_text": "✏️ Живой диалог с <b>{username}</b>.\nПишите сообщение или отправьте фото — всё уйдёт в чат покупателю.\nЛюбая кнопка — выход из режима.",
    "chats_read_done": "✅ Чат отмечен прочитанным.",
    "btn_auto_publish": "📤 Автовыставление",
    "btn_last_deals": "🕒 Последние сделки",
    "alert_in_development": "⏸ Раздел «{section}» в разработке — появится в следующих обновлениях.",
    "btn_close": "✖️ Закрыть",
    "cancelled": "Действие отменено.",
    "stub_message": "⏸ Раздел перенесён в Настройки",
    "btn_cancel": "Отмена",

    # --- Главное меню ---
    "menu_title": (
        "🐦 <b>PlayerokCardinal</b>\n\n"
        "👤 Аккаунт: <b>{username}</b>\n"
        "💰 Баланс: <b>{balance}</b>\n"
        "📩 Новые сообщения: <b>{unread_messages}</b>\n"
        "⏱ Аптайм: <b>{uptime}</b>"
    ),
    "menu_section_toggles": "🎛 Глобальные переключатели",
    "menu_section_stats": "📈 Статистика",
    "menu_section_autodelivery": "📦 Авто-выдача",
    "menu_section_autoresponse": "💬 Автоответчик",
    "menu_section_blacklist": "🚫 Чёрный список",
    "menu_section_notifications": "🔔 Уведомления",
    "menu_section_stub": "⏸ В разработке",
    "menu_section_plugins": "🧩 Плагины",
    "menu_section_settings": "⚙️ Настройки",
    "menu_btn_digest": "📊 Сводка сейчас",
    "btn_reply_menu": "Меню",
    "menu_keyboard_hint": "📋 Кнопка «Меню» — под полем ввода. Нажми на стрелку, чтобы свернуть её в компактный вид.",
    "module_autodelivery": "Авто-выдача",
    "module_autoraise": "Автоподнятие",
    "module_autoresponse": "Автоответчик",
    "module_autorestore": "Автовосстановление",
    "module_greeting": "Приветствие",
    "module_online": "Вечный онлайн",
    "module_digest": "Сводка дня",
    "module_toggled_on": "Модуль «{module}» включён.",
    "module_toggled_off": "Модуль «{module}» выключен.",

    # --- Глобальные переключатели ---
    "gl_title": "🎛 <b>Глобальные переключатели</b>\n\nНажмите на модуль, чтобы включить или выключить его:",
    "gl_btn_greeting_text": "✏️ Текст приветствия",
    "gl_enter_greeting": (
        "Пришлите новый текст приветствия.\n"
        "Переменная <code>$username</code> — ник покупателя.\n\n"
        "Текущий текст:\n<code>{current}</code>"
    ),
    "gl_greeting_saved": "✅ Текст приветствия сохранён.",

    # --- Статистика ---
    "st_title": "📈 <b>Статистика продаж</b> (последние 7 дней):",
    "st_line": "• {day}: <b>{count}</b> шт. на <b>{revenue}</b>",
    "st_empty": "За последние 7 дней продаж не было.",
    "st_total_week": "Итого за 7 дней: <b>{count}</b> шт. на <b>{revenue}</b>",
    "st_total_month": "Итого за 30 дней: <b>{count}</b> шт. на <b>{revenue}</b>",

    # --- Авто-выдача ---
    "ad_title": "📦 <b>Авто-выдача</b>\n\nЛоты и остатки на складах:",
    "ad_no_lots": "Пока не настроен ни один лот.",
    "ad_lot_line": "• {name} — <b>{stock}</b> шт.",
    "ad_btn_add_lot": "➕ Добавить лот",
    "ad_lot_title": (
        "📦 Лот <b>{name}</b>\n"
        "Склад: <code>{stock_file}</code>\n"
        "Остаток: <b>{stock}</b> шт.\n"
        "Автовосстановление: {restore}\n"
        "Деактивация при пустом складе: {deactivate}"
    ),
    "ad_btn_view_stock": "👀 Показать склад",
    "ad_stock_view_title": "📦 <b>Склад «{name}»</b> — позиций: <b>{total}</b>",
    "ad_stock_view_empty": "Склад пуст.",
    "ad_stock_more": "… и ещё {count} позиций",
    "ad_btn_add_stock": "➕ Пополнить склад",
    "ad_btn_toggle_restore": "♻️ Восстановление: {state}",
    "ad_btn_toggle_deactivate": "🛑 Деактивация: {state}",
    "ad_btn_delete_lot": "🗑 Удалить лот",
    "ad_enter_lot_name": "Отправьте <b>точное название лота</b> (как на Playerok):",
    "ad_enter_stock_file": "Отправьте путь к файлу-складу (например <code>storage/stock/my_lot.txt</code>) или «-», чтобы создать его автоматически:",
    "ad_lot_added": "✅ Лот «{name}» добавлен. Склад: <code>{stock_file}</code>",
    "ad_lot_deleted": "🗑 Лот «{name}» удалён из авто-выдачи (файл склада не тронут).",
    "ad_send_stock_items": (
        "Отправьте позиции товара: текстом или файлом <code>.txt</code>.\n"
        "Одна строка — одна позиция. Для многострочных товаров (логин+пароль+инструкция) "
        "разделяйте позиции строкой <code>---</code>."
    ),
    "ad_stock_added": "✅ Добавлено позиций: <b>{count}</b>. Теперь на складе: <b>{stock}</b>.",
    "ad_lot_missing": "Лот не найден (возможно, конфиг изменился). Откройте раздел заново.",

    # --- Автоответчик ---
    "ar_title": "💬 <b>Автоответчик</b>\n\nКоманды:",
    "ar_no_commands": "Пока нет ни одной команды.",
    "ar_btn_add": "➕ Добавить команду",
    "ar_command_view": "Команда: <code>{command}</code>\n\nОтвет:\n{response}",
    "ar_btn_delete": "🗑 Удалить",
    "ar_btn_edit": "✏️ Изменить ответ",
    "ar_enter_new_response": "Пришлите новый текст ответа для команды <code>{command}</code>.",
    "ar_edited": "✅ Ответ для <code>{command}</code> обновлён.",
    "ar_enter_command": "Отправьте команду (например <code>!!привет</code>):",
    "ar_enter_response": "Отправьте текст ответа. Переменные: <code>$username</code>, <code>$chat_id</code>, <code>$date</code>, <code>$time</code>.",
    "ar_added": "✅ Команда <code>{command}</code> добавлена.",
    "ar_deleted": "🗑 Команда <code>{command}</code> удалена.",
    "ar_missing": "Команда не найдена (возможно, конфиг изменился). Откройте раздел заново.",
    "ar_builtin_commands_response": "Доступные команды:\n{commands}",

    # --- Чёрный список ---
    "bl_title": "🚫 <b>Чёрный список</b>\n\nЭтих покупателей игнорируют автоответчик и приветствие, а о их покупках приходит предупреждение.\nНажмите на ник, чтобы убрать из списка:",
    "bl_empty": "Чёрный список пуст.",
    "bl_btn_add": "➕ Добавить ник",
    "bl_enter_username": "Отправьте ник покупателя Playerok (без учёта регистра):",
    "bl_added": "🚫 <code>{username}</code> добавлен в чёрный список.",
    "bl_already": "<code>{username}</code> уже в чёрном списке.",
    "bl_removed": "✅ {username} убран из чёрного списка.",
    "bl_missing": "Ник не найден (возможно, список изменился). Откройте раздел заново.",

    # --- Сводка дня ---
    "digest_text": (
        "📊 <b>Сводка за {date}</b>\n\n"
        "🛒 Продаж: <b>{sales}</b>\n"
        "💰 Выручка: <b>{revenue}</b>\n"
        "💳 Баланс: <b>{balance}</b>\n"
        "⏱ Аптайм: <b>{uptime}</b>\n\n"
        "📦 Остатки складов:\n{stocks}"
    ),
    "digest_stock_line": "• {name} — <b>{stock}</b> шт.",
    "digest_no_stocks": "склады авто-выдачи не настроены",
    "digest_unavailable": "Модуль сводки недоступен.",

    # --- Уведомления ---
    "nt_title": "🔔 <b>Уведомления</b>\n\nНажмите, чтобы переключить:",
    "nt_new_deal": "Новая сделка",
    "nt_item_paid": "Оплата лота",
    "nt_delivery": "Выдача товара",
    "nt_new_message": "Новые сообщения",
    "nt_new_review": "Новые отзывы",
    "nt_deal_problem": "Проблемы в сделках",
    "nt_deal_confirmed": "Подтверждение сделок",
    "nt_deal_rolled_back": "Возвраты сделок",
    "nt_item_raised": "Поднятие лотов",
    "nt_insufficient_balance": "Нехватка баланса",
    "nt_errors": "Ошибки",
    "nt_stock_empty": "Пустой склад",
    "nt_blacklist": "Сделки с ЧС",

    # --- Тексты уведомлений ---
    "notif_started": (
        "🐦 <b>PlayerokCardinal запущен</b>\n"
        "👤 Аккаунт: <b>{username}</b>\n"
        "💰 Баланс: <b>{balance}</b>\n"
        "🌙 Пропущенные сделки: <b>{missed_deals}</b>\n"
        "📩 Новые сообщения: <b>{unread_messages}</b>\n"
        "🧩 Модули: {modules}"
    ),
    "notif_new_deal": (
        "🛒 <b>Новая сделка</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "👤 <b>Покупатель:</b> {buyer}\n"
        "📋 <b>Статус:</b> {status}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Цена:</b> {price} ₽\n"
        "🤖 <i>Авто-выдача активна</i>\n\n"
        "💬 <i>Ответ на сообщение, отвечает в чат</i>\n"
        "🆔 <code>{chat_id}</code>"
    ),
    "notif_item_paid": (
        "💸 <b>Лот оплачен</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "👤 <b>Покупатель:</b> {buyer}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Цена:</b> {price} ₽"
    ),
    "notif_delivery_ok": (
        "📦 <b>Товар выдан</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "📊 <b>Остаток на складе:</b> {stock} шт."
    ),
    "notif_new_message": (
        "💌 <b>{username}</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "💬 {text}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Ответ на сообщение, отвечает в чат</i>"
    ),
    "notif_payout": (
        "💳 <b>Выплата с баланса</b>\n\n"
        "💸 <b>Сумма:</b> <code>-{amount} ₽</code>\n"
        "🏦 <b>Способ:</b> {method}\n"
        "📋 <b>Статус:</b> {status}\n"
        "🕒 <b>Дата:</b> {date}\n"
        "💰 <b>Остаток:</b> {balance}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Ответ на сообщение, отвечает в чат</i>"
    ),
    "notif_item_expiring": (
        "⏳ <b>Лот скоро снимут с продажи</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "📂 <b>Раздел:</b> {section}\n"
        "💰 <b>Цена:</b> {price}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Ответ на сообщение, отвечает в чат</i>"
    ),
    "notif_item_expiring_plain": (
        "⏳ <b>Лот скоро снимут с продажи</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Ответ на сообщение, отвечает в чат</i>"
    ),
    "notif_support_in_deal_chat": (
        "✉️ <b>{username}</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "👤 <b>Покупатель:</b> {buyer}\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "💬 {text}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Поддержка просматривает чат сделки. Ответьте для продолжения диалога.</i>"
    ),
    "notif_new_review": (
        "⭐ <b>Новый отзыв</b>\n\n"
        "👤 <b>Автор:</b> {author}\n"
        "⭐ <b>Оценка:</b> {rating}/5\n\n"
        "💬 {text}"
    ),
    "notif_deal_problem": (
        "⚠️ <b>Проблема в сделке</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🆔 <b>ID сделки:</b> <code>{deal_id}</code>"
    ),
    "notif_deal_problem_resolved": (
        "✅ <b>Проблема решена</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🆔 <b>ID сделки:</b> <code>{deal_id}</code>"
    ),
    "notif_deal_confirmed": (
        "🤝 <b>Сделка подтверждена</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "👤 <b>Покупатель:</b> {buyer}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Цена:</b> {price} ₽\n\n"
        "🆔 <code>{chat_id}</code>"
    ),
    "notif_deal_rolled_back": (
        "↩️ <b>Сделка возвращена</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}"
    ),
    "notif_item_raised": (
        "📈 <b>Лот поднят</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "💸 <b>Потрачено:</b> {spent} ₽"
    ),
    "notif_insufficient_balance": (
        "💸 <b>Не хватает баланса</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "💰 <b>Нужно:</b> {price} ₽\n"
        "📊 <b>Доступно:</b> {available} ₽"
    ),
    "notif_error": (
        "🚨 <b>Ошибка Cardinal</b>\n\n"
        "<pre>{error}</pre>"
    ),
    "notif_stock_empty": (
        "📭 <b>Склад пуст</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "Пополните склад, чтобы авто-выдача продолжила работать."
    ),
    "notif_restore_ok": (
        "♻️ <b>Лот восстановлен</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "🆔 <b>Новый ID:</b> <code>{item_id}</code>"
    ),
    "notif_restore_fail": (
        "♻️❌ <b>Ошибка восстановления</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "<pre>{error}</pre>"
    ),
    "notif_restore_premium_fallback": (
        "♻️⚠️ <b>Лот восстановлен бесплатно</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "🆔 <b>Новый ID:</b> <code>{item_id}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Премиум-статус не оплатился: {reason}"
    ),
    "notif_blacklist_deal": (
        "🚫 <b>Сделка с покупателем из ЧС</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "👤 <b>Покупатель:</b> {buyer}\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Проверьте сделку вручную"
    ),
    "reply_sent": "✅ Отправлено в чат Playerok.",
    "reply_failed": "❌ Не удалось отправить: {error}",
    "reply_unknown": "Не понимаю, куда отправить: ответьте на уведомление о сообщении.",

    # --- Система ---
    "settings_title": "⚙️ <b>Настройки</b>",
    "sys_btn_logs": "📄 Логи",
    "sys_btn_backup": "💾 Бэкап",
    "sys_backup_caption": "💾 Бэкап конфигов и данных Cardinal.\n⚠️ Внутри cookies аккаунта — не пересылайте архив никому!",
    "sys_btn_reload": "🔄 Перезагрузить конфиги",
    "sys_btn_update": "⬇️ Обновить с GitHub",
    "sys_update_confirm": (
        "Скачать последнюю версию с GitHub (<code>{repo}</code>) и перезапустить Cardinal?\n\n"
        "configs/, storage/ и ваши plugins/ не затираются."
    ),
    "sys_btn_update_yes": "Да, обновить",
    "sys_update_running": "⬇️ Скачиваю обновление с GitHub…",
    "sys_update_ok": "✅ {message}",
    "sys_update_ok_restart": (
        "✅ {message}\n{detail}\n\n🔁 Перезапускаюсь с новой версией… "
        "Панель вернётся через несколько секунд (/menu)."
    ),
    "sys_update_failed": "❌ Обновление не удалось: {message}",
    "sys_btn_restart": "🔁 Перезапустить",
    "sys_restart_confirm": "Перезапустить Cardinal? Бот будет недоступен несколько секунд.",
    "sys_btn_restart_yes": "Да, перезапустить",
    "sys_restart_done": "🔁 Перезапускаюсь… Панель вернётся через несколько секунд (/menu).",
    "sys_btn_shutdown": "🛑 Выключить Cardinal",
    "sys_logs_title": "Последние строки лога:",
    "sys_logs_empty": "Файл лога пуст или ещё не создан.",
    "sys_reloaded": "🔄 Конфиги перезагружены: {details}",
    "sys_shutdown_confirm": "Точно выключить Cardinal? Запустить обратно можно только с сервера.",
    "sys_btn_shutdown_yes": "Да, выключить",
    "sys_shutdown_done": "🛑 Выключаюсь…",

    # --- Очистка уведомлений ---
    "sys_btn_clear": "🗑 Очистить уведомления",
    "clear_title": "🗑 <b>Очистка уведомлений</b>",
    "clear_today": "📅 За 24 часа",
    "clear_week": "📅 За 7 дней",
    "clear_all": "🗑 Все уведомления",
    "clear_result": "🗑 Удалено сообщений: {removed}\n⚠️ Ошибок: {failed}",

    # --- Тесты UI ---
    "sys_btn_tests": "🧪 Тесты",
    "test_title": "🧪 <b>Тесты уведомлений</b>",
    "test_user_message": "👤 Сообщение от Test",
    "test_support_message": "🛠 Отдельный чат поддержки",
    "test_support_in_deal": "🛠 Поддержка в чате сделки",
    "test_new_deal": "🛒 Новая сделка",
    "test_deal_confirmed": "🤝 Сделка подтверждена",
    "test_new_review": "⭐ Новый отзыв",
    "test_delivery_ok": "📦 Успешная доставка",
    "test_error": "🚨 Ошибка",
    "test_payout": "💳 Выплата",
    "test_item_expiring": "⏳ Снятие лота",
    "test_photo": "🖼 Фото лота",

    # --- Плагины ---
    "pl_title": "🧩 <b>Плагины</b>\n\nЗагружены из папки <code>plugins/</code>:",
    "pl_no_plugins": "Плагины не найдены.",
    "pl_line": "{state} {name} <i>{version}</i>",
    "pl_btn_install": "➕ Установить плагин",
    "pl_install_warning": (
        "⚠️ <b>Внимание!</b> Плагин — это исполняемый Python-код с полным доступом к вашему "
        "аккаунту и серверу. Устанавливайте только плагины из доверенных источников.\n\n"
        "Отправьте файл <code>.py</code>, чтобы установить плагин."
    ),
    "pl_installed": "✅ Плагин «{name}» установлен и загружен.",
    "pl_install_failed": "❌ Не удалось установить плагин: {error}",
    "pl_toggled_on": "Плагин «{name}» включён.",
    "pl_toggled_off": "Плагин «{name}» выключен.",
    "pl_delete_confirm": "Удалить плагин «{name}»? Его хендлеры будут выгружены, файл удалён из папки plugins/.",
    "pl_btn_delete_yes": "Да, удалить",
    "pl_deleted": "🗑 Плагин «{name}» удалён.",
}