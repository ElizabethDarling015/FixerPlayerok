"""English locale for PlayerokCardinal."""

STRINGS = {
    # --- Common / TG auth ---
    "unauthorized": "⛔ You are not authorized. Send the secret code from the Cardinal console to bind yourself as an admin.",
    "auth_success": "✅ You are now a PlayerokCardinal administrator.",
    "auth_wrong_code": "❌ Wrong code. The current code is printed in the Cardinal console.",
    "btn_back": "◀️ Back",
    "btn_home": "🏠 Main menu",
    "btn_close": "✖️ Close",
    "cancelled": "✖️ Action cancelled.",
    "btn_cancel": "✖️ Cancel",

    # --- Main menu ---
    "menu_title": (
        "🐦 <b>PlayerokCardinal</b>\n\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "⏱ Uptime: <b>{uptime}</b>"
    ),
    "menu_section_toggles": "🎛 Global toggles",
    "menu_section_stats": "📈 Statistics",
    "menu_section_autodelivery": "📦 Auto-delivery",
    "menu_section_autoresponse": "💬 Auto-response",
    "menu_section_blacklist": "🚫 Blacklist",
    "menu_section_notifications": "🔔 Notifications",
    "menu_section_plugins": "🧩 Plugins",
    "menu_section_system": "⚙️ System",
    "menu_btn_digest": "📊 Digest now",
    "module_autodelivery": "Auto-delivery",
    "module_autoraise": "Auto-raise",
    "module_autoresponse": "Auto-response",
    "module_autorestore": "Auto-restore",
    "module_greeting": "Greeting",
    "module_postsale": "Post-sale",
    "module_online": "Always online",
    "module_digest": "Daily digest",
    "module_autoupdate": "Update checks",
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
    "st_line": "<code>{day} {bar}</code> <b>{count}</b> pcs. / <b>{revenue}</b>",
    "st_empty": "No sales in the last 7 days.",
    "st_total_week": "Total for 7 days: <b>{count}</b> pcs. for <b>{revenue}</b>",
    "st_total_month": "Total for 30 days: <b>{count}</b> pcs. for <b>{revenue}</b>",
    "st_bot_title": "🤖 <b>Bot activity</b> (today / 7 days / total):",
    "st_bot_delivered": "Items delivered: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",
    "st_bot_raised": "Lots raised: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",
    "st_bot_responses": "Auto-replies: <b>{today}</b> / <b>{week}</b> / <b>{total}</b>",

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
        "Deactivate when empty: {deactivate}\n"
        "Own delivery text: {own_text}\n"
        "Unpublish when stock is empty: {auto_deact}"
    ),
    "ad_btn_view_stock": "👀 View stock",
    "ad_stock_view_title": "📦 <b>Stock \"{name}\"</b> — items: <b>{total}</b>",
    "ad_stock_view_empty": "The stock is empty.",
    "ad_stock_more": "… and {count} more items",
    "ad_btn_add_stock": "➕ Add stock",
    "ad_btn_toggle_restore": "♻️ Restore: {state}",
    "ad_btn_toggle_deactivate": "🛑 Deactivate: {state}",
    "ad_btn_delete_lot": "🗑 Delete lot",
    "ad_delete_confirm": (
        "🗑 <b>Delete lot?</b>\n\n"
        "Lot \"{name}\" will be removed from auto-delivery.\n"
        "The stock file is kept on disk."
    ),
    "ad_btn_delete_yes": "🗑 Yes, delete",
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
    "ad_btn_delivery_text": "✏️ Delivery text",
    "ad_enter_delivery_text": (
        "Send the new delivery message text.\n"
        "Placeholder <code>{{item}}</code> (required) — the stock item being delivered.\n\n"
        "Current text:\n<code>{current}</code>"
    ),
    # Called without kwargs — str.format is not applied, so {item} stays literal here.
    "ad_text_needs_item": "⚠️ The text has no <code>{item}</code> — without it the buyer won't receive the goods. Send the text again.",
    "ad_delivery_text_saved": "✅ Delivery text saved.",
    "ad_btn_lot_delivery_text": "✏️ Lot delivery text",
    "ad_enter_lot_delivery_text": (
        "Send the delivery text for lot \"{name}\" — it will be used instead of the common one.\n"
        "Placeholder <code>{{item}}</code> (required) — the stock item being delivered.\n"
        "Send \"-\" to switch the lot back to the common delivery text.\n\n"
        "Current text:\n<code>{current}</code>"
    ),
    "ad_lot_delivery_text_saved": "✅ Own delivery text for lot \"{name}\" saved.",
    "ad_lot_delivery_text_reset": "✅ Lot \"{name}\" uses the common delivery text again.",

    "ad_btn_pick_lot": "🎮 Pick a lot from Playerok",
    "ad_pick_loading": "Loading your Playerok lots…",
    "ad_pick_title": "🎮 <b>Your Playerok lots</b>\n\nTap a lot to add it to auto-delivery (✅ — already added):",
    "ad_pick_empty": "No active lots found on Playerok.",
    "ad_pick_failed": "❌ Could not fetch lots from Playerok:\n<code>{error}</code>\n\nAdd the lot manually with \"➕ Add lot\".",
    "ad_pick_already": "Lot \"{name}\" is already configured.",
    "ad_pick_added": "✅ Lot \"{name}\" added.",

    "ad_btn_test": "🧪 Test delivery",
    "ad_test_result": (
        "🧪 <b>Test delivery</b> — lot \"{name}\"\n\n"
        "The buyer would receive:\n<code>{text}</code>\n\n"
        "Stock left after such a delivery: <b>{stock}</b> pcs.\n"
        "The item was put back in stock, nothing was sent to any buyer."
    ),
    "ad_test_empty": "🧪 Nothing to deliver: the stock of lot \"{name}\" is empty or the auto-delivery module is off.",
    "ad_btn_toggle_auto_deact": "🛑 Unpublish empty lots: {state}",
    "ad_btn_toggle_lot_deact": "🛑 Unpublish this lot: {state}",

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
    "bl_delete_confirm": "🚫 <b>Remove from the blacklist?</b>\n\nUsername: <code>{username}</code>",
    "bl_btn_delete_yes": "✅ Yes, remove",
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
    "nt_restore": "Item restore",
    "nt_updates": "Cardinal updates",
    "nt_btn_all_on": "🟢 Enable all",
    "nt_btn_all_off": "🔴 Disable all",

    # --- Notification texts ---
    "notif_started": (
        "🐦 <b>PlayerokCardinal started</b>\n"
        "👤 Account: <b>{username}</b>\n"
        "💰 Balance: <b>{balance}</b>\n"
        "🧩 Modules: {modules}"
    ),
    "notif_new_deal": "🛒 <b>New deal</b>\nItem: {item}\nBuyer: {buyer}\nStatus: {status}",
    "notif_item_paid": "💸 <b>Item paid</b>\nItem: {item}\nBuyer: {buyer}",
    "notif_delivery_ok": "📦 <b>Item delivered</b>\nItem: {item}\nStock left: {stock} pcs.",
    "notif_new_message": "✉️ <b>{username}</b> (chat <code>{chat_id}</code>):\n{text}\n\n<i>Reply to this message to answer in the Playerok chat.</i>",
    "notif_new_review": "⭐ <b>New review</b> ({rating}/5) from {author}:\n{text}",
    "notif_deal_problem": "⚠️ <b>Deal problem</b>\nItem: {item}\nDeal: <code>{deal_id}</code>",
    "notif_deal_problem_resolved": "✅ <b>Problem resolved</b>\nDeal: <code>{deal_id}</code>",
    "notif_deal_confirmed": "🤝 <b>Deal confirmed</b>\nItem: {item}",
    "notif_deal_rolled_back": "↩️ <b>Deal rolled back</b>\nItem: {item}",
    "notif_item_raised": "📈 <b>Item raised</b>\nItem: {item}\nSpent: {spent}",
    "notif_insufficient_balance": (
        "💸 <b>Not enough balance to raise</b>\n"
        "Item: {item}\nNeed: {price}\nAvailable: {available}"
    ),
    "notif_error": "🚨 <b>Cardinal error</b>\n<code>{error}</code>",
    "notif_stock_empty": (
        "📭 <b>Stock is empty</b>\nItem: {item}\n"
        "Refill it to keep auto-delivery working."
    ),
    "notif_lot_deactivated": (
        "🛑 <b>Lot unpublished</b>\nItem: {item}\n"
        "The stock is empty — the lot was removed from Playerok so nobody buys it without goods."
    ),
    "notif_lot_deactivate_fail": (
        "🛑❌ <b>Could not unpublish the lot</b>\nItem: {item}\nError: {error}\n"
        "The stock is empty — check the lot manually."
    ),
    "notif_restore_ok": "♻️ <b>Item restored</b>\nItem: {item}\nNew ID: <code>{item_id}</code>",
    "notif_restore_fail": "♻️❌ <b>Failed to restore item</b>\nItem: {item}\nError: {error}",
    "notif_restore_premium_fallback": (
        "♻️⚠️ <b>Item restored for free</b>\n"
        "Item: {item}\nNew ID: <code>{item_id}</code>\n"
        "Premium status was not paid: {reason}."
    ),
    "notif_blacklist_deal": "🚫 <b>Deal with a blacklisted buyer!</b>\nBuyer: {buyer}\nItem: {item}\nPlease check the deal manually.",
    "notif_update_available": (
        "🆕 <b>Cardinal update available</b>\n"
        "Installed: <code>{current}</code>\nOn GitHub: <code>{latest}</code>\n\n"
        "Install: /menu → ⚙️ System → ⬇️ Update from GitHub"
    ),
    "notif_update_installed": "🆕 <b>Update installed</b>\n{message}\n\n🔁 Restarting…",
    "notif_session_expired": (
        "🔑 <b>Playerok session expired</b>\n"
        "Reason: <code>{cause}</code>\n\n"
        "The bot is no longer authorized on Playerok. Copy a fresh token from your browser and "
        "send the new token (or the full cookies string) <b>as a reply to this message</b>, "
        "or via the <code>/token &lt;value&gt;</code> command."
    ),
    "notif_poll_stalled": (
        "⏳ <b>Playerok polling is down</b>\n"
        "No successful polls for more than {minutes} min — new deals and messages "
        "are not being tracked. Check the network/proxy and account cookies."
    ),
    "notif_poll_recovered": "✅ Playerok polling is working again.",
    "session_token_usage": (
        "Usage: <code>/token &lt;value&gt;</code> — a new token (eyJ...) "
        "or the full cookies string of the Playerok account."
    ),
    "session_updated": "✅ Session updated, authorized as <b>{username}</b>.",
    "session_update_failed": (
        "❌ Failed to update the session: {error}\n"
        "The old cookies were restored, the config was not changed."
    ),
    "reply_sent": "✅ Sent to the Playerok chat.",
    "reply_failed": "❌ Failed to send: {error}",
    "reply_unknown": "Not sure where to send this: reply to a message notification.",

    # --- System ---
    "sys_title": "⚙️ <b>System</b>",
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
    "sys_logs_title": "📄 <b>Logs</b> — last lines:",
    "sys_logs_empty": "Log file is empty or not created yet.",
    "sys_btn_logfile": "⬇️ Download log file",
    "sys_logfile_caption": "📄 Full Cardinal log file.",
    "sys_reloaded": "🔄 Configs reloaded: {details}",
    "sys_shutdown_confirm": "Really shut down Cardinal? You can only start it again from the server.",
    "sys_btn_shutdown_yes": "Yes, shut down",
    "sys_shutdown_done": "🛑 Shutting down…",

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
