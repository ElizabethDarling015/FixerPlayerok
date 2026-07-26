"""Тесты пер-лотового текста выдачи (`AutoDeliveryManager.delivery_texts`)."""
import threading

from playerokapi.autodelivery import AutoDeliveryManager


def make_manager(tmp_path, delivery_texts=None):
    for name, lines in (("Лот А", ("A-1", "A-2")), ("Лот Б", ("B-1", "B-2"))):
        (tmp_path / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return AutoDeliveryManager(
        config={name: str(tmp_path / f"{name}.txt") for name in ("Лот А", "Лот Б")},
        delivery_text_template="Общий текст: {item}",
        delivery_texts=delivery_texts,
        ledger_path=None,
    )


def test_lot_template_wins_over_global(tmp_path):
    manager = make_manager(tmp_path, {"Лот А": "Личный текст лота А: {item}"})
    # Явно переданное название лота (так делает «тест выдачи» из TG-панели).
    assert manager.format_delivery_text("A-1", "Лот А") == "Личный текст лота А: A-1"


def test_falls_back_to_global_template(tmp_path):
    manager = make_manager(tmp_path, {"Лот А": "Личный текст лота А: {item}"})
    assert manager.format_delivery_text("B-1", "Лот Б") == "Общий текст: B-1"
    # Лот вообще неизвестен — тоже общий шаблон.
    assert manager.format_delivery_text("X", "Чужой лот") == "Общий текст: X"


def test_reserve_binds_lot_for_call_without_name(tmp_path):
    """Runner зовёт `format_delivery_text(item_value)` без названия — лот берётся из reserve()."""
    manager = make_manager(tmp_path, {"Лот А": "Личный текст: {item}"})

    value = manager.reserve("Лот А")
    assert manager.format_delivery_text(value) == "Личный текст: A-1"

    value = manager.reserve("Лот Б")
    assert manager.format_delivery_text(value) == "Общий текст: B-1"


def test_binding_is_one_shot_and_value_checked(tmp_path):
    manager = make_manager(tmp_path, {"Лот А": "Личный текст: {item}"})
    value = manager.reserve("Лот А")

    # Чужое значение не подхватывает шаблон лота…
    assert manager.format_delivery_text("постороннее") == "Общий текст: постороннее"
    # …а после первого использования привязка снимается.
    assert manager.format_delivery_text(value) == "Личный текст: A-1"
    assert manager.format_delivery_text(value) == "Общий текст: A-1"


def test_restore_clears_binding(tmp_path):
    manager = make_manager(tmp_path, {"Лот А": "Личный текст: {item}"})
    value = manager.reserve("Лот А")
    manager.restore("Лот А", value)
    assert manager.format_delivery_text(value) == "Общий текст: A-1"


def test_binding_is_per_thread(tmp_path):
    """Параллельные выдачи (поллинг и веб-сокет — разные потоки) не путают шаблоны лотов."""
    manager = make_manager(tmp_path, {"Лот А": "Текст А: {item}", "Лот Б": "Текст Б: {item}"})
    results: dict[str, str] = {}
    started = threading.Barrier(2)

    def worker(item_name: str):
        value = manager.reserve(item_name)
        started.wait(timeout=5)  # оба потока резервируют раньше, чем форматируют
        results[item_name] = manager.format_delivery_text(value)

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("Лот А", "Лот Б")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert results == {"Лот А": "Текст А: A-1", "Лот Б": "Текст Б: B-1"}


def test_set_delivery_text_adds_and_removes(tmp_path):
    manager = make_manager(tmp_path)
    manager.set_delivery_text("Лот А", "Личный: {item}")
    assert manager.format_delivery_text("A-1", "Лот А") == "Личный: A-1"
    manager.set_delivery_text("Лот А", None)
    assert manager.format_delivery_text("A-1", "Лот А") == "Общий текст: A-1"


def test_deliver_uses_lot_template(tmp_path):
    manager = make_manager(tmp_path, {"Лот А": "Личный: {item}"})
    assert manager.deliver("Лот А") == "Личный: A-1"
    assert manager.deliver("Лот Б") == "Общий текст: B-1"
