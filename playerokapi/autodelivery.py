"""
Авто-выдача уникального товара из файлов-складов (аналог автовыдачи `FunPayCardinal`).

Формат склада — два варианта (определяется автоматически по содержимому файла):

- **Построчный** (по умолчанию): одна позиция товара — одна строка файла.
- **Блочный**: если в файле есть строка-разделитель `---`, позиции разделяются такими строками —
  каждая позиция может занимать несколько строк (например логин + пароль + инструкция).

При выдаче позиция забирается (выдаётся покупателю и удаляется из файла), поэтому один и тот же
товар не будет отдан двум разным покупателям.

`Runner` (штатный сценарий через `ItemPaidEvent`) использует безопасную транзакционную пару методов
`reserve()`/`restore()`: товар сначала забирается со склада, и только при подтверждённой отправке
сообщения покупателю считается по-настоящему выданным — если `send_message` упал с ошибкой, товар
автоматически возвращается обратно на склад (см. `restore()`), а не теряется. Метод `deliver()` —
более простой, "небезопасный" вариант для собственных сценариев без `Runner`.

Прогресс выдачи каждой сделки фиксируется в долговечном SQLite-журнале (`delivery_ledger.DeliveryLedger`,
включён по умолчанию) — он дедуплицирует `ItemPaidEvent` между источниками и перезапусками процесса
и позволяет обнаружить сделки, у которых выдача прервалась посередине (состояние `reserved`).

Файл склада перезаписывается атомарно (временный файл + `os.replace`), поэтому сбой процесса в
момент записи не оставит склад в полузаписанном состоянии.

Конфигурация — простой JSON вида `{"название лота": "путь/к/складу.txt"}` (см. `AutoDeliveryManager.load_config`).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading

from .delivery_ledger import DeliveryLedger

logger = logging.getLogger("playerokapi.autodelivery")

#: Строка-разделитель позиций в блочном формате склада (сама по себе на строке).
STOCK_DELIMITER = "---"


def parse_stock_text(text: str) -> list[str]:
    """
    Разбирает текст склада на список позиций товара.

    Если в тексте есть строка-разделитель `---` — блочный формат (позиция может быть многострочной),
    иначе — построчный (одна непустая строка = одна позиция). Пустые позиции отбрасываются.
    """
    lines = text.splitlines()
    if any(line.strip() == STOCK_DELIMITER for line in lines):
        items: list[str] = []
        block: list[str] = []
        for line in lines:
            if line.strip() == STOCK_DELIMITER:
                item = "\n".join(block).strip()
                if item:
                    items.append(item)
                block = []
            else:
                block.append(line)
        item = "\n".join(block).strip()
        if item:
            items.append(item)
        return items
    return [line.strip() for line in lines if line.strip()]


def serialize_stock(items: list[str]) -> str:
    """
    Сериализует список позиций обратно в текст склада.

    Если хоть одна позиция многострочная — блочный формат (разделитель `---`),
    иначе — построчный.
    """
    if not items:
        return ""
    if any("\n" in item for item in items):
        # Разделитель после каждой позиции (включая последнюю) — иначе склад из одной
        # многострочной позиции при следующем чтении распался бы на построчные.
        return "".join(f"{item}\n{STOCK_DELIMITER}\n" for item in items)
    return "\n".join(items) + "\n"


def _atomic_write(path: str, content: str) -> None:
    """Атомарно перезаписывает файл: пишет во временный файл рядом и заменяет через `os.replace`."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".stock_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class AutoDeliveryManager:
    """
    Менеджер авто-выдачи товара.

    :param config: Словарь `{название лота: путь к файлу-складу}`, либо путь к JSON-файлу с такой
        конфигурацией (см. `load_config`).
    :param delivery_text_template: Шаблон сообщения, отправляемого покупателю после выдачи.
        Подстрока `{item}` заменяется на выданную строку товара.
    :param ledger_path: Путь к файлу SQLite-журнала выдач (см. `delivery_ledger.DeliveryLedger`).
        Передайте `None`, чтобы отключить журнал (дедупликация останется только в памяти процесса,
        без защиты от повторной выдачи после перезапуска).
    """

    def __init__(self, config: dict[str, str] | str | None = None,
                 delivery_text_template: str = "Спасибо за покупку! Вот ваш товар:\n{item}",
                 ledger_path: str | None = "autodelivery_ledger.sqlite3"):
        self.stock_paths: dict[str, str] = {}
        self.delivery_text_template = delivery_text_template
        self._lock = threading.Lock()
        self.ledger: DeliveryLedger | None = DeliveryLedger(ledger_path) if ledger_path else None
        """SQLite-журнал выдач (`None`, если отключён через `ledger_path=None`)."""

        if isinstance(config, str):
            self.load_config(config)
        elif isinstance(config, dict):
            self.stock_paths = dict(config)

    def load_config(self, config_path: str) -> None:
        """
        Загружает конфигурацию `{название лота: путь к складу}` из JSON-файла.

        :param config_path: Путь к JSON-файлу конфигурации.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            self.stock_paths = json.load(f)

    def set_stock_path(self, item_name: str, stock_path: str) -> None:
        """
        Привязывает лот к файлу-складу.

        :param item_name: Название лота (должно совпадать с `Item.name`/`MyItem.name` на сайте).
        :param stock_path: Путь к текстовому файлу-складу (одна позиция товара на строку).
        """
        self.stock_paths[item_name] = stock_path

    def get_stock_size(self, item_name: str) -> int:
        """
        Возвращает количество доступных для выдачи позиций товара для лота.

        :param item_name: Название лота.
        :return: Количество позиций в файле-складе — строк в построчном формате или блоков
            в блочном (`0`, если склад не настроен/пуст/не найден).
        """
        path = self.stock_paths.get(item_name)
        if not path or not os.path.isfile(path):
            return 0
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                return len(parse_stock_text(f.read()))

    def format_delivery_text(self, item_value: str) -> str:
        """Подставляет выданное значение товара в `delivery_text_template`."""
        return self.delivery_text_template.format(item=item_value)

    def reserve(self, item_name: str) -> str | None:
        """
        Забирает одну позицию товара со склада лота (потокобезопасно), но **не** отправляет её
        покупателю — это делает вызывающий код (см. `Runner._handle_autodelivery`).

        В отличие от `deliver()`, забранную позицию можно вернуть обратно через `restore()`, если
        её так и не удалось отправить покупателю (например, `send_message` упал с ошибкой) — так
        авто-выдача не теряет товар при сетевом сбое (см. README, раздел про безопасную авто-выдачу).

        :param item_name: Название лота, для которого нужно забрать товар.
        :return: Забранное значение товара (строка или многострочный блок без пробелов по краям),
            либо `None`, если для лота нет настроенного склада или он пуст.
        """
        path = self.stock_paths.get(item_name)
        if not path or not os.path.isfile(path):
            logger.warning("Для лота %r не настроен склад авто-выдачи", item_name)
            return None

        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                items = parse_stock_text(f.read())

            if not items:
                logger.warning("Склад авто-выдачи для лота %r пуст", item_name)
                return None

            item_value, remaining = items[0], items[1:]
            _atomic_write(path, serialize_stock(remaining))

        logger.info("Со склада лота %r забрана одна позиция (осталось: %d)", item_name, len(remaining))
        return item_value

    def restore(self, item_name: str, item_value: str) -> None:
        """
        Возвращает ранее забранную (`reserve()`) позицию товара обратно на склад лота (в начало,
        потокобезопасно) — чтобы её можно было выдать следующему покупателю.

        Используется, когда забранный товар не удалось доставить покупателю (см. `reserve()`).

        :param item_name: Название лота, на склад которого нужно вернуть товар.
        :param item_value: Значение товара (строка или блок, ранее полученные от `reserve()`).
        """
        path = self.stock_paths.get(item_name)
        if not path:
            # Само значение товара в лог не пишем — это секрет (ключ/аккаунт покупателя).
            logger.error("Не удалось вернуть товар на склад лота %r — склад не настроен", item_name)
            return

        with self._lock:
            existing = ""
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = f.read()
            items = [item_value.strip()] + parse_stock_text(existing)
            _atomic_write(path, serialize_stock(items))

        logger.info("Товар возвращён на склад лота %r (не удалось выдать покупателю)", item_name)

    def add_stock(self, item_name: str, text: str) -> int:
        """
        Добавляет позиции товара в конец склада лота (потокобезопасно, с атомарной записью).

        Текст разбирается как склад: позиции либо построчно, либо блоками через `---`
        (см. `parse_stock_text`). Пустые позиции игнорируются.

        :param item_name: Название лота, чей склад пополняется.
        :param text: Сырой текст с позициями (например, содержимое `.txt`-файла).
        :raises KeyError: Для лота не настроен склад.
        :return: Сколько непустых позиций добавлено.
        """
        path = self.stock_paths[item_name]
        new_items = parse_stock_text(text)
        if not new_items:
            return 0
        with self._lock:
            existing = ""
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = f.read()
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            _atomic_write(path, serialize_stock(parse_stock_text(existing) + new_items))
        logger.info("Склад лота %r пополнен: добавлено позиций — %d", item_name, len(new_items))
        return len(new_items)

    def deliver(self, item_name: str) -> str | None:
        """
        Забирает одну позицию товара из склада лота и возвращает готовый текст сообщения для
        покупателя (уже с подстановкой в `delivery_text_template`).

        Это простой "небезопасный" способ выдачи (для собственных сценариев без `Runner`) — товар
        считается выданным сразу после вызова, независимо от того, дошло ли сообщение до покупателя.
        `Runner` (при штатной авто-выдаче через `ItemPaidEvent`) использует более безопасную пару
        `reserve()`/`restore()`, которая при сбое отправки возвращает товар обратно на склад.

        :param item_name: Название лота, для которого нужно выдать товар.
        :return: Готовый текст сообщения для отправки покупателю, либо `None`, если для лота нет
            настроенного склада или он пуст (в этом случае ничего не отправляется автоматически).
        """
        item_value = self.reserve(item_name)
        if item_value is None:
            return None
        return self.format_delivery_text(item_value)
