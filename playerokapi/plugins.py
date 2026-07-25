"""
Плагинная система `playerokapi` (аналог `FunPayCardinal`, но встроена прямо в библиотеку).

Плагин — это `.py`-файл в папке `plugins/`, объявляющий на уровне модуля метаданные (`NAME`,
`VERSION`, `DESCRIPTION`, `CREDITS`, `UUID`) и функцию `init(manager: PluginManager)`, которая
регистрирует хендлеры через `manager.bind(hook_name, handler)`.

`PluginManager` поддерживает:

- Фиксированные хуки жизненного цикла и событий (см. `common.enums.Hooks`) — например
  `PRE_INIT`/`POST_INIT`, `NEW_MESSAGE`, `NEW_DEAL`, `DEAL_STATUS_CHANGED`, `PRE_START`/`POST_START` и т.п.
- Автоматические хуки `PRE_<имя_метода>`/`POST_<имя_метода>` на каждый публичный метод `Account`
  (после `attach_to_account`) — например `PRE_send_message`, `POST_create_item`.
- Динамическое включение/выключение плагинов без перезапуска (`enable_plugin`/`disable_plugin`).

Использование опционально: если не создавать `PluginManager`, библиотека работает как обычный
API-клиент без какого-либо оверхеда.
"""
from __future__ import annotations

import functools
import importlib.util
import logging
import os
import sys
import uuid as uuid_module
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("playerokapi.plugins")


@dataclass
class PluginInfo:
    """Метаданные загруженного плагина."""

    uuid: str
    """Уникальный идентификатор плагина (из атрибута `UUID` модуля либо сгенерированный по пути к файлу)."""
    name: str
    """Название плагина (атрибут `NAME` модуля, либо имя файла, если не указано)."""
    version: str | None
    """Версия плагина (атрибут `VERSION` модуля)."""
    description: str | None
    """Описание плагина (атрибут `DESCRIPTION` модуля)."""
    credits: str | None
    """Автор/благодарности (атрибут `CREDITS` модуля)."""
    path: str
    """Путь к файлу плагина."""
    module: object = field(repr=False)
    """Импортированный модуль плагина."""
    enabled: bool = True
    """Включён ли плагин сейчас (хендлеры выключенного плагина не вызываются)."""


