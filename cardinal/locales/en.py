"""English locale for PlayerokCardinal."""

STRINGS = {
    # --- Common / TG auth ---
    "unauthorized": "⛔ You are not authorized. Send the secret code from the Cardinal console to bind yourself as an admin.",
    "auth_success": "✅ You are now a PlayerokCardinal administrator.",
    "auth_wrong_code": "❌ Wrong code. The current code is printed in the Cardinal console.",
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
    "btn_auto_publish": "📤 Auto-publish",
    "btn_last_deals": "🕒 Recent deals",
    "alert_in_development": "⏸ The “{section}” section is under development — coming in future updates.",
    "btn_close": "✖️ Close",
    "cancelled": "Action cancelled.",
    "stub_message": "⏸ Section has been moved to Settings",
    "btn_cancel": "Cancel",

    # --- Main menu ---
    "menu_title": (
        "🐦 <b>PlayerokCardinal</b>\n\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "📩 New messages: <b>{unread_messages}</b>\n"
        "⏱ Uptime: <b>{uptime}</b>"
    ),
    "menu_section_toggles": "🎛 Global toggles",
    "menu_section_stats": "📈 Statistics",
    "menu_section_autodelivery": "📦 Auto-delivery",
    "menu_section_autoresponse": "💬 Auto-response",
    "menu_section_blacklist": "🚫 Blacklist",
    "menu_section_notifications": "🔔 Notifications",
    "menu_section_stub": "⏸ Under development",
    "menu_section_plugins": "🧩 Plugins",
    "menu_section_settings": "⚙️ Settings",
    "menu_btn_digest": "📊 Digest now",
    "btn_reply_menu": "Menu",
    "menu_keyboard_hint": "📋 The “Menu” button is under the input field. Tap the arrow to collapse it into a compact button.",
    "module_autodelivery": "Auto-delivery",
    "module_autoraise": "Auto-raise",
    "module_autoresponse": "Auto-response",
    "module_autorestore": "Auto-restore",
    "module_greeting": "Greeting",
    "module_online": "Always online",
    "module_digest": "Daily digest",
    "module_toggled_on": "Module \"{module}\" enabled.",
    "module_toggled_off": "Module \"{module}\" disabled.",

    # --- Global toggles ---
    "gl_title": "🎛 <b>Global toggles</b>\n\nTap a module to enable or disable it:",
    "gl_btn_greeting_text": "✏️ Greeting text",
    "gl_enter_greeting": (
        "Send the new greeting text.\n"
        "Variable <code>$username</code> — buyer's username.\n\n"
        "Current text:\n<code>{current}</code>"
    ),
    "gl_greeting_saved": "✅ Greeting text saved.",

    # --- Statistics ---
    "st_title": "📈 <b>Sales statistics</b> (last 7 days):",
    "st_line": "• {day}: <b>{count}</b> pcs. for <b>{revenue}</b>",
    "st_empty": "No sales in the last 7 days.",
    "st_total_week": "Total for 7 days: <b>{count}</b> pcs. for <b>{revenue}</b>",
    "st_total_month": "Total for 30 days: <b>{count}</b> pcs. for <b>{revenue}</b>",

    # --- Auto-delivery ---
    "ad_title": "📦 <b>Auto-delivery</b>\n\nLots and stock:",
    "ad_no_lots": "No lots configured yet.",
    "ad_lot_line": "• {name} — <b>{stock}</b> pcs.",
    "ad_btn_add_lot": "➕ Add lot",
    "ad_lot_title": (
        "📦 Lot <b>{name}</b>\n"
        "Stock file: <code>{stock_file}</code>\n"
        "In stock: <b>{stock}</b> pcs.\n"
        "Auto-restore: {restore}\n"
        "Deactivate when empty: {deactivate}"
    ),
    "ad_btn_view_stock": "👀 View stock",
    "ad_stock_view_title": "📦 <b>Stock \"{name}\"</b> — items: <b>{total}</b>",
    "ad_stock_view_empty": "The stock is empty.",
    "ad_stock_more": "… and {count} more items",
    "ad_btn_add_stock": "➕ Add stock",
    "ad_btn_toggle_restore": "♻️ Restore: {state}",
    "ad_btn_toggle_deactivate": "🛑 Deactivate: {state}",
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
    "bl_title": "🚫 <b>Blacklist</b>\n\nThese buyers are ignored by auto-response and greeting, and their purchases trigger a warning.\nTap a username to remove it:",
    "bl_empty": "The blacklist is empty.",
    "bl_btn_add": "➕ Add username",
    "bl_enter_username": "Send the Playerok buyer username (case-insensitive):",
    "bl_added": "🚫 <code>{username}</code> added to the blacklist.",
    "bl_already": "<code>{username}</code> is already blacklisted.",
    "bl_removed": "✅ {username} removed from the blacklist.",
    "bl_missing": "Username not found (the list may have changed). Re-open the section.",

    # --- Daily digest ---
    "digest_text": (
        "📊 <b>Digest for {date}</b>\n\n"
        "🛒 Sales: <b>{sales}</b>\n"
        "💰 Revenue: <b>{revenue}</b>\n"
        "💳 Balance: <b>{balance}</b>\n"
        "⏱ Uptime: <b>{uptime}</b>\n\n"
        "📦 Stock left:\n{stocks}"
    ),
    "digest_stock_line": "• {name} — <b>{stock}</b> pcs.",
    "digest_no_stocks": "no auto-delivery stocks configured",
    "digest_unavailable": "The digest module is unavailable.",

    # --- Notifications ---
    "nt_title": "🔔 <b>Notifications</b>\n\nTap to toggle:",
    "nt_new_deal": "New deal",
    "nt_item_paid": "Item paid",
    "nt_delivery": "Delivery",
    "nt_new_message": "New messages",
    "nt_new_review": "New reviews",
    "nt_deal_problem": "Deal problems",
    "nt_deal_confirmed": "Deal confirmations",
    "nt_deal_rolled_back": "Deal rollbacks",
    "nt_item_raised": "Item raised",
    "nt_insufficient_balance": "Insufficient balance",
    "nt_errors": "Errors",
    "nt_stock_empty": "Empty stock",
    "nt_blacklist": "Blacklist deals",

    # --- Notification texts ---
    "notif_started": (
        "🐦 <b>PlayerokCardinal started</b>\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "🌙 Missed deals: <b>{missed_deals}</b>\n"
        "📩 New messages: <b>{unread_messages}</b>\n"
        "🧩 Modules: {modules}"
    ),
    "notif_new_deal": (
        "🛒 <b>New deal</b>\n"
        "📂 <b>Section:</b> {section}\n"
        "🎁 <b>Item:</b> {item}\n"
        "👤 <b>Buyer:</b> {buyer}\n"
        "📋 <b>Status:</b> {status}\n"
        "💰 <b>Price:</b> {price} ₽\n\n"
        "💬 <i>Reply to message, sends to chat</i>\n"
        "🆔 <code>{chat_id}</code>"
    ),
    "notif_item_paid": "💸 <b>Item paid</b>\nItem: {item}\nBuyer: {buyer}",
    "notif_delivery_ok": "📦 <b>Item delivered</b>\nItem: {item}\nStock left: {stock} pcs.",
    "notif_new_message": (
        "💌 <b>{username}</b>\n\n"
        "🎁 <b>Item:</b> {item}\n\n"
        "💬 {text}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Reply to message, sends to chat</i>"
    ),
    "notif_payout": (
        "💳 <b>Withdrawal from balance</b>\n\n"
        "💸 <b>Amount:</b> <code>-{amount} ₽</code>\n"
        "🏦 <b>Method:</b> {method}\n"
        "📋 <b>Status:</b> {status}\n"
        "🕒 <b>Date:</b> {date}\n"
        "💰 <b>Balance:</b> {balance}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Reply to message, sends to chat</i>"
    ),
    "notif_item_expiring": (
        "⏳ <b>Item will be delisted soon</b>\n\n"
        "🎁 <b>Item:</b> {item}\n"
        "📂 <b>Section:</b> {section}\n"
        "💰 <b>Price:</b> {price}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Reply to message, sends to chat</i>"
    ),
    "notif_item_expiring_plain": (
        "⏳ <b>Item will be delisted soon</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 {text}\n\n"
        "<i>Reply to message, sends to chat</i>"
    ),
    "notif_new_review": "⭐ <b>New review</b> ({rating}/5) from {author}:\n{text}",
    "notif_deal_problem": "⚠️ <b>Deal problem</b>\nItem: {item}\nDeal: <code>{deal_id}</code>",
    "notif_deal_problem_resolved": "✅ Problem in deal <code>{deal_id}</code> resolved.",
    "notif_deal_confirmed": (
        "🤝 <b>Deal confirmed</b>\n\n"
        "📂 <b>Section:</b> {section}\n"
        "🎁 <b>Item:</b> {item}\n"
        "👤 <b>Buyer:</b> {buyer}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Price:</b> {price} ₽\n\n"
        "🆔 <code>{chat_id}</code>"
    ),
    "notif_deal_rolled_back": "↩️ <b>Deal rolled back</b>\nItem: {item}",
    "notif_item_raised": "📈 Item \"{item}\" raised (spent {spent}).",
    "notif_insufficient_balance": "💸 Not enough balance to raise \"{item}\": need {price}, available {available}.",
    "notif_error": "🚨 <b>Cardinal error</b>:\n<code>{error}</code>",
    "notif_stock_empty": "📭 Stock for \"{item}\" is empty! Refill it to keep auto-delivery working.",
    "notif_restore_ok": "♻️ Item \"{item}\" restored after sale (new ID: <code>{item_id}</code>).",
    "notif_restore_fail": "♻️❌ Failed to restore item \"{item}\": {error}",
    "notif_restore_premium_fallback": (
        "♻️⚠️ Item \"{item}\" restored for free (new ID: <code>{item_id}</code>). "
        "Premium status was not paid: {reason}."
    ),
    "notif_blacklist_deal": "🚫 <b>Deal with a blacklisted buyer!</b>\nBuyer: {buyer}\nItem: {item}\nPlease check the deal manually.",
    "reply_sent": "✅ Sent to the Playerok chat.",
    "reply_failed": "❌ Failed to send: {error}",
    "reply_unknown": "Not sure where to send this: reply to a message notification.",

    # --- Settings ---
    "settings_title": "⚙️ <b>Settings</b>",
    "sys_btn_logs": "📄 Logs",
    "sys_btn_backup": "💾 Backup",
    "sys_backup_caption": "💾 Backup of Cardinal configs and data.\n⚠️ Contains account cookies — never share this archive!",
    "sys_btn_reload": "🔄 Reload configs",
    "sys_btn_update": "⬇️ Update from GitHub",
    "sys_update_confirm": (
        "Download the latest version from GitHub (<code>{repo}</code>) and restart Cardinal?\n\n"
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
    "sys_btn_restart": "🔁 Restart",
    "sys_restart_confirm": "Restart Cardinal? The bot will be unavailable for a few seconds.",
    "sys_btn_restart_yes": "Yes, restart",
    "sys_restart_done": "🔁 Restarting… The panel will be back in a few seconds (/menu).",
    "sys_btn_shutdown": "🛑 Shut down Cardinal",
    "sys_logs_title": "Last log lines:",
    "sys_logs_empty": "Log file is empty or not created yet.",
    "sys_reloaded": "🔄 Configs reloaded: {details}",
    "sys_shutdown_confirm": "Really shut down Cardinal? You can only start it again from the server.",
    "sys_btn_shutdown_yes": "Yes, shut down",
    "sys_shutdown_done": "🛑 Shutting down…",

    # --- UI Tests ---
    "sys_btn_tests": "🧪 Tests",
    "test_title": "🧪 <b>Notification Tests</b>",
    "test_user_message": "👤 Message from Test",
    "test_support_message": "🛠 Message from Admin",
    "test_new_deal": "🛒 New Deal",
    "test_deal_confirmed": "🤝 Deal Confirmed",
    "test_new_review": "⭐ New Review",
    "test_delivery_ok": "📦 Successful Delivery",
    "test_error": "🚨 Error",
    "test_payout": "💳 Payout",
    "test_item_expiring": "⏳ Item delisting",
    "test_photo": "🖼 Item photo",

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
}