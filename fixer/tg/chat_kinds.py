"""Какой это чат и кто в нём пишет: покупатель, сотрудник Playerok или сама площадка.

У Playerok три вида чатов (`Chat.type`):

* ``PM`` — переписка с покупателем (чат сделки);
* ``SUPPORT`` — чат с поддержкой;
* ``NOTIFICATIONS`` — уведомления площадки («товар заблокирован», «снимут через 7 дней»,
  выплаты). Единственный участник — сам продавец, у сообщений нет отправителя.

В WS-кадре нового сообщения тип чата не приходит, поэтому тип определяется и по ID:
у профиля аккаунта есть `support_chat_id` и `system_chat_id`.

Сотрудник площадки определяется по роли пользователя: всё, что не ``USER``
(``SUPPORT`` 🔰, ``SECURITY`` ⚖️, ``POSTMODERATOR`` 📦 и т.д.). Эмодзи в нике не
используются — их может поставить себе кто угодно.
"""
from __future__ import annotations

from typing import Any

SUPPORT = "support"
SYSTEM = "system"
PM = "pm"

#: Как эти чаты подписываются в списке чатов и уведомлениях.
SUPPORT_TITLE = "🛟 Поддержка Playerok"
SYSTEM_TITLE = "📢 Уведомления Playerok"
#: Отправитель сообщений из чата уведомлений (у них нет автора).
SYSTEM_SENDER = "📢 Playerok"
#: Автоответы в чате поддержки (тоже без автора): «Как проходит сделка?» и т.п.
SUPPORT_BOT = "🤖 Бот поддержки"

#: Роли, которые НЕ являются сотрудниками площадки.
_REGULAR_ROLES = frozenset({"USER"})


def _type_name(chat: Any) -> str | None:
    chat_type = getattr(chat, "type", None)
    if chat_type is None:
        return None
    return getattr(chat_type, "name", str(chat_type)).upper()


def chat_kind(chat: Any, account: Any = None) -> str:
    """``SUPPORT`` / ``SYSTEM`` / ``PM`` для чата (по типу, а если его нет — по ID из профиля)."""
    type_name = _type_name(chat)
    if type_name == "SUPPORT":
        return SUPPORT
    if type_name == "NOTIFICATIONS":
        return SYSTEM
    chat_id = getattr(chat, "id", None) if chat is not None else None
    profile = getattr(account, "profile", None) if account is not None else None
    if chat_id and profile is not None:
        if chat_id == getattr(profile, "support_chat_id", None):
            return SUPPORT
        if chat_id == getattr(profile, "system_chat_id", None):
            return SYSTEM
    return PM


def role_name(user: Any) -> str | None:
    """Роль пользователя строкой (``USER``, ``SECURITY``…), ``None`` — если неизвестна."""
    if user is None:
        return None
    raw = getattr(user, "raw_role", None)
    if raw:
        return str(raw).upper()
    role = getattr(user, "role", None)
    if role is None:
        return None
    return getattr(role, "name", str(role)).upper()


def is_staff(user: Any) -> bool:
    """Сотрудник Playerok: известная роль, отличная от обычного пользователя."""
    role = role_name(user)
    return role is not None and role not in _REGULAR_ROLES


def is_staff_message(message: Any) -> bool:
    """Сообщение от сотрудника: по роли автора (или автора события) либо по полю ``moderator``."""
    if message is None:
        return False
    if getattr(message, "moderator", None) is not None:
        return True
    return is_staff(getattr(message, "user", None)) or is_staff(getattr(message, "event_by_user", None))


def staff_event(message: Any) -> str | None:
    """``CHAT_STARTED`` («Смотрим чат…») / ``CHAT_FINISHED`` («Чат завершён») или ``None``."""
    event = getattr(message, "event", None) if message is not None else None
    if event is None:
        return None
    name = getattr(event, "name", str(event)).upper()
    return name if name in ("CHAT_STARTED", "CHAT_FINISHED") else None


def staff_display_name(message: Any) -> str:
    """Имя сотрудника из сообщения (ник уже содержит значок роли, например «⚖️ Виктор Г.»)."""
    for attr in ("event_by_user", "user"):
        user = getattr(message, attr, None)
        name = getattr(user, "username", None) if user is not None else None
        if name:
            return name
    moderator = getattr(message, "moderator", None)
    return getattr(moderator, "username", None) or "Сотрудник Playerok"


def counterpart(chat: Any, own_id: str | None) -> Any:
    """Собеседник в чате: первый участник, который не продавец и не сотрудник (или ``None``)."""
    for user in getattr(chat, "users", None) or []:
        if getattr(user, "id", None) != own_id and not is_staff(user):
            return user
    return None


def chat_title(chat: Any, account: Any) -> str:
    """Подпись чата в списке: поддержка / уведомления / ник покупателя."""
    kind = chat_kind(chat, account)
    if kind == SUPPORT:
        return SUPPORT_TITLE
    if kind == SYSTEM:
        return SYSTEM_TITLE
    other = counterpart(chat, getattr(account, "id", None))
    name = getattr(other, "username", None) if other is not None else None
    return f"👤 {name or 'Unknown'}"