class PluginManager:
    """
    Менеджер плагинов `playerokapi`.

    :param plugins_dir: Папка, из которой автоматически загружаются плагины при вызове `load_plugins()`.
    """

    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir: str = plugins_dir
        self.plugins: dict[str, PluginInfo] = {}
        self.account = None
        self._hooks: dict[str, list[tuple[str, Callable]]] = {}

    # ------------------------------------------------------------------
    # Регистрация и вызов хендлеров
    # ------------------------------------------------------------------

    def bind(self, hook_name, handler: Callable, plugin_uuid: str | None = None) -> None:
        """
        Регистрирует хендлер на хук.

        :param hook_name: Имя хука — значение `common.enums.Hooks` (или его `.value`), либо строка
            `"PRE_<метод>"`/`"POST_<метод>"` для авто-хуков методов `Account`, либо произвольная строка.
        :param handler: Функция-хендлер вида `def handler(account, **kwargs): ...`.
        :param plugin_uuid: UUID плагина-владельца (проставляется автоматически при загрузке из файла).
        """
        name = hook_name.value if hasattr(hook_name, "value") else str(hook_name)
        self._hooks.setdefault(name, []).append((plugin_uuid or "__manual__", handler))

    def unbind_all(self, plugin_uuid: str) -> None:
        """Снимает все хендлеры, зарегистрированные плагином с указанным UUID."""
        for name, handlers in list(self._hooks.items()):
            self._hooks[name] = [(pid, h) for pid, h in handlers if pid != plugin_uuid]

    def dispatch(self, hook_name, **kwargs) -> None:
        """
        Вызывает все активные хендлеры, зарегистрированные на хук.

        Хендлеры плагинов, отключённых через `disable_plugin`, не вызываются. Исключение в одном
        хендлере не прерывает вызов остальных — оно логируется и подавляется.
        """
        name = hook_name.value if hasattr(hook_name, "value") else str(hook_name)
        # Вызывающий код (например, Runner) может передать account сам — не дублируем kwarg,
        # иначе каждый хендлер падал бы с TypeError "multiple values for argument 'account'".
        kwargs.setdefault("account", self.account)
        for plugin_uuid, handler in self._hooks.get(name, []):
            plugin = self.plugins.get(plugin_uuid)
            if plugin is not None and not plugin.enabled:
                continue
            try:
                handler(**kwargs)
            except Exception:
                logger.exception("Ошибка в хендлере плагина %s на хуке %s", plugin_uuid, name)

    # ------------------------------------------------------------------
    # Авто-хуки на методы Account
    # ------------------------------------------------------------------

    def attach_to_account(self, account) -> None:
        """
        Оборачивает публичные методы переданного аккаунта авто-хуками `PRE_<метод>`/`POST_<метод>`.

        Оборачиваются только методы конкретного экземпляра `account` — остальные экземпляры
        `Account` в этом же процессе не затрагиваются.

        :param account: Экземпляр `playerokapi.account.Account`.
        """
        self.account = account
        for attr_name in dir(account):
            if attr_name.startswith("_"):
                continue
            attr = getattr(account, attr_name, None)
            if not callable(attr) or not hasattr(attr, "__func__"):
                continue
            setattr(account, attr_name, self._wrap_method(attr_name, attr))

    def _wrap_method(self, method_name: str, method: Callable) -> Callable:
        pre_hook = f"PRE_{method_name}"
        post_hook = f"POST_{method_name}"

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            self.dispatch(pre_hook, method_name=method_name, args=args, kwargs=kwargs)
            result = method(*args, **kwargs)
            self.dispatch(post_hook, method_name=method_name, args=args, kwargs=kwargs, result=result)
            return result

        return wrapper

    # ------------------------------------------------------------------
    # Загрузка плагинов из файлов
    # ------------------------------------------------------------------

    def load_plugins(self) -> list[PluginInfo]:
        """
        Загружает все `.py`-файлы из `plugins_dir` (кроме начинающихся с `_`) как плагины.

        Для каждого файла: импортирует модуль, читает метаданные, вызывает `module.init(self)`,
        если она определена. Ошибка при загрузке одного плагина не прерывает загрузку остальных.

        :return: Список успешно загруженных плагинов.
        """
        if not os.path.isdir(self.plugins_dir):
            return []
        loaded: list[PluginInfo] = []
        for filename in sorted(os.listdir(self.plugins_dir)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            path = os.path.join(self.plugins_dir, filename)
            try:
                plugin_info = self._load_plugin_file(path)
                if plugin_info:
                    loaded.append(plugin_info)
            except Exception:
                logger.exception("Не удалось загрузить плагин из файла %s", path)
        return loaded

    def _load_plugin_file(self, path: str) -> PluginInfo | None:
        module_name = f"playerokapi_plugin_{os.path.splitext(os.path.basename(path))[0]}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugin_uuid = getattr(module, "UUID", None) or str(uuid_module.uuid5(uuid_module.NAMESPACE_URL, path))
        plugin_info = PluginInfo(
            uuid=plugin_uuid,
            name=getattr(module, "NAME", os.path.basename(path)),
            version=getattr(module, "VERSION", None),
            description=getattr(module, "DESCRIPTION", None),
            credits=getattr(module, "CREDITS", None),
            path=path,
            module=module,
        )
        self.plugins[plugin_uuid] = plugin_info

        init_func = getattr(module, "init", None)
        if callable(init_func):
            original_bind = self.bind

            def bound_bind(hook_name, handler, _uuid=plugin_uuid):
                original_bind(hook_name, handler, plugin_uuid=_uuid)

            self.bind = bound_bind
            try:
                init_func(self)
            finally:
                self.bind = original_bind

        logger.info("Загружен плагин %s (%s)", plugin_info.name, plugin_info.version or "?")
        return plugin_info

    # ------------------------------------------------------------------
    # Включение/выключение плагинов
    # ------------------------------------------------------------------

    def enable_plugin(self, plugin_uuid: str) -> None:
        """Включает плагин (его хендлеры снова будут вызываться)."""
        if plugin_uuid in self.plugins:
            self.plugins[plugin_uuid].enabled = True

    def disable_plugin(self, plugin_uuid: str) -> None:
        """Выключает плагин (его хендлеры перестают вызываться, но остаются зарегистрированными)."""
        if plugin_uuid in self.plugins:
            self.plugins[plugin_uuid].enabled = False

    def unload_plugin(self, plugin_uuid: str) -> PluginInfo | None:
        """
        Полностью выгружает плагин: снимает все его хендлеры и убирает из реестра.

        Файл плагина не трогается — удалить его (чтобы плагин не вернулся при следующем
        `load_plugins()`) должен вызывающий код.

        :return: Метаданные выгруженного плагина, либо `None`, если такого не было.
        """
        plugin = self.plugins.pop(plugin_uuid, None)
        if plugin is not None:
            self.unbind_all(plugin_uuid)
            logger.info("Плагин %s выгружен", plugin.name)
        return plugin
