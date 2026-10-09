"""Русская локаль FixerPlayerok."""

STRINGS = {
    # --- Общие / авторизация в TG ---
    "unauthorized": "⛔ Вы не авторизованы. Отправьте секретный код из консоли Fixer, чтобы привязать себя как администратора.",
    "auth_success": "✅ Вы привязаны как администратор FixerPlayerok.",
    "auth_wrong_code": "❌ Неверный код. Актуальный код напечатан в консоли Fixer.",
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
    "chats_read_failed": "⚠️ Не удалось отметить чат прочитанным, см. лог.",
    "chats_read_slow": "⚠️ Playerok не ответил вовремя (за {seconds} с), жду ответа…",
    "chats_read_late_ok": "✅ Ответил, время выполнения {seconds} с.",
    "chats_read_late_failed": "❌ Не удалось отметить чат прочитанным (через {seconds} с), см. лог.",
    "btn_auto_publish": "📤 Автовыставление",
    "btn_last_deals": "🕒 Последние сделки",
    "wd_offline": (
        '⚠️ Playerok не подключён.\n'
        'Вывод средств доступен в онлайн-режиме.'
    ),
    "wd_failed": '❌ Не получилось: {error}',
    "wd_status_confirmed": '✅ Проведена',
    "wd_status_processing": '🔄 В обработке',
    "wd_status_pending": '⏳ В очереди',
    "wd_done": (
        '✅ <b>Заявка на вывод создана</b>\n'
        '\n'
        '💸 Сумма: <b>{amount}</b>\n'
        '📍 Куда: {destination}\n'
        '📋 Статус: {status}\n'
        '🆔 <code>{tx_id}</code>\n'
        '\n'
        'Когда Playerok проведёт выплату, придёт уведомление «Выплата с баланса».'
    ),
    "wd_sending": '⏳ Создаю заявку на вывод…',
    "wd_btn_go": '✅ Вывести',
    "wd_confirm": (
        '💳 <b>Подтвердите вывод</b>\n'
        '\n'
        '💸 Сумма: <b>{amount}</b>\n'
        '📍 Куда: {destination}\n'
        '🧾 Комиссия Playerok ≈ {fee} ({fee_rule})\n'
        '\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '⚠️ После нажатия «Вывести» заявка уйдёт на Playerok.'
    ),
    "wd_usdt_estimate": '🪙 ≈ {usdt} USDT по курсу {rate} ₽ (до комиссии)',
    "wd_err_provider_gone": 'Этот способ вывода сейчас недоступен на Playerok.',
    "wd_err_expired": 'Данные вывода устарели — начните заново: «💳 Вывод средств».',
    "wd_err_balance": 'Больше, чем доступно к выводу ({available}).',
    "wd_err_max": 'Больше максимальной суммы для этого способа ({max}).',
    "wd_err_min": 'Меньше минимальной суммы для этого способа ({min}).',
    "wd_err_amount": 'Напишите сумму целым числом в рублях, например: <code>2000</code>',
    "wd_btn_cancel": '✖️ Отмена',
    "wd_btn_all": 'Всё доступное — {amount}',
    "wd_amount_prompt": (
        '💳 <b>Вывод</b> → {destination}\n'
        '\n'
        '💰 Доступно: <b>{available}</b>\n'
        '📏 Лимиты способа: {min} – {max}\n'
        '\n'
        'Напишите сумму в рублях или нажмите кнопку:'
    ),
    "wd_err_usdt": 'Это не похоже на адрес TRC20: он начинается с <code>T</code> и состоит из 34 символов.',
    "wd_enter_usdt": (
        '🪙 Напишите адрес кошелька <b>USDT (TRC20)</b> — начинается с <code>T</code>, 34 символа.\n'
        '\n'
        '⚠️ Перевод на неверный адрес не вернуть — проверьте адрес дважды.'
    ),
    "wd_no_cards": (
        '💳 На Playerok нет привязанных карт.\n'
        'Привяжите карту в кошельке на сайте и вернитесь сюда.'
    ),
    "wd_choose_card": (
        '💳 <b>Карта для вывода</b>\n'
        '\n'
        'Выберите карту, привязанную на Playerok:'
    ),
    "wd_err_phone": 'Не похоже на российский номер. Пример: <code>+79001234567</code>',
    "wd_enter_phone": (
        '📱 На сайте нет сохранённого номера для СБП.\n'
        'Напишите номер телефона, привязанный к банку (например: <code>+79001234567</code>):'
    ),
    "wd_err_bank_not_found": 'Банк не найден — попробуйте другое название.',
    "wd_enter_bank": '🔍 Напишите часть названия банка (например: <code>альфа</code>):',
    "wd_choose_bank": (
        '🏦 <b>Банк получателя (СБП)</b>\n'
        '\n'
        'Выберите банк или найдите его по названию:'
    ),
    "wd_btn_bank_search": '🔍 Найти другой банк',
    "wd_btn_repeat": '⚡ Как в прошлый раз: {label}',
    "wd_site_only": '<i>только на сайте</i>',
    "wd_methods_header": '<b>Способы</b> (комиссия · лимиты):',
    "wd_available": '💰 Доступно к выводу: <b>{amount}</b>',
    "wd_title": '💳 <b>Вывод средств</b>',
    "btn_withdraw": '💳 Вывод средств',
    "ld_failed": '⚠️ Не удалось загрузить сделки: {error}',
    "ld_offline": (
        '⚠️ Playerok не подключён.\n'
        'Раздел «Последние сделки» доступен в онлайн-режиме.'
    ),
    "ld_btn_refresh": '🔄 Обновить',
    "ld_page": '<i>📄 Стр. {page}</i>',
    "ld_empty": 'Продаж пока нет.',
    "ld_entry": (
        '📂 <b>Раздел:</b> {section}\n'
        '🎁 <b>Лот:</b> {item}\n'
        '👤 <b>Покупатель:</b> {buyer} | 💰 <b>Цена:</b> {price}\n'
        '{state}'
    ),
    "ld_title": '🕒 <b>Последние сделки</b>',
    "ld_review": ' · ⭐ {rating}',
    "ld_state_unknown": '❔ {status}',
    "ld_state_problem": '⚠️ Проблема в сделке',
    "ld_state_rolled_back": '↩️ Возврат',
    "ld_state_auto": '✅ Завершено автоматически',
    "ld_state_confirmed": '✅ Завершено',
    "ld_state_sent": '⏳ Не подтвердил',
    "ld_state_paid": '💰 Оплачено, ждёт выдачи',
    "alert_in_development": "⏸ Раздел «{section}» в разработке — появится в следующих обновлениях.",
    "btn_close": "❌ Закрыть",
    "cancelled": "Действие отменено.",
    "stub_message": "⏸ Раздел перенесён в Настройки",
    "btn_cancel": "Отмена",

    # --- Главное меню ---
    "menu_title": (
        "🐦 <b>FixerPlayerok</b>\n\n"
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
    "menu_section_plugins": "🧩 Плагины",
    "menu_section_settings": "⚙️ Настройки",
    "menu_btn_digest": "📊 Сводка сейчас",
    "btn_reply_menu": "Меню",
    "menu_keyboard_hint": "📋 Кнопка «Меню» — под полем ввода. Нажми на стрелку, чтобы свернуть её в компактный вид.",
    "module_autodelivery": "Авто-выдача",
    "module_autoraise": "Автоподнятие",
    "module_autoresponse": "Автоответчик",
    "module_autorestore": "Автовосстановление",
    "module_online": "Вечный онлайн",
    "module_digest": "Сводка дня",
    "module_toggled_on": "Модуль «{module}» включён.",
    "module_toggled_off": "Модуль «{module}» выключен.",

    # --- Глобальные переключатели ---
    "gl_title": "🎛 <b>Глобальные переключатели</b>\n\nНажмите на модуль, чтобы включить или выключить его:",

    # --- Статистика ---
    "st_title": (
        '📈 <b>Статистика продаж</b>\n'
        '<i>по данным Playerok, последние 7 дней</i>\n'
    ),
    "digest_stocks_block": (
        '\n'
        '\n'
        '📦 Остатки складов авто-выдачи:\n'
        '{stocks}'
    ),
    "st_offline": (
        '⚠️ Playerok не подключён.\n'
        'Статистика и сводка доступны в онлайн-режиме.'
    ),
    "st_failed": '⚠️ Не удалось загрузить историю продаж с Playerok: {error}',
    "st_refunds_month": '↩️ Возвратов за 30 дней: <b>{refunds}</b>',
    "st_line_refunds": ' · ↩️ {refunds}',
    "st_line": '• {day}: <b>{count}</b> шт. · {gross} (на руки {net})',
    "st_empty": 'За последние 7 дней продаж не было.',
    "st_total_week": 'За 7 дней: <b>{count}</b> шт. · <b>{gross}</b> (на руки {net})',
    "st_total_month": 'За 30 дней: <b>{count}</b> шт. · <b>{gross}</b> (на руки {net})',

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
    "bl_title": (
        '🚫 <b>Чёрный список</b>\n'
        '\n'
        'О покупках этих покупателей приходит предупреждение. После первой сделки бот запоминает ID покупателя — смена ника не поможет.\n'
        'Нажмите на ник, чтобы убрать из списка:'
    ),
    "bl_empty": "Чёрный список пуст.",
    "bl_btn_add": "➕ Добавить ник",
    "bl_enter_username": "Отправьте ник покупателя Playerok (без учёта регистра):",
    "bl_added": "🚫 <code>{username}</code> добавлен в чёрный список.",
    "bl_already": "<code>{username}</code> уже в чёрном списке.",
    "bl_removed": "✅ {username} убран из чёрного списка.",
    "bl_missing": "Ник не найден (возможно, список изменился). Откройте раздел заново.",

    # --- Сводка дня ---
    "digest_text": (
        '📊 <b>Сводка за {date}</b>\n'
        '\n'
        '🛒 Продаж: <b>{sales}</b>\n'
        '💰 Выручка: <b>{revenue}</b> (на руки {net})\n'
        '↩️ Возвратов: <b>{refunds}</b>\n'
        '💳 Баланс: <b>{balance}</b>\n'
        '⏱ Аптайм: <b>{uptime}</b>{stocks}'
    ),
    "digest_stock_line": "• {name} — <b>{stock}</b> шт.",
    "digest_unavailable": "Модуль сводки недоступен.",

    # --- Уведомления ---
    "nt_title": "🔔 <b>Уведомления</b>\n\nНажмите, чтобы переключить:",
    "nt_new_deal": "Новая сделка",
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
        "🐦 <b>FixerPlayerok запущен</b>\n"
        "👤 Аккаунт: <b>{username}</b>\n"
        "💰 Баланс: <b>{balance}</b>\n"
        "🌙 Пропущенные сделки: <b>{missed_deals}</b>\n"
        "📩 Новые сообщения: <b>{unread_messages}</b>\n"
        "🧩 Модули: {modules}"
    ),
    "notif_new_deal": (
        '🛒 <b>Новая сделка</b>\n'
        '\n'
        '📂 <b>Раздел:</b> {section}\n'
        '🎁 <b>Лот:</b> {item}\n'
        '👤 <b>Покупатель:</b> {buyer}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '💰 <b>Цена:</b> {price} ₽{autodelivery}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "menu_closed": '✖️ Меню закрыто.',
    "payout_line_balance": '💰 <b>Остаток:</b> {balance} ₽',
    "payout_line_date": '🕒 <b>Дата:</b> {date}',
    "payout_line_status": '📋 <b>Статус:</b> {status}',
    "payout_line_method": '🏦 <b>Способ:</b> {method}',
    "payout_line_amount": '💸 <b>Сумма:</b> <code>-{amount} ₽</code>',
    "notif_system_lot": (
        '\n'
        '\n'
        '🎁 <b>Лот:</b> {lot}'
    ),
    "notif_system_message": (
        '📢 <b>Уведомление Playerok</b>\n'
        '\n'
        '💬 {text}{lot}'
    ),
    "notif_place_deal_chat": '🛒 Чат с покупателем {buyer}',
    "notif_staff_finished": (
        '✅ <b>Чат завершён</b>\n'
        '{place}\n'
        '👤 {staff}'
    ),
    "notif_staff_started": (
        '👀 <b>Смотрим чат…</b>\n'
        '{place}\n'
        '👤 {staff}'
    ),
    "notif_support_message": (
        '🛟 <b>Поддержка Playerok</b>\n'
        '👤 {staff}\n'
        '\n'
        '💬 {text}\n'
        '\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '<i>Ответ на сообщение, отвечает в чат поддержки</i>'
    ),
    "deal_confirm_offline": '⚠️ Playerok не подключён — подтвердить выдачу сейчас нельзя.',
    "deal_confirm_failed": '❌ Не удалось подтвердить выдачу: {error}',
    "deal_confirm_test": '✅ Выдача подтверждена (это тестовое уведомление — на Playerok ничего не отправлено).',
    "deal_confirm_ok": '✅ Выдача подтверждена.',
    "deal_btn_collapse": '➖ Свернуть',
    "deal_btn_confirm": '✅ Подтвердить выдачу',
    "notif_new_deal_short": (
        '🛒 <b>Раздел:</b> {section}\n'
        '🎁 <b>Лот:</b> {item}\n'
        '👤 <b>Купил:</b> {buyer}\n'
        '💰 <b>Цена:</b> {price}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "notif_new_deal_autodelivery": (
        '\n'
        '🤖 <i>Авто-выдача активна</i>'
    ),
    "notif_delivery_ok": (
        "📦 <b>Товар выдан</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "📊 <b>Остаток на складе:</b> {stock} шт."
    ),
    "notif_new_message": (
        '💌 <b>Сообщение от {username}!</b>\n'
        '💬:{text}\n'
        '\n'
        '🎁 <b>Лот:</b> {item}'
    ),
    "notif_payout": (
        '💳 <b>Выплата с баланса</b>\n'
        '\n'
        '{details}━━━━━━━━━━━━━━━━━━━\n'
        '💬 {text}'
    ),
    "notif_item_expiring": (
        "⏳ <b>Лот скоро снимут с продажи</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "📂 <b>Раздел:</b> {section}\n"
        "💰 <b>Цена:</b> {price}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}"
    ),
    "notif_item_expiring_plain": (
        "⏳ <b>Лот скоро снимут с продажи</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}"
    ),
    "notif_support_in_deal_chat": (
        '🛟 <b>Поддержка в сделке</b>\n'
        '👤 {staff}\n'
        '\n'
        '🛒 <b>Покупатель:</b> {buyer}\n'
        '🎁 <b>Лот:</b> {item}\n'
        '\n'
        '💬 {text}\n'
        '\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '<i>Ответ на сообщение, отвечает в чат сделки</i>'
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
        "🎁 <b>Лот:</b> {item}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🆔 <b>ID сделки:</b> <code>{deal_id}</code>"
    ),
    "notif_deal_problem_resolved": (
        "✅ <b>Проблема решена</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🆔 <b>ID сделки:</b> <code>{deal_id}</code>"
    ),
    "notif_deal_confirmed": (
        "🤝 <b>Сделка подтверждена</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "🎁 <b>Лот:</b> {item}\n"
        "👤 <b>Покупатель:</b> {buyer}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Цена:</b> {price} ₽\n"
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
        "🚨 <b>Ошибка Fixer</b>\n\n"
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
    "reply_offline": "🤬 Нет связи с Playerok — сообщение не отправлено.",
    "reply_refused": "🤷 Playerok не принял сообщение. Посмотрите лог: Настройки → 📄 Логи.",

    # --- Система ---
    "settings_title": "⚙️ <b>Настройки</b>",
    "sys_btn_logs": "📄 Логи",
    "sys_btn_backup": "💾 Бэкап",
    "sys_backup_caption": "💾 Бэкап конфигов и данных Fixer.\n⚠️ Внутри cookies аккаунта — не пересылайте архив никому!",
    "sys_btn_reload": "🔄 Перезагрузить конфиги",
    "sys_btn_update": "⬇️ Обновить с GitHub",
    "sys_update_confirm": (
        "Скачать последнюю версию с GitHub (<code>{repo}</code>) и перезапустить Fixer?\n\n"
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
    "sys_logs_title": "Последние строки лога:",
    "sys_logs_empty": "Файл лога пуст или ещё не создан.",
    "sys_reloaded": "🔄 Конфиги перезагружены: {details}",

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
    "test_support_message": '🛟 Чат поддержки',
    "test_support_in_deal": '🛟 Поддержка в сделке',
    "test_new_deal": "🛒 Новая сделка",
    "test_deal_confirmed": "🤝 Сделка подтверждена",
    "test_new_review": "⭐ Новый отзыв",
    "test_delivery_ok": "📦 Успешная доставка",
    "test_error": "🚨 Ошибка",
    "test_payout": "💳 Выплата",
    "test_item_expiring": "⏳ Снятие лота",
    "test_blacklist": '🚫 Сделка с ЧС',
    "test_system_notice": '📢 Уведомление Playerok',
    "test_staff_event": '👀 Смотрим чат',
    "test_staff_finished": "✅ Чат завершён",
    "test_item_expiring_plain": "⏳ Снятие (лот не найден)",
    "test_deal_problem": "⚠️ Проблема в сделке",
    "test_problem_resolved": "✅ Проблема решена",
    "test_rolled_back": "↩️ Сделка возвращена",
    "test_item_raised": "📈 Лот поднят",
    "test_no_balance": "💸 Не хватает баланса",
    "test_stock_empty": "📭 Склад пуст",
    "test_restore_ok": "♻️ Лот восстановлен",
    "test_restore_fail": "♻️❌ Ошибка восстановл.",
    "test_restore_free": "♻️⚠️ Восст. бесплатно",
    "test_started": "🐦 Бот запущен",
    "test_page_1": "📄 <b>Страница 1:</b> сообщения, поддержка, сделки",
    "test_page_2": "📄 <b>Страница 2:</b> проблемы, модули, служебные",

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