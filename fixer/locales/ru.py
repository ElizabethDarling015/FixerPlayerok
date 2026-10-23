"""Русская локаль FixerPlayerok."""

STRINGS = {
    # --- Общие / авторизация в TG ---
    "unauthorized": "⛔ Вы не авторизованы. Отправьте секретный код из консоли Fixer, чтобы привязать себя как администратора.",
    "auth_success": "✅ Вы привязаны как администратор FixerPlayerok.",
    "btn_back": "◀️ Назад",
    "btn_home": "🏠 Главное меню",
    "btn_chats": "💬 Чаты с покупателями",
    "chats_empty": "Нет активных чатов.",
    "chats_view_title": "💬 <b>Чат с {username}</b>\n\n",
    "chats_btn_reply": "✏️ Ответить в чат",
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
    "btn_items": "🛍 Товары",
    "it_title": "🛍 <b>Товары</b>\nВ продаже: <b>{on_sale}</b> · На модерации: <b>{moderation}</b>\n\nВыберите раздел:",
    "it_empty": "Активных лотов нет.",
    "it_btn_inactive": "⏸ Снятые и заблокированные",
    "it_btn_refresh": "🔄 Обновить",
    "it_section_title": "📂 <b>{section}</b> — лотов: <b>{count}</b>\n\n🔁 — включено автовыставление",
    "it_inactive_title": "⏸ <b>Снятые и заблокированные</b>\n⏸ Сняты вами: <b>{discontinued}</b>\n⛔ Заблокированы: <b>{blocked}</b>\n🔴 Отклонены: <b>{declined}</b>\n🟠 Истёк срок: <b>{expired}</b>",
    "it_inactive_empty": "Таких лотов нет.",
    "it_card_title": "🎁 <b>{name}</b>",
    "it_card_section": "📂 {section}",
    "it_card_price": "💰 <b>{price} ₽</b> · {status} · {priority}",
    "it_card_until": "🗓 В продаже до {until}",
    "it_card_stats": "👁 Просмотров: {views} · 🛒 Продаж: {deals}",
    "it_card_reason": "⚠️ <b>Причина:</b> {reason}",
    "it_card_comment": "💬 <b>Комментарий:</b>\n<blockquote expandable>{comment}</blockquote>",
    "it_card_no_comment": "💬 Комментария нет",
    "it_card_keep": "🔁 Автовыставление: {state}",
    "it_card_autodelivery": "📦 Автовыдача: {state}",
    "it_autodelivery_on": "вкл, на складе {stock} шт.",
    "it_on": "вкл",
    "it_off": "выкл",
    "it_premium": "🚀 Премиум",
    "it_free": "Обычный",
    "it_status_approved": "В продаже",
    "it_status_pending_moderation": "На модерации",
    "it_status_pending_approval": "Ждёт проверки",
    "it_status_expired": "Истёк срок",
    "it_status_declined": "Отклонён",
    "it_status_blocked": "Заблокирован",
    "it_status_discontinued": "Снят с продажи",
    "it_status_sold": "Продан",
    "it_status_draft": "Черновик",
    "it_btn_keep": "🔁 Автовыставление: {state}",
    "it_btn_comment": "💬 Комментарий",
    "it_btn_price": "💰 Цена",
    "it_btn_raise": "⬆️ Поднять",
    "it_btn_pause": "⏸ Снять с продажи",
    "it_btn_resume": "▶️ Вернуть в продажу",
    "it_btn_publish": "🔄 Выставить заново",
    "it_btn_site": "🌐 Открыть на сайте",
    "it_btn_pay": "✅ {label} · {price} ₽",
    "it_raise_confirm": "⬆️ <b>Поднять в топ</b>\n🎁 {name}\n\nДеньги спишутся с баланса Playerok. Срок выставления начнётся заново (30 дней).",
    "it_publish_confirm": "🔄 <b>Выставить заново</b>\n🎁 {name}\n\nВыберите статус. Платный списывается с баланса Playerok.",
    "it_no_statuses": "Playerok не предложил ни одного варианта — попробуйте на сайте.",
    "it_pending_expired": "Экран оплаты устарел — откройте лот заново.",
    "it_raised": "✅ Лот поднят, списано {price} ₽.",
    "it_published": "✅ Лот выставлен, списано {price} ₽.",
    "it_keep_on": "🔁 Автовыставление включено",
    "it_keep_off": "🔁 Автовыставление выключено",
    "it_keep_unknown": "Playerok не прислал, включено ли автовыставление у этого лота, — ничего не меняю. Откройте лот на сайте.",
    "it_paused": "⏸ Лот снят с продажи",
    "it_resumed": "▶️ Лот снова в продаже",
    "it_enter_comment": "💬 Пришлите новый <b>комментарий</b> — его получит покупатель после оплаты.\n\nПосле правки комментария лот ненадолго уходит на модерацию.",
    "it_enter_price": "💰 Пришлите новую <b>цену</b> в рублях (только число).",
    "it_bad_price": "Нужна цена числом, например 330.",
    "it_bad_comment": "Пришлите текст комментария (не пустой и не команду).",
    "it_comment_saved": "✅ Комментарий сохранён. Лот ненадолго ушёл на модерацию.",
    "it_price_saved": "✅ Цена изменена: {price} ₽.",
    "it_offline": "⚠️ Playerok не подключён — раздел «Товары» доступен в онлайн-режиме.",
    "it_forbidden": "❌ Playerok не разрешает это действие для лота в таком статусе.",
    "it_failed": "❌ Не получилось: {error}",
    "it_load_failed": "🛍 <b>Товары</b>\n\n❌ Не удалось загрузить лоты: {error}",
    "it_not_found": "Лот не найден — возможно, он удалён.",
    "btn_last_deals": "🕒 Последние сделки",
    "wd_offline": (
        '⚠️ Playerok не подключён.\n'
        'Вывод средств доступен в онлайн-режиме.'
    ),
    "wd_failed": '❌ Не получилось: {error}',
    "wd_status_confirmed": '✅ Проведена',
    "wd_status_processing": '🔄 В обработке',
    "wd_status_pending": '⏳ В очереди',
    "wd_status_rolled_back": '↩️ Возвращена',
    "wd_status_failed": '❌ Не прошла',
    "wd_history_entry": (
        '💸 <b>-{amount}</b> · {method}\n'
        '🕒 {date} · {status}'
    ),
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
        '{state}{date}'
    ),
    "ld_date": '\n🗓 {date}',
    "ld_title": '🕒 <b>Последние сделки</b>',
    "ld_review": ' · ⭐ {rating}',
    "ld_state_unknown": '❔ {status}',
    "ld_state_problem": '⚠️ Проблема в сделке',
    "ld_state_rolled_back": '↩️ Возврат',
    "ld_state_auto": '✅ Завершено автоматически',
    "ld_state_confirmed": '✅ Завершено',
    "ld_state_sent": '⏳ Не подтвердил',
    "ld_state_paid": '💰 Оплачено, ждёт выдачи',
    "btn_deals_in_work": '⏳ Сделки в работе',
    "dw_btn_count": '⏳ Сделки в работе ({count})',
    "dw_title": '⏳ <b>Сделки в работе: {count}</b>',
    "dw_empty": 'Всё подтверждено, споров нет.',
    "dw_syncing": '<i>Сверяюсь с Playerok — нажмите «🔄 Обновить» через пару секунд.</i>',
    "dw_entry": (
        '{n}. <b>{item}</b>\n'
        '📂 {section}\n'
        '👤 {buyer} · 💰 {price}\n'
        '🕒 {date}{problem}'
    ),
    "dw_problem": ' · ⚠️ Спор',
    "dw_offline": '⚠️ Playerok не подключён. Раздел «Сделки в работе» доступен в онлайн-режиме.',
    "dw_card_title": '⏳ <b>Сделка в работе</b>',
    "dw_card_done_title": '✅ <b>Выдача подтверждена</b>',
    "dw_card": (
        '🎁 <b>Лот:</b> {item}\n'
        '📂 <b>Раздел:</b> {section}\n'
        '👤 <b>Покупатель:</b> {buyer} | 💰 <b>Цена:</b> {price}\n'
        '🕒 <b>Оплачена:</b> {date}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "dw_card_problem": '⚠️ <b>Открыт спор</b>',
    "dw_card_sent": '✅ Выдача подтверждена, ждём решения спора',
    "dw_btn_confirmed": '✅ Выдача подтверждена',
    "dw_btn_give": '📦 Выдать со склада',
    "dw_btn_given": '📦 Товар выдан',
    "dw_gone": 'Этой сделки уже нет в работе.',
    "dw_already_sent": 'Выдача по этой сделке уже подтверждена — ждём решения спора.',
    "dw_give_ok": '📦 Товар отправлен покупателю в чат сделки.',
    "dw_give_none": '📦 Автовыдача для этого лота не настроена.',
    "dw_give_empty": '📦 Склад этого лота пуст.',
    "dw_give_given": '📦 Товар по этой сделке уже выдан.',
    "dw_give_no_chat": '⚠️ Не удалось найти чат сделки.',
    "dw_give_failed": '❌ Товар не отправлен: {error}\nПозиция возвращена на склад.',
    "btn_close": "❌ Закрыть",
    "cancelled": "Действие отменено.",
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
    "menu_section_profile": "👤 Профиль",
    "pf_title": '👤 <b>Профиль</b>',
    "pf_name": '👤 <b>{username}</b>',
    "pf_id": '🆔 <code>{id}</code>',
    "pf_email": '📪 {email}',
    "pf_rating": '⭐ Рейтинг: <b>{rating}</b> · 💬 Отзывов: <b>{reviews}</b>',
    "pf_verified_yes": '✅ Верифицирован',
    "pf_verified_no": '☑️ Не верифицирован',
    "pf_blocked": '⛔ <b>Аккаунт заблокирован</b>',
    "pf_blocked_until": '⛔ <b>Заблокирован до {until}</b>',
    "pf_created": '🗓 На Playerok с {date}',
    "pf_balance": '💰 Баланс: <b>{value}</b>',
    "pf_available": '・ 👜 Доступно: {value}',
    "pf_withdrawable": '・ 💸 К выводу: {value}',
    "pf_pending": '・ ⌛ В обработке: {value}',
    "pf_frozen": '・ ❄️ Заморожено: {value}',
    "pf_items": '📦 Лоты: в продаже <b>{active}</b> · сняты и истекли <b>{inactive}</b>',
    "pf_sales": '🛒 Продажи: <b>{total}</b> · ✅ завершено {done} · ⏳ в работе {active} · ↩️ возвратов {refund}',
    "pf_purchases": '🛍 Покупки: <b>{total}</b>',
    "pf_failed": '⚠️ Не удалось загрузить профиль: {error}',
    "pf_offline": '⚠️ Playerok не подключён. Профиль доступен в онлайн-режиме.',
    "menu_section_autoraise": "⬆️ Автоподнятие",
    "up_title": '⬆️ <b>Автоподнятие</b> {status} · {time}',
    "up_title_short": '⬆️ <b>Автоподнятие</b>',
    "up_on": '🟢 Включено',
    "up_off": '🔴 Выключено',
    "up_day": '☀️ День',
    "up_night": '🌙 Ночь',
    "up_allday": '🕒 Сутки',
    "up_mode_position_line": '📊 Режим: по позиции — держать в топ-<b>{position}</b>',
    "up_check_line": '⏱️ Проверка: раз в {check}',
    "up_cooldown_line": '🕒 Кулдаун: {cooldown}',
    "up_streak_line": '🔁 Проверок подряд: {streak}',
    "up_limit_value": 'Лимит {limit}',
    "up_no_limit_cap": 'Без лимита',
    "up_mode_interval_line": '⏰ Режим: по интервалу — раз в <b>{interval}</b>',
    "up_next_run": '⏭ Следующее поднятие: {time}',
    "up_night_pos": 'топ-{position}',
    "up_night_int": 'раз в {interval}',
    "up_night_line": '🌙 Ночь {start}–{end}: {value} | {limit}',
    "up_spent_line": '💸 Потрачено {window}: <b>{spent}</b> | {limit}',
    "up_reserve_line": '💰 Неснижаемый остаток: {reserve}',
    "up_no_limit": 'без лимита',
    "up_no_items": 'Лоты не отмечены — нажмите «🛍 Лоты».',
    "up_positions_head": '📊 <b>Позиции</b>',
    "up_checked_at": '(проверено в {time})',
    "up_items_head": '🛍 <b>Отмеченные лоты</b>',
    "up_item_ok": '{pos} место ✅',
    "up_item_low": '{pos} место ⬆️ ({streak} из {need})',
    "up_item_unchecked": 'ещё не проверен',
    "up_item_waiting": 'ждёт интервала',
    "up_item_not_premium": '⚠️ не премиум — поднять нельзя',
    "up_item_not_active": '⚠️ не в продаже',
    "up_item_not_found": '⚠️ лот не найден',
    "up_item_error": '⚠️ не удалось проверить',
    "up_hint": '<i>Поднимаются только отмеченные премиум-лоты. Цена поднятия — по цене лота (9–75 ₽).</i>',
    "up_btn_on": '🟢 Включено',
    "up_btn_off": '🔴 Выключено',
    "up_btn_mode_position": '📊 Режим: по позиции',
    "up_btn_mode_interval": '⏰ Режим: по интервалу',
    "up_btn_pos": '📊 Место: {value}',
    "up_btn_chk": '⏱ Проверка: {value}',
    "up_btn_cd": '🕒 Кулдаун: {value}',
    "up_btn_streak": '🔁 Подряд: {value}',
    "up_btn_int": '⏰ Интервал: {value}',
    "up_btn_dl": '☀️ Лимит днём: {value}',
    "up_btn_dl_all": '💸 Лимит в сутки: {value}',
    "up_btn_res": '💰 Остаток: {value}',
    "up_btn_night_on": '🌙 Ночной режим: включён',
    "up_btn_night_off": '🌙 Ночной режим: выключен',
    "up_btn_nf": '🌙 С: {value}',
    "up_btn_nt": '🌅 По: {value}',
    "up_btn_npos": '🌙 Место ночью: {value}',
    "up_btn_nint": '🌙 Интервал ночью: {value}',
    "up_btn_nl": '🌙 Лимит ночью: {value}',
    "up_btn_lots": '🛍 Лоты ({count})',
    "up_in_pos": 'Место, ниже которого лот поднимается (от {lo} до {hi}).\nСейчас: <b>{current}</b>',
    "up_in_npos": 'Место ночью, ниже которого лот поднимается (от {lo} до {hi}).\nСейчас: <b>{current}</b>',
    "up_in_chk": 'Как часто проверять места (в минутах от {lo} до {hi}).\nСейчас: <b>{current}</b>',
    "up_in_cd": 'Не поднимать один лот чаще, чем раз в N минут.\nОт {lo} до {hi}; 0 — без кулдауна.\nСейчас: <b>{current}</b>',
    "up_in_int": 'Интервал поднятия в минутах (от {lo} до {hi}).\nСейчас: <b>{current}</b>',
    "up_in_nint": 'Время ночного интервала (от {lo} до {hi}).\nСейчас: <b>{current}</b>',
    "up_in_dl": 'Лимит трат на поднятия.\nДнём, или в сутки без ночного режима ₽ (0 — без лимита).\nСейчас: <b>{current}</b>',
    "up_in_nl": 'Лимит трат на поднятия ночью (0 ₽ — без лимита).\nСейчас: <b>{current}</b>',
    "up_in_res": 'Неснижаемый остаток баланса, ₽.\nБот не поднимает лот, если после списания на балансе останется меньше этой суммы. Это не лимит трат: лимит считает, сколько потрачено на поднятия, а остаток защищает деньги на балансе — например, отложенные на вывод.\n0 — можно тратить весь баланс.\nСейчас: <b>{current}</b>',
    "up_in_nf": 'Начало ночи (ЧЧ:ММ).\nСейчас: <b>{current}</b>',
    "up_in_nt": 'Конец ночи (ЧЧ:ММ).\nСейчас: <b>{current}</b>',
    "up_err_number": 'Нужно целое число.',
    "up_err_range": 'Число должно быть от {lo} до {hi}.',
    "up_err_time": 'Время в формате ЧЧ:ММ, например 23:00.',
    "up_refreshing": '🔄 Запрашиваю места у Playerok…',
    "up_lots_title": '🛍 <b>Лоты для автоподнятия</b>',
    "up_lots_hint": 'Нажмите на лот, чтобы отметить (✅) или снять отметку (▫️). Показаны активные премиум-лоты.',
    "up_lots_empty": 'Активных премиум-лотов нет.',
    "up_lots_regular": '<i>Обычных лотов не показано: {count} — их поднять нельзя.</i>',
    "up_lots_failed": '⚠️ Список лотов не загрузился: {error}',
    "up_lot_not_premium": 'Этот лот не премиум или не в продаже — его поднять нельзя.',
    "up_offline": '⚠️ Playerok не подключён. Список лотов доступен в онлайн-режиме.',
    "menu_section_stats": "📈 Статистика",
    "menu_section_autodelivery": "📦 Авто-выдача",
    "menu_section_autoresponse": "💬 Автоответчик",
    "menu_section_blacklist": "🚫 Чёрный список",
    "menu_section_notifications": "🔔 Уведомления",
    "menu_section_plugins": "🧩 Плагины",
    "menu_section_settings": "⚙️ Настройки",
    "btn_reply_menu": "Меню",
    "module_autodelivery": "Авто-выдача",
    "module_autoraise": "Автоподнятие",
    "module_online": "Вечный онлайн",
    "module_digest": "Сводка дня",
    "module_night": 'Ночное сообщение',
    "night_btn_text": '✏️ Текст',
    "night_btn_reset": '↩️ Текст по умолчанию',
    "night_tz_server": 'пояс сервера — задайте [digest] timezone',
    "night_text_view": '🌙 <b>{title}</b>\n\n{about}\n\n<blockquote>{text}</blockquote>\n\nПришлите новый текст сообщением. {placeholders}',
    "night_texts_menu": '🌙 <b>Ночные сообщения</b>\nНочь: <b>{start}</b>–<b>{end}</b> ({tz})\n\n🛒 <b>После покупки</b> — в чат сделки, если лот оплатили ночью:\n<blockquote>{buy}</blockquote>\n\n💬 <b>Ответ на сообщение</b> — если покупатель пишет ночью (по любой сделке), не чаще раза в час на чат:\n<blockquote>{reply}</blockquote>',
    "night_btn_edit_buy": '✏️ После покупки',
    "night_btn_edit_reply": '✏️ Ответ на сообщение',
    "night_kind_buy_title": 'Ночное сообщение после покупки',
    "night_kind_buy": 'Покупатель, оплативший лот с <b>{start}</b> до <b>{end}</b> ({tz}), получит в чате сделки это сообщение (через пару секунд после товара):',
    "night_kind_reply_title": 'Ночной ответ на сообщение',
    "night_kind_reply": 'Если покупатель пишет вам с <b>{start}</b> до <b>{end}</b> ({tz}) — по старой или новой сделке, — бот ответит этим сообщением. Одному покупателю — не чаще раза в час:',
    "night_placeholders_buy": 'Можно вставить <code>$username</code> — ник покупателя и <code>$item</code> — название лота.',
    "night_placeholders_reply": 'Можно вставить <code>$username</code> — ник покупателя.',
    "night_text_saved": '✅ Текст ночного сообщения сохранён.',
    "night_text_empty": 'Пришлите текст сообщения (не пустой и не команду).',
    "night_text_too_long": 'Слишком длинно: не больше {limit} символов.',
    "module_toggled_on": "Модуль «{module}» включён.",
    "module_toggled_off": "Модуль «{module}» выключен.",

    # --- Глобальные переключатели ---
    "gl_placeholder": "⏳ Скоро",
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
        "Снять с продажи, когда склад пуст: {deactivate}"
    ),
    "ad_btn_view_stock": "👀 Показать склад",
    "ad_stock_view_title": "📦 <b>Склад «{name}»</b> — позиций: <b>{total}</b>",
    "ad_stock_view_empty": "Склад пуст.",
    "ad_stock_more": "… и ещё {count} позиций",
    "ad_btn_add_stock": "➕ Пополнить склад",
    "ad_btn_toggle_deactivate": "🛑 Снять с продажи при пустом складе: {state}",
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
    "nt_insufficient_balance": "Поднятие: баланс и лимит",
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
        '━━━━━━━━━━━━━━━━━━━\n'
        '<i>Ответ на сообщение, отвечает в чат поддержки</i>'
    ),
    "deal_confirm_offline": '⚠️ Playerok не подключён — подтвердить выдачу сейчас нельзя.',
    "deal_confirm_failed": '❌ Не удалось подтвердить выдачу: {error}',
    "deal_confirm_not_ready": '⏳ Playerok ещё не видит эту сделку. Нажмите «Подтвердить выдачу» ещё раз через минуту.',
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
    "msg_photo_one": '🖼 <i>Фото</i>',
    "msg_photo_many": '🖼 <i>Фото: {count}</i>',
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
        "⏳ <b>Лот скоро снимут с продажи</b>\n"
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
        "⬆️ <b>Лот поднят</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "📊 <b>Место:</b> {place}\n"
        "💸 <b>Списано:</b> {spent} ₽\n"
        "🧾 {budget}"
    ),
    "notif_insufficient_balance": (
        "💸 <b>Не хватает баланса на поднятие</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n"
        "💰 <b>Нужно:</b> {price} ₽\n"
        "📊 <b>Доступно:</b> {available} ₽"
    ),
    "notif_raise_limit": (
        "🛑 <b>Лимит автоподнятия исчерпан</b>\n\n"
        "🧾 {budget}\n"
        "⏳ Следующее поднятие — после {until}"
    ),
    "raise_place": "{before} → 1",
    "raise_place_unknown": "по интервалу",
    "raise_budget_limit": "Потрачено {window}: <b>{total} ₽</b> из {limit} ₽",
    "raise_budget_free": "Потрачено {window}: <b>{total} ₽</b> (без лимита)",
    "raise_window_day": "днём",
    "raise_window_night": "ночью",
    "raise_window_all": "сегодня",
    "notif_error": (
        "🚨 <b>Ошибка Fixer</b>\n\n"
        "<pre>{error}</pre>"
    ),
    "notif_stock_empty": (
        "📭 <b>Склад пуст</b>\n\n"
        "🎁 <b>Лот:</b> {item}\n\n"
        "Пополните склад, чтобы авто-выдача продолжила работать."
    ),
    "notif_stock_empty_paused": "⏸ Лот снят с продажи, чтобы его не покупали без товара. Пополните склад и верните лот в «🛍 Товарах».",
    "notif_item_expired": "⌛ <b>Лот снят: истёк срок выставления</b>\n\n📂 <b>Раздел:</b> {section}\n🎁 <b>Лот:</b> {item}\n💰 <b>Цена:</b> {price} ₽\n━━━━━━━━━━━━━━━━━━━\nВыставить заново можно кнопкой ниже — сначала покажу цену.",
    "nt_item_expired": "Лот истёк",
    "test_item_expired": "⌛ Лот истёк",
    "notif_blacklist_deal": (
        "🚫 <b>Сделка с покупателем из ЧС</b>\n\n"
        "📂 <b>Раздел:</b> {section}\n"
        "👤 <b>Покупатель:</b> {buyer}\n"
        "🎁 <b>Лот:</b> {item}\n"
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
    "lg_title": '📄 <b>Логи</b> · {level}',
    "lg_empty": 'Под эти фильтры записей нет.',
    "lg_footer": '<i>Показано {shown} из {total} · стр. {page}/{pages} · файл {size} МБ</i>',
    "lg_lvl_all": '📜 Все',
    "lg_lvl_info": 'ℹ️ Инфо',
    "lg_lvl_warn": '⚠️ Предупр.',
    "lg_lvl_err": '❌ Ошибки',
    "lg_older": '◀️ Старее',
    "lg_newer": 'Новее ▶️',
    "lg_dl_filtered": '📥 Отфильтрованное',
    "lg_dl_all": '📥 Весь файл',
    "lg_dl_failed": '❌ Файл не отправлен: {error}',
    "sys_btn_logs": "📄 Логи",
    "bk_title": '💾 <b>Бэкап конфигов</b>',
    "bk_contents": (
        'В архив входит:\n'
        '• 🎛 Глобальные переключатели и все настройки бота\n'
        '• 🤖 Автоответчик\n'
        '• 📦 Автовыдача: лоты и склады (сами позиции товара)\n'
        '• 🔔 Настройки уведомлений\n'
        '• 🔑 Аккаунт Playerok: cookies, user-agent, прокси аккаунта\n'
        '• ✈️ Токен Telegram-бота и список админов\n'
        '• 💳 Последний способ вывода\n'
        '• 🚫 Чёрный список\n'
        '• 🌙 Ночное сообщение, время сводки, часовой пояс, автоподнятие\n'
        '\n'
        'Не входит: журнал выдач, сохранённые прокси (🌐), кэши и логи.\n'
        '📥 Импорт: перед применением текущие настройки сохраняются в <code>storage/backups/</code>, '
        'затем бот перезапускается.'
    ),
    "bk_warning": '⚠️ Внутри cookies и токен бота — архив никому не пересылайте.',
    "bk_btn_import": '📥 Импорт',
    "bk_btn_export": '📤 Экспорт',
    "bk_export_caption": '💾 Бэкап конфигов Fixer.\n⚠️ Внутри cookies и токен бота — не пересылайте архив никому.',
    "bk_export_failed": '❌ Не удалось собрать архив: {error}',
    "bk_send_file": '📥 Пришлите архив бэкапа (<code>fixer-backup_….zip</code>) файлом в этот чат.',
    "bk_err": 'Архив не принят: {error}',
    "bk_err_apply": 'Не удалось применить архив: {error}',
    "bk_err_not_file": 'Нужен файл — архив бэкапа .zip.',
    "bk_applied": '✅ Бэкап от <b>{date}</b> (аккаунт <b>{account}</b>) применён.',
    "bk_stocks": '📦 Складов автовыдачи восстановлено: <b>{count}</b>',
    "bk_tg_same": '✈️ Токен бота и админы: без изменений',
    "bk_tg_changed": '✈️ Токен бота и/или админы заменены из архива',
    "bk_restarting": '🔄 Перезапускаюсь…',
    "bk_started_line": '✅ Бэкап от {date} применён',
    "sys_btn_backup": "💾 Бэкап конфигов",
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
    "test_raise_limit": "🛑 Лимит поднятия",
    "test_item_raised": "📈 Лот поднят",
    "test_no_balance": "💸 Не хватает баланса",
    "test_stock_empty": "📭 Склад пуст",
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

    # --- Связь с Playerok (playerok_link.py) ---
    "notif_playerok_unavailable": "⚠️ <b>Playerok недоступен</b>\n\nПробую подключиться снова: через 30 с, 1 мин, 2 мин, 5 мин и дальше каждые 5 мин. Сообщу, когда получится.\n\n<b>Причина:</b> <code>{reason}</code>",
    "notif_playerok_connected": "✅ <b>Успешное подключение к Playerok</b>\n\nСделки и сообщения снова отслеживаются.",
    "notif_playerok_lost": "⚠️ <b>Потеряна связь с Playerok</b>\n\nБольше 3 минут нет ответа. Переподключаюсь сам — сообщу, когда связь вернётся.",
    "notif_playerok_restored": "✅ <b>Связь с Playerok восстановлена</b>",
    "plink_btn_retry": "🔄 Повторить подключение",
    "plink_retry_started": "🔄 Пробую подключиться заново…",
    "plink_already_connected": "✅ Playerok уже подключён",
    "test_playerok_unavailable": "⚠️ Playerok недоступен",
    "test_playerok_lost": "⚠️ Потеря связи",
    "test_playerok_then": "<i>↓ Когда связь появится, сообщение станет таким:</i>",
}
