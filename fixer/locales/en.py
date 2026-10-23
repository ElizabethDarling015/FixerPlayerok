"""English locale for FixerPlayerok."""

STRINGS = {
    # --- Common / TG auth ---
    "unauthorized": "⛔ You are not authorized. Send the secret code from the Fixer console to bind yourself as an admin.",
    "auth_success": "✅ You are now a FixerPlayerok administrator.",
    "auth_wrong_code": "❌ Wrong code. The current code is printed in the Fixer console.",
    "btn_back": "◀️ Back",
    "btn_home": "🏠 Main menu",
    "btn_chats": "💬 Buyer chats",
    "chats_empty": "No active chats.",
    "chats_view_title": "💬 <b>Chat with {username}</b>\n\n",
    "chats_btn_reply": "✏️ Reply to chat",
    "chats_reply_sent": "✅ Message successfully sent to the buyer!",
    "chats_title": "💬 <b>Buyer chats</b>\n\nChat list (refreshed on tap):",
    "chats_btn_prev_page": "⬅️ Prev",
    "chats_btn_next_page": "➡️ Next",
    "chats_btn_older": "⬆️ Older",
    "chats_btn_newer": "⬇️ Newer",
    "chats_btn_read": "✅ Mark read",
    "chats_btn_refresh": "🔄 Refresh",
    "chats_btn_cancel": "✖️ End dialog",
    "chats_enter_text": "✏️ Live dialog with <b>{username}</b>.\nType a message or send a photo — it goes to the buyer's chat.\nAny button exits the mode.",
    "chats_read_done": "✅ Chat marked as read.",
    "chats_read_failed": "⚠️ Failed to mark chat as read, see log.",
    "chats_read_slow": "⚠️ Playerok did not respond in time ({seconds} s), waiting…",
    "chats_read_late_ok": "✅ Responded, took {seconds} s.",
    "chats_read_late_failed": "❌ Failed to mark chat as read (after {seconds} s), see log.",
    "btn_items": "🛍 Items",
    "it_title": "🛍 <b>Items</b>\nOn sale: <b>{on_sale}</b> · In moderation: <b>{moderation}</b>\n\nChoose a section:",
    "it_empty": "No active items.",
    "it_btn_inactive": "⏸ Paused and blocked",
    "it_btn_refresh": "🔄 Refresh",
    "it_section_title": "📂 <b>{section}</b> — items: <b>{count}</b>\n\n🔁 — auto-relist is on",
    "it_inactive_title": "⏸ <b>Paused and blocked</b>\n⏸ Paused by you: <b>{discontinued}</b>\n⛔ Blocked: <b>{blocked}</b>\n🔴 Declined: <b>{declined}</b>\n🟠 Expired: <b>{expired}</b>",
    "it_inactive_empty": "No such items.",
    "it_card_title": "🎁 <b>{name}</b>",
    "it_card_section": "📂 {section}",
    "it_card_price": "💰 <b>{price} ₽</b> · {status} · {priority}",
    "it_card_until": "🗓 On sale until {until}",
    "it_card_stats": "👁 Views: {views} · 🛒 Sales: {deals}",
    "it_card_reason": "⚠️ <b>Reason:</b> {reason}",
    "it_card_comment": "💬 <b>Comment:</b>\n<blockquote expandable>{comment}</blockquote>",
    "it_card_no_comment": "💬 No comment",
    "it_card_keep": "🔁 Auto-relist: {state}",
    "it_card_autodelivery": "📦 Auto-delivery: {state}",
    "it_autodelivery_on": "on, {stock} in stock",
    "it_on": "on",
    "it_off": "off",
    "it_premium": "🚀 Premium",
    "it_free": "Regular",
    "it_status_approved": "On sale",
    "it_status_pending_moderation": "In moderation",
    "it_status_pending_approval": "Awaiting review",
    "it_status_expired": "Expired",
    "it_status_declined": "Declined",
    "it_status_blocked": "Blocked",
    "it_status_discontinued": "Paused",
    "it_status_sold": "Sold",
    "it_status_draft": "Draft",
    "it_btn_keep": "🔁 Auto-relist: {state}",
    "it_btn_comment": "💬 Comment",
    "it_btn_price": "💰 Price",
    "it_btn_raise": "⬆️ Raise",
    "it_btn_pause": "⏸ Pause",
    "it_btn_resume": "▶️ Resume",
    "it_btn_publish": "🔄 Relist",
    "it_btn_site": "🌐 Open on site",
    "it_btn_pay": "✅ {label} · {price} ₽",
    "it_raise_confirm": "⬆️ <b>Raise to top</b>\n🎁 {name}\n\nPaid from the Playerok balance. The 30-day listing period restarts.",
    "it_publish_confirm": "🔄 <b>Relist</b>\n🎁 {name}\n\nChoose a status. A paid one is charged to the Playerok balance.",
    "it_no_statuses": "Playerok offered no options — try on the site.",
    "it_pending_expired": "The payment screen is outdated — open the item again.",
    "it_raised": "✅ Item raised, {price} ₽ charged.",
    "it_published": "✅ Item relisted, {price} ₽ charged.",
    "it_keep_on": "🔁 Auto-relist on",
    "it_keep_off": "🔁 Auto-relist off",
    "it_keep_unknown": "Playerok did not report whether auto-relist is on for this item — nothing changed. Open it on the site.",
    "it_keep_sent": "Request sent, but Playerok did not confirm the new state — check on the site.",
    "it_keep_not_changed": "Playerok did not change auto-relist — check the item on the site.",
    "it_paused": "⏸ Item paused",
    "it_resumed": "▶️ Item is on sale again",
    "it_enter_comment": "💬 Send the new <b>comment</b> — the buyer gets it after paying.\n\nAfter a comment change the item briefly goes to moderation.",
    "it_enter_price": "💰 Send the new <b>price</b> in rubles (number only).",
    "it_bad_price": "Send the price as a number, e.g. 330.",
    "it_bad_comment": "Send the comment text (not empty and not a command).",
    "it_comment_saved": "✅ Comment saved. The item briefly went to moderation.",
    "it_price_saved": "✅ Price changed: {price} ₽.",
    "it_offline": "⚠️ Playerok is not connected — «Items» works online only.",
    "it_forbidden": "❌ Playerok does not allow this for an item in this status.",
    "it_failed": "❌ Failed: {error}",
    "it_load_failed": "🛍 <b>Items</b>\n\n❌ Could not load items: {error}",
    "it_not_found": "Item not found — it may have been deleted.",
    "btn_last_deals": "🕒 Recent deals",
    "wd_offline": (
        '⚠️ Playerok is not connected.\n'
        'Withdrawals are available in online mode.'
    ),
    "wd_failed": '❌ Failed: {error}',
    "wd_status_confirmed": '✅ Paid out',
    "wd_status_processing": '🔄 Processing',
    "wd_status_pending": '⏳ Queued',
    "wd_status_rolled_back": '↩️ Returned',
    "wd_status_failed": '❌ Failed',
    "wd_history_entry": (
        '💸 <b>-{amount}</b> · {method}\n'
        '🕒 {date} · {status}'
    ),
    "wd_done": (
        '✅ <b>Withdrawal request created</b>\n'
        '\n'
        '💸 Amount: <b>{amount}</b>\n'
        '📍 To: {destination}\n'
        '📋 Status: {status}\n'
        '🆔 <code>{tx_id}</code>\n'
        '\n'
        "When Playerok pays it out you'll get a «Payout» notification."
    ),
    "wd_sending": '⏳ Creating the withdrawal request…',
    "wd_btn_go": '✅ Withdraw',
    "wd_confirm": (
        '💳 <b>Confirm withdrawal</b>\n'
        '\n'
        '💸 Amount: <b>{amount}</b>\n'
        '📍 To: {destination}\n'
        '🧾 Playerok fee ≈ {fee} ({fee_rule})\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '⚠️ After you tap «Withdraw» the request goes to Playerok.'
    ),
    "wd_usdt_estimate": '🪙 ≈ {usdt} USDT at {rate} ₽ (before fees)',
    "wd_err_provider_gone": 'This withdrawal method is not available on Playerok right now.',
    "wd_err_expired": 'Withdrawal data expired — start again: «💳 Withdraw».',
    "wd_err_balance": 'More than available to withdraw ({available}).',
    "wd_err_max": 'Above the maximum for this method ({max}).',
    "wd_err_min": 'Below the minimum for this method ({min}).',
    "wd_err_amount": 'Type a whole number of rubles, e.g. <code>2000</code>',
    "wd_btn_cancel": '✖️ Cancel',
    "wd_btn_all": 'Everything — {amount}',
    "wd_amount_prompt": (
        '💳 <b>Withdraw</b> → {destination}\n'
        '\n'
        '💰 Available: <b>{available}</b>\n'
        '📏 Method limits: {min} – {max}\n'
        '\n'
        'Type an amount in rubles or tap the button:'
    ),
    "wd_err_usdt": "That doesn't look like a TRC20 address: it starts with <code>T</code> and has 34 characters.",
    "wd_enter_usdt": (
        '🪙 Type a <b>USDT (TRC20)</b> wallet address — starts with <code>T</code>, 34 characters.\n'
        '\n'
        '⚠️ A transfer to a wrong address cannot be returned — double-check it.'
    ),
    "wd_no_cards": (
        '💳 No cards are linked on Playerok.\n'
        'Link a card in the website wallet and come back.'
    ),
    "wd_choose_card": (
        '💳 <b>Card</b>\n'
        '\n'
        'Pick a card linked on Playerok:'
    ),
    "wd_err_phone": "That doesn't look like a Russian phone number. Example: <code>+79001234567</code>",
    "wd_enter_phone": (
        '📱 No SBP phone number is saved on the website.\n'
        'Type the phone number linked to the bank (e.g. <code>+79001234567</code>):'
    ),
    "wd_err_bank_not_found": 'Bank not found — try another name.',
    "wd_enter_bank": '🔍 Type part of the bank name:',
    "wd_choose_bank": (
        '🏦 <b>Recipient bank (SBP)</b>\n'
        '\n'
        'Pick a bank or search by name:'
    ),
    "wd_btn_bank_search": '🔍 Find another bank',
    "wd_btn_repeat": '⚡ Same as last time: {label}',
    "wd_site_only": '<i>website only</i>',
    "wd_methods_header": '<b>Methods</b> (fee · limits):',
    "wd_available": '💰 Available to withdraw: <b>{amount}</b>',
    "wd_title": '💳 <b>Withdraw funds</b>',
    "btn_withdraw": '💳 Withdraw',
    "ld_failed": '⚠️ Could not load deals: {error}',
    "ld_offline": (
        '⚠️ Playerok is not connected.\n'
        'Recent deals are available in online mode.'
    ),
    "ld_btn_refresh": '🔄 Refresh',
    "ld_page": '<i>📄 Page {page}</i>',
    "ld_empty": 'No sales yet.',
    "ld_entry": (
        '📂 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}\n'
        '👤 <b>Buyer:</b> {buyer} | 💰 <b>Price:</b> {price}\n'
        '{state}{date}'
    ),
    "ld_date": '\n🗓 {date}',
    "ld_title": '🕒 <b>Recent deals</b>',
    "ld_review": ' · ⭐ {rating}',
    "ld_state_unknown": '❔ {status}',
    "ld_state_problem": '⚠️ Problem in the deal',
    "ld_state_rolled_back": '↩️ Refunded',
    "ld_state_auto": '✅ Completed automatically',
    "ld_state_confirmed": '✅ Completed',
    "ld_state_sent": '⏳ Not confirmed yet',
    "ld_state_paid": '💰 Paid, waiting for delivery',
    "btn_deals_in_work": '⏳ Deals in progress',
    "dw_btn_count": '⏳ Deals in progress ({count})',
    "dw_title": '⏳ <b>Deals in progress: {count}</b>',
    "dw_empty": 'Everything is confirmed, no disputes.',
    "dw_syncing": '<i>Syncing with Playerok — press «🔄 Refresh» in a couple of seconds.</i>',
    "dw_entry": (
        '{n}. <b>{item}</b>\n'
        '📂 {section}\n'
        '👤 {buyer} · 💰 {price}\n'
        '🕒 {date}{problem}'
    ),
    "dw_problem": ' · ⚠️ Dispute',
    "dw_offline": '⚠️ Playerok is not connected. «Deals in progress» works in online mode.',
    "dw_card_title": '⏳ <b>Deal in progress</b>',
    "dw_card_done_title": '✅ <b>Delivery confirmed</b>',
    "dw_card": (
        '🎁 <b>Item:</b> {item}\n'
        '📂 <b>Section:</b> {section}\n'
        '👤 <b>Buyer:</b> {buyer} | 💰 <b>Price:</b> {price}\n'
        '🕒 <b>Paid:</b> {date}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "dw_card_problem": '⚠️ <b>Dispute opened</b>',
    "dw_card_sent": '✅ Delivery confirmed, waiting for the dispute to be resolved',
    "dw_btn_confirmed": '✅ Delivery confirmed',
    "dw_btn_give": '📦 Deliver from stock',
    "dw_btn_given": '📦 Delivered',
    "dw_gone": 'This deal is no longer in progress.',
    "dw_already_sent": 'Delivery for this deal is already confirmed — waiting for the dispute to be resolved.',
    "dw_give_ok": '📦 The item was sent to the buyer in the deal chat.',
    "dw_give_none": '📦 Auto-delivery is not set up for this item.',
    "dw_give_empty": '📦 This item\'s stock is empty.',
    "dw_give_given": '📦 The item for this deal has already been delivered.',
    "dw_give_no_chat": '⚠️ Could not find the deal chat.',
    "dw_give_failed": '❌ The item was not sent: {error}\nIt was returned to stock.',
    "btn_close": "❌ Close",
    "cancelled": "Action cancelled.",
    "stub_message": "⏸ Section has been moved to Settings",
    "btn_cancel": "Cancel",

    # --- Main menu ---
    "menu_title": (
        "🐦 <b>FixerPlayerok</b>\n\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "📩 New messages: <b>{unread_messages}</b>\n"
        "⏱ Uptime: <b>{uptime}</b>"
    ),
    "menu_section_toggles": "🎛 Global toggles",
    "menu_section_profile": "👤 Profile",
    "pf_title": '👤 <b>Profile</b>',
    "pf_name": '👤 <b>{username}</b>',
    "pf_id": '🆔 <code>{id}</code>',
    "pf_email": '📪 {email}',
    "pf_rating": '⭐ Rating: <b>{rating}</b> · 💬 Reviews: <b>{reviews}</b>',
    "pf_verified_yes": '✅ Verified',
    "pf_verified_no": '☑️ Not verified',
    "pf_blocked": '⛔ <b>Account is blocked</b>',
    "pf_blocked_until": '⛔ <b>Blocked until {until}</b>',
    "pf_created": '🗓 On Playerok since {date}',
    "pf_balance": '💰 Balance: <b>{value}</b>',
    "pf_available": '・ 👜 Available: {value}',
    "pf_withdrawable": '・ 💸 Withdrawable: {value}',
    "pf_pending": '・ ⌛ Processing: {value}',
    "pf_frozen": '・ ❄️ Frozen: {value}',
    "pf_items": '📦 Items: on sale <b>{active}</b> · removed and expired <b>{inactive}</b>',
    "pf_sales": '🛒 Sales: <b>{total}</b> · ✅ completed {done} · ⏳ in progress {active} · ↩️ refunds {refund}',
    "pf_purchases": '🛍 Purchases: <b>{total}</b>',
    "pf_failed": '⚠️ Could not load the profile: {error}',
    "pf_offline": '⚠️ Playerok is not connected. The profile works in online mode.',
    "menu_section_autoraise": "⬆️ Auto-raise",
    "up_title": '⬆️ <b>Auto-raise</b> {status} · {time}',
    "up_title_short": '⬆️ <b>Auto-raise</b>',
    "up_on": '🟢 On',
    "up_off": '🔴 Off',
    "up_day": '☀️ Day',
    "up_night": '🌙 Night',
    "up_allday": '🕒 24 h',
    "up_mode_position_line": '📊 Mode: by position — keep in top-<b>{position}</b>',
    "up_check_line": '⏱️ Check: every {check}',
    "up_cooldown_line": '🕒 Cooldown: {cooldown}',
    "up_streak_line": '🔁 Checks in a row: {streak}',
    "up_limit_value": 'Limit {limit}',
    "up_no_limit_cap": 'No limit',
    "up_mode_interval_line": '⏰ Mode: by interval — every <b>{interval}</b>',
    "up_next_run": '⏭ Next raise: {time}',
    "up_night_pos": 'top-{position}',
    "up_night_int": 'every {interval}',
    "up_night_line": '🌙 Night {start}–{end}: {value} | {limit}',
    "up_spent_line": '💸 Spent {window}: <b>{spent}</b> | {limit}',
    "up_reserve_line": '💰 Minimum balance: {reserve}',
    "up_no_limit": 'no limit',
    "up_no_items": 'No items selected — press «🛍 Items».',
    "up_positions_head": '📊 <b>Positions</b>',
    "up_checked_at": '(checked at {time})',
    "up_items_head": '🛍 <b>Selected items</b>',
    "up_item_ok": 'place {pos} ✅',
    "up_item_low": 'place {pos} ⬆️ ({streak} of {need})',
    "up_item_unchecked": 'not checked yet',
    "up_item_waiting": 'waiting for the interval',
    "up_item_not_premium": '⚠️ not premium — cannot be raised',
    "up_item_not_active": '⚠️ not on sale',
    "up_item_not_found": '⚠️ item not found',
    "up_item_error": '⚠️ check failed',
    "up_hint": '<i>Only selected premium items are raised. The raise price depends on the item price (9–75 ₽).</i>',
    "up_btn_on": '🟢 On',
    "up_btn_off": '🔴 Off',
    "up_btn_mode_position": '📊 Mode: by position',
    "up_btn_mode_interval": '⏰ Mode: by interval',
    "up_btn_pos": '📊 Place: {value}',
    "up_btn_chk": '⏱ Check: {value}',
    "up_btn_cd": '🕒 Cooldown: {value}',
    "up_btn_streak": '🔁 In a row: {value}',
    "up_btn_int": '⏰ Interval: {value}',
    "up_btn_dl": '☀️ Day limit: {value}',
    "up_btn_dl_all": '💸 Daily limit: {value}',
    "up_btn_res": '💰 Keep: {value}',
    "up_btn_night_on": '🌙 Night mode: on',
    "up_btn_night_off": '🌙 Night mode: off',
    "up_btn_nf": '🌙 From: {value}',
    "up_btn_nt": '🌅 To: {value}',
    "up_btn_npos": '🌙 Night place: {value}',
    "up_btn_nint": '🌙 Night interval: {value}',
    "up_btn_nl": '🌙 Night limit: {value}',
    "up_btn_lots": '🛍 Items ({count})',
    "up_in_pos": 'Place below which an item is raised ({lo} to {hi}).\nNow: <b>{current}</b>',
    "up_in_npos": 'Night place below which an item is raised ({lo} to {hi}).\nNow: <b>{current}</b>',
    "up_in_chk": 'How often to check places (minutes, {lo} to {hi}).\nNow: <b>{current}</b>',
    "up_in_cd": 'Do not raise one item more often than every N minutes.\n{lo} to {hi}; 0 — no cooldown.\nNow: <b>{current}</b>',
    "up_in_int": 'Raise interval in minutes ({lo} to {hi}).\nNow: <b>{current}</b>',
    "up_in_nint": 'Night interval ({lo} to {hi}).\nNow: <b>{current}</b>',
    "up_in_dl": 'Spending limit for raises.\nDay, or per 24 h without night mode, ₽ (0 — no limit).\nNow: <b>{current}</b>',
    "up_in_nl": 'Night spending limit for raises (0 ₽ — no limit).\nNow: <b>{current}</b>',
    "up_in_res": 'Minimum balance, ₽.\nThe bot does not raise an item if less than this amount would remain on the balance after paying. This is not a spending limit: the limit counts what was spent on raises, the minimum protects the money on the balance — e.g. set aside for a withdrawal.\n0 — the whole balance may be spent.\nNow: <b>{current}</b>',
    "up_in_nf": 'Night start (HH:MM).\nNow: <b>{current}</b>',
    "up_in_nt": 'Night end (HH:MM).\nNow: <b>{current}</b>',
    "up_err_number": 'A whole number is needed.',
    "up_err_range": 'The number must be from {lo} to {hi}.',
    "up_err_time": 'Time as HH:MM, e.g. 23:00.',
    "up_refreshing": '🔄 Asking Playerok for places…',
    "up_lots_title": '🛍 <b>Items for auto-raise</b>',
    "up_lots_hint": 'Tap an item to select (✅) or unselect (▫️). Active premium items are shown.',
    "up_lots_empty": 'No active premium items.',
    "up_lots_regular": '<i>Regular items not shown: {count} — they cannot be raised.</i>',
    "up_lots_failed": '⚠️ Items did not load: {error}',
    "up_lot_not_premium": 'This item is not premium or not on sale — it cannot be raised.',
    "up_offline": '⚠️ Playerok is not connected. The item list works in online mode.',
    "menu_section_stats": "📈 Statistics",
    "menu_section_autodelivery": "📦 Auto-delivery",
    "menu_section_autoresponse": "💬 Auto-response",
    "menu_section_blacklist": "🚫 Blacklist",
    "menu_section_notifications": "🔔 Notifications",
    "menu_section_plugins": "🧩 Plugins",
    "menu_section_settings": "⚙️ Settings",
    "btn_reply_menu": "Menu",
    "menu_keyboard_hint": "📋 The “Menu” button is under the input field. Tap the arrow to collapse it into a compact button.",
    "module_autodelivery": "Auto-delivery",
    "module_autoraise": "Auto-raise",
    "module_autoresponse": "Auto-response",
    "module_online": "Always online",
    "module_digest": "Daily digest",
    "module_night": 'Night message',
    "night_btn_text": '✏️ Text',
    "night_btn_reset": '↩️ Default text',
    "night_tz_server": 'server time zone — set [digest] timezone',
    "night_text_view": '🌙 <b>{title}</b>\n\n{about}\n\n<blockquote>{text}</blockquote>\n\nSend the new text as a message. {placeholders}',
    "night_texts_menu": '🌙 <b>Night messages</b>\nNight: <b>{start}</b>–<b>{end}</b> ({tz})\n\n🛒 <b>After a purchase</b> — to the deal chat if the item was paid at night:\n<blockquote>{buy}</blockquote>\n\n💬 <b>Reply to a message</b> — if a buyer writes at night (about any deal), at most once an hour per chat:\n<blockquote>{reply}</blockquote>',
    "night_btn_edit_buy": '✏️ After a purchase',
    "night_btn_edit_reply": '✏️ Reply to a message',
    "night_kind_buy_title": 'Night message after a purchase',
    "night_kind_buy": 'A buyer who pays from <b>{start}</b> to <b>{end}</b> ({tz}) gets this message in the deal chat (a few seconds after the item):',
    "night_kind_reply_title": 'Night reply to a message',
    "night_kind_reply": 'If a buyer writes to you from <b>{start}</b> to <b>{end}</b> ({tz}) — about an old or a new deal — the bot replies with this message. At most once an hour per buyer:',
    "night_placeholders_buy": 'You can use <code>$username</code> — buyer nickname and <code>$item</code> — item name.',
    "night_placeholders_reply": 'You can use <code>$username</code> — buyer nickname.',
    "night_text_saved": '✅ Night message text saved.',
    "night_text_empty": 'Send the message text (not empty and not a command).',
    "night_text_too_long": 'Too long: {limit} characters max.',
    "module_toggled_on": "Module \"{module}\" enabled.",
    "module_toggled_off": "Module \"{module}\" disabled.",

    # --- Global toggles ---
    "gl_title": "🎛 <b>Global toggles</b>\n\nTap a module to enable or disable it:",

    # --- Statistics ---
    "st_title": (
        '📈 <b>Sales statistics</b>\n'
        '<i>from Playerok, last 7 days</i>\n'
    ),
    "digest_stocks_block": (
        '\n'
        '\n'
        '📦 Auto-delivery stock:\n'
        '{stocks}'
    ),
    "st_offline": (
        '⚠️ Playerok is not connected.\n'
        'Statistics and the digest are available in online mode.'
    ),
    "st_failed": '⚠️ Could not load sales history from Playerok: {error}',
    "st_refunds_month": '↩️ Refunds in 30 days: <b>{refunds}</b>',
    "st_line_refunds": ' · ↩️ {refunds}',
    "st_line": '• {day}: <b>{count}</b> pcs · {gross} (net {net})',
    "st_empty": 'No sales in the last 7 days.',
    "st_total_week": '7 days: <b>{count}</b> pcs · <b>{gross}</b> (net {net})',
    "st_total_month": '30 days: <b>{count}</b> pcs · <b>{gross}</b> (net {net})',

    # --- Auto-delivery ---
    "ad_title": "📦 <b>Auto-delivery</b>\n\nLots and stock:",
    "ad_no_lots": "No lots configured yet.",
    "ad_lot_line": "• {name} — <b>{stock}</b> pcs.",
    "ad_btn_add_lot": "➕ Add lot",
    "ad_lot_title": (
        "📦 Lot <b>{name}</b>\n"
        "Stock file: <code>{stock_file}</code>\n"
        "In stock: <b>{stock}</b> pcs.\n"
        "Take off sale when stock is empty: {deactivate}"
    ),
    "ad_btn_view_stock": "👀 View stock",
    "ad_stock_view_title": "📦 <b>Stock \"{name}\"</b> — items: <b>{total}</b>",
    "ad_stock_view_empty": "The stock is empty.",
    "ad_stock_more": "… and {count} more items",
    "ad_btn_add_stock": "➕ Add stock",
    "ad_btn_toggle_deactivate": "🛑 Off sale when empty: {state}",
    "ad_btn_delete_lot": "🗑 Delete lot",
    "ad_enter_lot_name": "Send the <b>exact lot name</b> (as on Playerok):",
    "ad_enter_stock_file": "Send the stock file path (e.g. <code>storage/stock/my_lot.txt</code>) or \"-\" to create one automatically:",
    "ad_lot_added": "✅ Lot \"{name}\" added. Stock file: <code>{stock_file}</code>",
    "ad_lot_deleted": "🗑 Lot \"{name}\" removed from auto-delivery (the stock file is kept).",
    "ad_send_stock_items": (
        "Send the goods: as text or as a <code>.txt</code> file.\n"
        "One line — one item. For multi-line items (login+password+instructions) "
        "separate them with a <code>---</code> line."
    ),
    "ad_stock_added": "✅ Items added: <b>{count}</b>. Now in stock: <b>{stock}</b>.",
    "ad_lot_missing": "Lot not found (config may have changed). Re-open the section.",

    # --- Auto-response ---
    "ar_title": "💬 <b>Auto-response</b>\n\nCommands:",
    "ar_no_commands": "No commands yet.",
    "ar_btn_add": "➕ Add command",
    "ar_command_view": "Command: <code>{command}</code>\n\nResponse:\n{response}",
    "ar_btn_delete": "🗑 Delete",
    "ar_btn_edit": "✏️ Edit response",
    "ar_enter_new_response": "Send the new response text for command <code>{command}</code>.",
    "ar_edited": "✅ Response for <code>{command}</code> updated.",
    "ar_enter_command": "Send the command (e.g. <code>!hello</code>):",
    "ar_enter_response": "Send the response text. Variables: <code>$username</code>, <code>$chat_id</code>, <code>$date</code>, <code>$time</code>.",
    "ar_added": "✅ Command <code>{command}</code> added.",
    "ar_deleted": "🗑 Command <code>{command}</code> deleted.",
    "ar_missing": "Command not found (config may have changed). Re-open the section.",
    "ar_builtin_commands_response": "Available commands:\n{commands}",

    # --- Blacklist ---
    "bl_title": (
        '🚫 <b>Blacklist</b>\n'
        '\n'
        "Purchases by these buyers trigger a warning. After their first deal the bot remembers the buyer's ID, so changing the username won't help.\n"
        'Tap a username to remove it:'
    ),
    "bl_empty": "The blacklist is empty.",
    "bl_btn_add": "➕ Add username",
    "bl_enter_username": "Send the Playerok buyer username (case-insensitive):",
    "bl_added": "🚫 <code>{username}</code> added to the blacklist.",
    "bl_already": "<code>{username}</code> is already blacklisted.",
    "bl_removed": "✅ {username} removed from the blacklist.",
    "bl_missing": "Username not found (the list may have changed). Re-open the section.",

    # --- Daily digest ---
    "digest_text": (
        '📊 <b>Digest for {date}</b>\n'
        '\n'
        '🛒 Sales: <b>{sales}</b>\n'
        '💰 Revenue: <b>{revenue}</b> (net {net})\n'
        '↩️ Refunds: <b>{refunds}</b>\n'
        '💳 Balance: <b>{balance}</b>\n'
        '⏱ Uptime: <b>{uptime}</b>{stocks}'
    ),
    "digest_stock_line": "• {name} — <b>{stock}</b> pcs.",
    "digest_unavailable": "The digest module is unavailable.",

    # --- Notifications ---
    "nt_title": "🔔 <b>Notifications</b>\n\nTap to toggle:",
    "nt_new_deal": "New deal",
    "nt_delivery": "Delivery",
    "nt_new_message": "New messages",
    "nt_new_review": "New reviews",
    "nt_deal_problem": "Deal problems",
    "nt_deal_confirmed": "Deal confirmations",
    "nt_deal_rolled_back": "Deal rollbacks",
    "nt_item_raised": "Item raised",
    "nt_insufficient_balance": "Raise: balance and limit",
    "nt_errors": "Errors",
    "nt_stock_empty": "Empty stock",
    "nt_blacklist": "Blacklist deals",

    # --- Notification texts ---
    "notif_started": (
        "🐦 <b>FixerPlayerok started</b>\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "🌙 Missed deals: <b>{missed_deals}</b>\n"
        "📩 New messages: <b>{unread_messages}</b>\n"
        "🧩 Modules: {modules}"
    ),
    "notif_new_deal": (
        '🛒 <b>New deal</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}\n'
        '👤 <b>Buyer:</b> {buyer}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '💰 <b>Price:</b> {price} ₽{autodelivery}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "menu_closed": '✖️ Menu closed.',
    "payout_line_balance": '💰 <b>Balance:</b> {balance} ₽',
    "payout_line_date": '🕒 <b>Date:</b> {date}',
    "payout_line_status": '📋 <b>Status:</b> {status}',
    "payout_line_method": '🏦 <b>Method:</b> {method}',
    "payout_line_amount": '💸 <b>Amount:</b> <code>-{amount} ₽</code>',
    "notif_system_lot": (
        '\n'
        '\n'
        '🎁 <b>Item:</b> {lot}'
    ),
    "notif_system_message": (
        '📢 <b>Playerok notice</b>\n'
        '\n'
        '💬 {text}{lot}'
    ),
    "notif_place_deal_chat": '🛒 Chat with buyer {buyer}',
    "notif_staff_finished": (
        '✅ <b>Chat finished</b>\n'
        '{place}\n'
        '👤 {staff}'
    ),
    "notif_staff_started": (
        '👀 <b>Looking at the chat…</b>\n'
        '{place}\n'
        '👤 {staff}'
    ),
    "notif_support_in_deal_chat": (
        '🛟 <b>Support in a deal</b>\n'
        '👤 {staff}\n'
        '\n'
        '🛒 <b>Buyer:</b> {buyer}\n'
        '🎁 <b>Item:</b> {item}\n'
        '\n'
        '💬 {text}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '<i>Reply to this message to answer in the deal chat</i>'
    ),
    "notif_support_message": (
        '🛟 <b>Playerok support</b>\n'
        '👤 {staff}\n'
        '\n'
        '💬 {text}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '<i>Reply to this message to answer support</i>'
    ),
    "deal_confirm_offline": '⚠️ Playerok is not connected — delivery cannot be confirmed now.',
    "deal_confirm_failed": '❌ Could not confirm delivery: {error}',
    "deal_confirm_not_ready": "⏳ Playerok doesn't see this deal yet. Press «Confirm delivery» again in a minute.",
    "deal_confirm_test": '✅ Delivery confirmed (test notification — nothing was sent to Playerok).',
    "deal_confirm_ok": '✅ Delivery confirmed.',
    "deal_btn_collapse": '➖ Collapse',
    "deal_btn_confirm": '✅ Confirm delivery',
    "notif_new_deal_short": (
        '🛒 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}\n'
        '👤 <b>Bought by:</b> {buyer}\n'
        '💰 <b>Price:</b> {price}\n'
        '🆔 <code>{chat_id}</code>'
    ),
    "notif_new_deal_autodelivery": (
        '\n'
        '🤖 <i>Auto-delivery is active</i>'
    ),
    "notif_delivery_ok": (
        '📦 <b>Item delivered</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}\n'
        '📊 <b>Left in stock:</b> {stock} pcs.'
    ),
    "msg_photo_one": '🖼 <i>Photo</i>',
    "msg_photo_many": '🖼 <i>Photos: {count}</i>',
    "notif_new_message": (
        '💌 <b>Message from {username}!</b>\n'
        '💬:{text}\n'
        '\n'
        '🎁 <b>Item:</b> {item}'
    ),
    "notif_payout": (
        '💳 <b>Payout</b>\n'
        '\n'
        '{details}━━━━━━━━━━━━━━━━━━━\n'
        '💬 {text}'
    ),
    "notif_item_expiring": (
        "⏳ <b>Item will be delisted soon</b>\n\n"
        "🎁 <b>Item:</b> {item}\n"
        "📂 <b>Section:</b> {section}\n"
        "💰 <b>Price:</b> {price}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}"
    ),
    "notif_item_expiring_plain": (
        "⏳ <b>Item will be delisted soon</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}"
    ),
    "notif_new_review": (
        '⭐ <b>New review</b>\n'
        '\n'
        '👤 <b>Author:</b> {author}\n'
        '⭐ <b>Rating:</b> {rating}/5\n'
        '\n'
        '💬 {text}'
    ),
    "notif_deal_problem": (
        '⚠️ <b>Deal problem</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '🆔 <b>Deal ID:</b> <code>{deal_id}</code>'
    ),
    "notif_deal_problem_resolved": (
        '✅ <b>Problem resolved</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '🆔 <b>Deal ID:</b> <code>{deal_id}</code>'
    ),
    "notif_deal_confirmed": (
        "🤝 <b>Deal confirmed</b>\n\n"
        "📂 <b>Section:</b> {section}\n"
        "🎁 <b>Item:</b> {item}\n"
        "👤 <b>Buyer:</b> {buyer}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Price:</b> {price} ₽\n"
        "🆔 <code>{chat_id}</code>"
    ),
    "notif_deal_rolled_back": (
        '↩️ <b>Deal refunded</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '🎁 <b>Item:</b> {item}'
    ),
    "notif_item_raised": (
        "⬆️ <b>Item raised</b>\n\n"
        "🎁 <b>Item:</b> {item}\n"
        "📊 <b>Place:</b> {place}\n"
        "💸 <b>Charged:</b> {spent} ₽\n"
        "🧾 {budget}"
    ),
    "notif_insufficient_balance": (
        "💸 <b>Not enough balance to raise</b>\n\n"
        "🎁 <b>Item:</b> {item}\n"
        "💰 <b>Needed:</b> {price} ₽\n"
        "📊 <b>Available:</b> {available} ₽"
    ),
    "notif_raise_limit": (
        "🛑 <b>Auto-raise limit reached</b>\n\n"
        "🧾 {budget}\n"
        "⏳ Next raise — after {until}"
    ),
    "raise_place": "{before} → 1",
    "raise_place_unknown": "by interval",
    "raise_budget_limit": "Spent {window}: <b>{total} ₽</b> of {limit} ₽",
    "raise_budget_free": "Spent {window}: <b>{total} ₽</b> (no limit)",
    "raise_window_day": "during the day",
    "raise_window_night": "at night",
    "raise_window_all": "today",
    "notif_error": (
        '🚨 <b>Fixer error</b>\n'
        '\n'
        '<pre>{error}</pre>'
    ),
    "notif_stock_empty": (
        '📭 <b>Stock is empty</b>\n'
        '\n'
        '🎁 <b>Item:</b> {item}\n'
        '\n'
        'Refill the stock so auto-delivery keeps working.'
    ),
    "notif_stock_empty_paused": "⏸ The item was paused so nobody buys it without stock. Restock and resume it in «🛍 Items».",
    "notif_item_expired": "⌛ <b>Item delisted: listing period ended</b>\n\n📂 <b>Section:</b> {section}\n🎁 <b>Item:</b> {item}\n💰 <b>Price:</b> {price} ₽\n━━━━━━━━━━━━━━━━━━━\nRelist with the button below — I'll show the price first.",
    "nt_item_expired": "Item expired",
    "test_item_expired": "⌛ Item expired",
    "notif_blacklist_deal": (
        '🚫 <b>Deal with a blacklisted buyer</b>\n'
        '\n'
        '📂 <b>Section:</b> {section}\n'
        '👤 <b>Buyer:</b> {buyer}\n'
        '🎁 <b>Item:</b> {item}\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        '⚠️ Check the deal manually'
    ),
    "reply_sent": "✅ Sent to the Playerok chat.",
    "reply_failed": "❌ Failed to send: {error}",
    "reply_unknown": "Not sure where to send this: reply to a message notification.",
    "reply_offline": "🤬 No connection to Playerok — message not sent.",
    "reply_refused": "🤷 Playerok did not accept the message. Check the log: Settings → 📄 Logs.",

    # --- Settings ---
    "settings_title": "⚙️ <b>Settings</b>",
    "lg_title": '📄 <b>Logs</b> · {level}',
    "lg_empty": 'No records match these filters.',
    "lg_footer": '<i>Shown {shown} of {total} · page {page}/{pages} · file {size} MB</i>',
    "lg_lvl_all": '📜 All',
    "lg_lvl_info": 'ℹ️ Info',
    "lg_lvl_warn": '⚠️ Warnings',
    "lg_lvl_err": '❌ Errors',
    "lg_older": '◀️ Older',
    "lg_newer": 'Newer ▶️',
    "lg_dl_filtered": '📥 Filtered',
    "lg_dl_all": '📥 Whole file',
    "lg_dl_failed": '❌ File not sent: {error}',
    "sys_btn_logs": "📄 Logs",
    "bk_title": '💾 <b>Config backup</b>',
    "bk_contents": (
        'The archive contains:\n'
        '• 🎛 Global toggles and all bot settings\n'
        '• 🤖 Auto-response\n'
        '• 📦 Auto-delivery: items and stock (the goods themselves)\n'
        '• 🔔 Notification settings\n'
        '• 🔑 Playerok account: cookies, user-agent, account proxy\n'
        '• ✈️ Telegram bot token and admin list\n'
        '• 💳 Last withdrawal method\n'
        '• 🚫 Blacklist\n'
        '• 🌙 Night message, digest time, timezone, auto-raise\n'
        '\n'
        'Not included: delivery ledger, saved proxies (🌐), caches and logs.\n'
        '📥 Import: current settings are saved to <code>storage/backups/</code> first, '
        'then the bot restarts.'
    ),
    "bk_warning": '⚠️ It contains cookies and the bot token — never share the archive.',
    "bk_btn_import": '📥 Import',
    "bk_btn_export": '📤 Export',
    "bk_export_caption": '💾 Fixer config backup.\n⚠️ It contains cookies and the bot token — never share it.',
    "bk_export_failed": '❌ Could not build the archive: {error}',
    "bk_send_file": '📥 Send the backup archive (<code>fixer-backup_….zip</code>) as a file to this chat.',
    "bk_err": 'Archive rejected: {error}',
    "bk_err_apply": 'Could not apply the archive: {error}',
    "bk_err_not_file": 'A file is needed — the .zip backup archive.',
    "bk_applied": '✅ Backup from <b>{date}</b> (account <b>{account}</b>) applied.',
    "bk_stocks": '📦 Auto-delivery stocks restored: <b>{count}</b>',
    "bk_tg_same": '✈️ Bot token and admins: unchanged',
    "bk_tg_changed": '✈️ Bot token and/or admins replaced from the archive',
    "bk_restarting": '🔄 Restarting…',
    "bk_started_line": '✅ Backup from {date} applied',
    "sys_btn_backup": "💾 Config backup",
    "sys_btn_reload": "🔄 Reload configs",
    "sys_btn_update": "⬇️ Update from GitHub",
    "sys_update_confirm": (
        "Download the latest version from GitHub (<code>{repo}</code>) and restart Fixer?\n\n"
        "configs/, storage/, and your plugins/ are kept."
    ),
    "sys_btn_update_yes": "Yes, update",
    "sys_update_running": "⬇️ Downloading update from GitHub…",
    "sys_update_ok": "✅ {message}",
    "sys_update_ok_restart": (
        "✅ {message}\n{detail}\n\n🔁 Restarting with the new version… "
        "The panel will be back in a few seconds (/menu)."
    ),
    "sys_update_failed": "❌ Update failed: {message}",
    "sys_reloaded": "🔄 Configs reloaded: {details}",

    # --- UI Tests ---
    "sys_btn_tests": "🧪 Tests",
    "test_title": "🧪 <b>Notification Tests</b>",
    "test_user_message": "👤 Message from Test",
    "test_support_message": '🛟 Support chat',
    "test_new_deal": "🛒 New Deal",
    "test_deal_confirmed": "🤝 Deal Confirmed",
    "test_new_review": "⭐ New Review",
    "test_delivery_ok": "📦 Successful Delivery",
    "test_error": "🚨 Error",
    "test_payout": "💳 Payout",
    "test_item_expiring": "⏳ Item delisting",
    "test_blacklist": '🚫 Blacklisted deal',
    "test_system_notice": '📢 Playerok notice',
    "test_staff_event": '👀 Viewing chat',
    "test_staff_finished": "✅ Chat finished",
    "test_item_expiring_plain": "⏳ Delisting (no item)",
    "test_deal_problem": "⚠️ Deal problem",
    "test_problem_resolved": "✅ Problem resolved",
    "test_rolled_back": "↩️ Deal refunded",
    "test_raise_limit": "🛑 Raise limit",
    "test_item_raised": "📈 Item raised",
    "test_no_balance": "💸 Low balance",
    "test_stock_empty": "📭 Stock empty",
    "test_started": "🐦 Bot started",
    "test_page_1": "📄 <b>Page 1:</b> messages, support, deals",
    "test_page_2": "📄 <b>Page 2:</b> problems, modules, service",
    "test_support_in_deal": '🛟 Support in a deal',

    # --- Plugins ---
    "pl_title": "🧩 <b>Plugins</b>\n\nLoaded from <code>plugins/</code>:",
    "pl_no_plugins": "No plugins found.",
    "pl_line": "{state} {name} <i>{version}</i>",
    "pl_btn_install": "➕ Install plugin",
    "pl_install_warning": (
        "⚠️ <b>Warning!</b> A plugin is executable Python code with full access to your "
        "account and server. Install plugins only from trusted sources.\n\n"
        "Send a <code>.py</code> file to install a plugin."
    ),
    "pl_installed": "✅ Plugin \"{name}\" installed and loaded.",
    "pl_install_failed": "❌ Failed to install plugin: {error}",
    "pl_toggled_on": "Plugin \"{name}\" enabled.",
    "pl_toggled_off": "Plugin \"{name}\" disabled.",
    "pl_delete_confirm": "Delete plugin \"{name}\"? Its handlers will be unloaded and the file removed from plugins/.",
    "pl_btn_delete_yes": "Yes, delete",
    "pl_deleted": "🗑 Plugin \"{name}\" deleted.",
    "sys_btn_clear": '🗑 Clear notifications',
    "clear_title": '🗑 <b>Clearing notifications</b>',
    "clear_today": '📅 Last 24 hours',
    "clear_week": '📅 Last 7 days',
    "clear_all": '🗑 All notifications',
    "clear_result": (
        '🗑 Messages deleted: {removed}\n'
        '⚠️ Errors: {failed}'
    ),

    # --- Связь с Playerok (playerok_link.py) ---
    "notif_playerok_unavailable": "⚠️ <b>Playerok is unavailable</b>\n\nRetrying in 30 s, 1 min, 2 min, 5 min and then every 5 min. I will let you know when it works.\n\n<b>Reason:</b> <code>{reason}</code>",
    "notif_playerok_connected": "✅ <b>Connected to Playerok</b>\n\nDeals and messages are tracked again.",
    "notif_playerok_lost": "⚠️ <b>Lost connection to Playerok</b>\n\nNo response for over 3 minutes. Reconnecting automatically — I will let you know when it is back.",
    "notif_playerok_restored": "✅ <b>Connection to Playerok restored</b>",
    "plink_btn_retry": "🔄 Retry connection",
    "plink_retry_started": "🔄 Retrying now…",
    "plink_already_connected": "✅ Playerok is already connected",
    "test_playerok_unavailable": "⚠️ Playerok unavailable",
    "test_playerok_lost": "⚠️ Connection lost",
    "test_playerok_then": "<i>↓ Once connected, the message turns into:</i>",
}
