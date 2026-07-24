"""Тесты файлового склада авто-выдачи: атомарная запись, reserve/restore, секреты вне логов."""
import logging

from playerokapi.autodelivery import AutoDeliveryManager


def make_manager(tmp_path, lines=("SECRET-1", "SECRET-2")):
    stock = tmp_path / "stock.txt"
    stock.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manager = AutoDeliveryManager(config={"Лот": str(stock)}, ledger_path=None)
    return manager, stock


def test_reserve_takes_first_line(tmp_path):
    manager, stock = make_manager(tmp_path)
    assert manager.reserve("Лот") == "SECRET-1"
    assert stock.read_text(encoding="utf-8") == "SECRET-2\n"
    # Атомарная запись не должна оставлять временных файлов рядом со складом.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["stock.txt"]


def test_reserve_empty_stock_returns_none(tmp_path):
    manager, stock = make_manager(tmp_path, lines=())
    stock.write_text("", encoding="utf-8")
    assert manager.reserve("Лот") is None


def test_reserve_unknown_item_returns_none(tmp_path):
    manager, _ = make_manager(tmp_path)
    assert manager.reserve("Несуществующий лот") is None


def test_restore_returns_item_to_head(tmp_path):
    manager, stock = make_manager(tmp_path)
    value = manager.reserve("Лот")
    manager.restore("Лот", value)
    assert stock.read_text(encoding="utf-8") == "SECRET-1\nSECRET-2\n"


def test_get_stock_size(tmp_path):
    manager, _ = make_manager(tmp_path)
    assert manager.get_stock_size("Лот") == 2
    manager.reserve("Лот")
    assert manager.get_stock_size("Лот") == 1
    assert manager.get_stock_size("Несуществующий лот") == 0


def test_deliver_formats_template(tmp_path):
    manager, _ = make_manager(tmp_path)
    manager.delivery_text_template = "Ваш товар: {item}"
    assert manager.deliver("Лот") == "Ваш товар: SECRET-1"


def test_restore_log_does_not_leak_secret(tmp_path, caplog):
    manager, _ = make_manager(tmp_path)
    value = manager.reserve("Лот")
    with caplog.at_level(logging.DEBUG, logger="playerokapi.autodelivery"):
        manager.restore("Лот", value)
    assert "SECRET-1" not in caplog.text
