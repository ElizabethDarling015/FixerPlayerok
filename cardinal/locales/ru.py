"""Русская локаль PlayerokCardinal."""

STRINGS = {
    # --- Общие / авторизация в TG ---
    "unauthorized": "⛔ Вы не авторизованы. Отправьте секретный код из консоли Cardinal, чтобы привязать себя как администратора.",
    "auth_success": "✅ Вы привязаны как администратор PlayerokCardinal.",
    "auth_wrong_code": "❌ Неверный код. Актуальный код напечатан в консоли Cardinal.",
    "btn_back": "◀️ Назад",
    "btn_home": "🏠 Главное меню",
    "btn_close": "✖️ Закрыть",
    "cancelled": "✖️ Действие отменено.",
    "btn_cancel": "✖️ Отмена",

    # --- Главное меню ---
    "menu_title": (
        "🐦 <b>PlayerokCardinal</b>\n\n"
        "👤 Аккаунт: <b>{username}</b>\n"
        "💰 Баланс: <b>{balance}</b>\n"
        "⏱ Аптайм: <b>{uptime}</b>"
    ),
    "menu_section_toggles": "🎛 Глобальные переключатели",
    "menu_section_stats": "📈 Статистика",
    "menu_section_autodelivery": "📦 Авто-выдача",
    "menu_section_autoresponse": "💬 Автоответчик",
    "menu_section_blacklist": "🚫 Чёрный список",
    "menu_section_notifications": "🔔 Уведомления",
    "menu_section_plugins": "🧩 Плагины",
    "menu_section_system": "⚙️ Система",
    "menu_btn_digest": "📊 Сводка сейчас",
    "module_autodelivery": "Авто-выдача",
    "module_autoraise": "Автоподнятие",
    "module_autoresponse": "Автоответчик",
    "module_autorestore": "Автовосстановление",
    "module_greeting": "Приветствие",
    "module_postsale": "После продажи",
    "module_online": "Вечный онлайн",
    "module_digest": "Сводка дня",
    "module_autoupdate": "Проверка обновлений",
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
    "st_line": "<code>{day} {bar}</code> <b>{count}</b> шт. / <b>{revenue}</b>",
    "st_empty": "За последние 7 дней продаж не было.",
    "st_total_week": "Итого за 7 дней: <b>{count}</b> шт. на <b>{revenue}</b>",
    "st_total_month": "Итого за 30 дней: <b>{count}</b> шт. на <b>{revenue}</b>",
    "st_bot_title": "🤖 <b>Работа бота</b> (сегодня / 7 дней / всего):",
    "st_bot_delivered": "Выдано товаров: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",
    "st_bot_raised": "Поднятий лотов: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",
    "st_bot_responses": "Автоответов: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",

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
        "Деактивация при пустом складе: {deactivate}\n"
        "Свой текст выдачи: {own_text}\n"
        "Снимать с публикации при пустом складе: {auto_deact}"
    ),
    "ad_btn_view_stock": "👀 Показать склад",
    "ad_stock_view_title": "📦 <b>Склад «{name}»</b> — позиций: <b>{total}</b>",
    "ad_stock_view_empty": "Склад пуст.",
    "ad_stock_more": "… и ещё {count} позиций",
    "ad_btn_add_stock": "➕ Пополнить склад",
    "ad_btn_toggle_restore": "♻️ Восстановление: {state}",
    "ad_btn_toggle_deactivate": "🛑 Деактивация: {state}",
    "ad_btn_delete_lot": "🗑 Удалить лот",
    "ad_delete_confirm": (
        "🗑 <b>Удалить лот?</b>\n\n"
        "Лот «{name}» будет убран из авто-выдачи.\n"
        "Файл склада останется на диске."
    ),
    "ad_btn_delete_yes": "🗑 Да, удалить",
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
    "ad_btn_delivery_text": "✏️ Текст выдачи",
    "ad_enter_delivery_text": (
        "Пришлите новый текст сообщения с выдачей товара.\n"
        "Плейсхолдер <code>{{item}}</code> (обязателен) — выданная позиция со склада.\n\n"
        "Текущий текст:\n<code>{current}</code>"
    ),
    # Вызывается без kwargs — str.format не применяется, поэтому {item} здесь литерален.
    "ad_text_needs_item": "⚠️ В тексте нет <code>{item}</code> — без него покупатель не получит товар. Пришлите текст ещё раз.",
    "ad_delivery_text_saved": "✅ Текст выдачи сохранён.",
    "ad_btn_lot_delivery_text": "✏️ Текст выдачи лота",
    "ad_enter_lot_delivery_text": (
        "Пришлите текст выдачи для лота «{name}» — он будет использоваться вместо общего.\n"
        "Плейсхолдер <code>{{item}}</code> (обязателен) — выданная позиция со склада.\n"
        "Отправьте «-», чтобы вернуть лоту общий текст выдачи.\n\n"
        "Текущий текст:\n<code>{current}</code>"
    ),
    "ad_lot_delivery_text_saved": "✅ Свой текст выдачи для лота «{name}» сохранён.",
    "ad_lot_delivery_text_reset": "✅ Лот «{name}» снова использует общий текст выдачи.",

    "ad_btn_pick_lot": "🎮 Выбрать лот с Playerok",
    "ad_pick_loading": "Загружаю лоты с Playerok…",
    "ad_pick_title": "🎮 <b>Ваши лоты на Playerok</b>\n\nНажмите на лот, чтобы добавить его в авто-выдачу (✅ — уже добавлен):",
    "ad_pick_empty": "На Playerok не найдено активных лотов.",
    "ad_pick_failed": "❌ Не удалось получить лоты с Playerok:\n<code>{error}</code>\n\nДобавьте лот вручную кнопкой «➕ Добавить лот».",
    "ad_pick_already": "Лот «{name}» уже настроен.",
    "ad_pick_added": "✅ Лот «{name}» добавлен.",

    "ad_btn_test": "🧪 Тест выдачи",
    "ad_test_result": (
        "🧪 <b>Тест выдачи</b> — лот «{name}»\n\n"
        "Покупатель получил бы:\n<code>{text}</code>\n\n"
        "Остаток склада после такой выдачи: <b>{stock}</b> шт.\n"
        "Товар возвращён на склад, покупателю ничего не отправлено."
    ),
    "ad_test_empty": "🧪 Выдавать нечего: склад лота «{name}» пуст либо модуль авто-выдачи выключен.",
    "ad_btn_toggle_auto_deact": "🛑 Снимать пустые лоты: {state}",
    "ad_btn_toggle_lot_deact": "🛑 Автоснятие этого лота: {state}",

    # --- Автоответчик ---
    "ar_title": "💬 <b>Автоответчик</b>\n\nКоманды:",
    "ar_no_commands": "Пока нет ни одной команды.",
    "ar_btn_add": "➕ Добавить команду",
    "ar_command_view": "Команда: <code>{command}</code>\n\nОтвет:\n{response}",
    "ar_btn_delete": "🗑 Удалить",
    "ar_btn_edit": "✏️ Изменить ответ",
    "ar_enter_new_response": "Пришлите новый текст ответа для команды <code>{command}</code>.",
    "ar_edited": "✅ Ответ для <code>{command}</code> обновлён.",
    "ar_enter_command": "Отправьте команду (например <code>!привет</code>):",
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
    "bl_delete_confirm": "🚫 <b>Убрать из чёрного списка?</b>\n\nНик: <code>{username}</code>",
    "bl_btn_delete_yes": "✅ Да, убрать",
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
    "nt_restore": "Восстановление лотов",
    "nt_updates": "Обновления Cardinal",
    "nt_btn_all_on": "🟢 Включить все",
    "nt_btn_all_off": "🔴 Выключить все",

    # --- Тексты уведомлений ---
    "notif_started": (
        "🐦 <b>PlayerokCardinal запущен</b>\n"
        "👤 Аккаунт: <b>{username}</b>\n"
        "💰 Баланс: <b>{balance}</b>\n"
        "🧩 Модули: {modules}"
    ),
    "notif_new_deal": "🛒 <b>Новая сделка</b>\nЛот: {item}\nПокупатель: {buyer}\nСтатус: {status}",
    "notif_item_paid": "💸 <b>Лот оплачен</b>\nЛот: {item}\nПокупатель: {buyer}",
    "notif_delivery_ok": "📦 <b>Товар выдан</b>\nЛот: {item}\nОстаток на складе: {stock} шт.",
    "notif_new_message": "✉️ <b>{username}</b> (чат <code>{chat_id}</code>):\n{text}\n\n<i>Ответьте на это сообщение, чтобы написать в чат Playerok.</i>",
    "notif_new_review": "⭐ <b>Новый отзыв</b> ({rating}/5) от {author}:\n{text}",
    "notif_deal_problem": "⚠️ <b>Проблема в сделке</b>\nЛот: {item}\nСделка: <code>{deal_id}</code>",
    "notif_deal_problem_resolved": "✅ <b>Проблема решена</b>\nСделка: <code>{deal_id}</code>",
    "notif_deal_confirmed": "🤝 <b>Сделка подтверждена</b>\nЛот: {item}",
    "notif_deal_rolled_back": "↩️ <b>Сделка возвращена</b>\nЛот: {item}",
    "notif_item_raised": "📈 <b>Лот поднят</b>\nЛот: {item}\nПотрачено: {spent}",
    "notif_insufficient_balance": (
        "💸 <b>Не хватило баланса для поднятия</b>\n"
        "Лот: {item}\nНужно: {price}\nДоступно: {available}"
    ),
    "notif_error": "🚨 <b>Ошибка Cardinal</b>\n<code>{error}</code>",
    "notif_stock_empty": (
        "📭 <b>Склад пуст</b>\nЛот: {item}\n"
        "Пополните склад, чтобы авто-выдача продолжила работать."
    ),
    "notif_lot_deactivated": (
        "🛑 <b>Лот снят с публикации</b>\nЛот: {item}\n"
        "Склад опустел — лот убран с Playerok, чтобы его не купили без товара."
    ),
    "notif_lot_deactivate_fail": (
        "🛑❌ <b>Не удалось снять лот с публикации</b>\nЛот: {item}\nОшибка: {error}\n"
        "Склад пуст — проверьте лот вручную."
    ),
    "notif_restore_ok": "♻️ <b>Лот восстановлен</b>\nЛот: {item}\nНовый ID: <code>{item_id}</code>",
    "notif_restore_fail": "♻️❌ <b>Не удалось восстановить лот</b>\nЛот: {item}\nОшибка: {error}",
    "notif_restore_premium_fallback": (
        "♻️⚠️ <b>Лот восстановлен бесплатно</b>\n"
        "Лот: {item}\nНовый ID: <code>{item_id}</code>\n"
        "Премиум-статус не оплатился: {reason}."
    ),
    "notif_blacklist_deal": "🚫 <b>Сделка с покупателем из чёрного списка!</b>\nПокупатель: {buyer}\nЛот: {item}\nПроверьте сделку вручную.",
    "notif_update_available": (
        "🆕 <b>Доступно обновление Cardinal</b>\n"
        "Установлено: <code>{current}</code>\nНа GitHub: <code>{latest}</code>\n\n"
        "Установить: /menu → ⚙️ Система → ⬇️ Обновить с GitHub"
    ),
    "notif_update_installed": "🆕 <b>Обновление установлено</b>\n{message}\n\n🔁 Перезапускаюсь…",
    "notif_session_expired": (
        "🔑 <b>Сессия Playerok истекла</b>\n"
        "Причина: <code>{cause}</code>\n\n"
        "Бот больше не авторизован на Playerok. Скопируйте свежий token из браузера и "
        "отправьте новый token (или полную строку cookies) <b>ответом на это сообщение</b>, "
        "либо командой <code>/token &lt;значение&gt;</code>."
    ),
    "notif_poll_stalled": (
        "⏳ <b>Опрос Playerok не работает</b>\n"
        "Успешных опросов не было дольше {minutes} мин. — новые сделки и сообщения "
        "не отслеживаются. Проверьте сеть/прокси и cookies аккаунта."
    ),
    "notif_poll_recovered": "✅ Опрос Playerok снова работает.",
    "session_token_usage": (
        "Использование: <code>/token &lt;значение&gt;</code> — новый token (eyJ...) "
        "или полная строка cookies аккаунта Playerok."
    ),
    "session_updated": "✅ Сессия обновлена, авторизованы как <b>{username}</b>.",
    "session_update_failed": (
        "❌ Не удалось обновить сессию: {error}\n"
        "Старые cookies возвращены на место, конфиг не изменён."
    ),
    "reply_sent": "✅ Отправлено в чат Playerok.",
    "reply_failed": "❌ Не удалось отправить: {error}",
    "reply_unknown": "Не понимаю, куда отправить: ответьте на уведомление о сообщении.",

    # --- Система ---
    "sys_title": "⚙️ <b>Система</b>",
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
    "sys_logs_title": "📄 <b>Логи</b> — последние строки:",
    "sys_logs_empty": "Файл лога пуст или ещё не создан.",
    "sys_btn_logfile": "⬇️ Скачать файл лога",
    "sys_logfile_caption": "📄 Полный файл лога Cardinal.",
    "sys_reloaded": "🔄 Конфиги перезагружены: {details}",
    "sys_shutdown_confirm": "Точно выключить Cardinal? Запустить обратно можно только с сервера.",
    "sys_btn_shutdown_yes": "Да, выключить",
    "sys_shutdown_done": "🛑 Выключаюсь…",

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
