"""Тесты блочного (многострочного) формата склада авто-выдачи (разделитель `---`)."""
from playerokapi.autodelivery import AutoDeliveryManager, parse_stock_text, serialize_stock

BLOCK_STOCK = """login1:pass1
рекомендую сменить пароль
---
login2:pass2
инструкция для второго
---
login3:pass3
"""


def make_manager(tmp_path, content):
    stock = tmp_path / "stock.txt"
    stock.write_text(content, encoding="utf-8")
    manager = AutoDeliveryManager(config={"Лот": str(stock)}, ledger_path=None)
    return manager, stock


# ----------------------------------------------------------------------
# parse / serialize
# ----------------------------------------------------------------------

def test_parse_line_mode():
    assert parse_stock_text("a\n\nb\n") == ["a", "b"]


def test_parse_block_mode():
    items = parse_stock_text(BLOCK_STOCK)
    assert len(items) == 3
    assert items[0] == "login1:pass1\nрекомендую сменить пароль"
    assert items[2] == "login3:pass3"


def test_parse_skips_empty_blocks():
    assert parse_stock_text("---\n\n---\nitem\n---\n") == ["item"]


def test_serialize_roundtrip_block():
    items = parse_stock_text(BLOCK_STOCK)
    assert parse_stock_text(serialize_stock(items)) == items


def test_serialize_single_line_items_stay_line_mode():
    text = serialize_stock(["a", "b"])
    assert text == "a\nb\n"


# ----------------------------------------------------------------------
# reserve / restore / size
# ----------------------------------------------------------------------

def test_stock_size_counts_blocks(tmp_path):
    manager, _ = make_manager(tmp_path, BLOCK_STOCK)
    assert manager.get_stock_size("Лот") == 3


def test_reserve_takes_whole_block(tmp_path):
    manager, stock = make_manager(tmp_path, BLOCK_STOCK)
    value = manager.reserve("Лот")
    assert value == "login1:pass1\nрекомендую сменить пароль"
    assert manager.get_stock_size("Лот") == 2
    # Оставшиеся позиции не перемешались.
    assert manager.reserve("Лот") == "login2:pass2\nинструкция для второго"


def test_restore_multiline_item(tmp_path):
    manager, stock = make_manager(tmp_path, BLOCK_STOCK)
    value = manager.reserve("Лот")
    manager.restore("Лот", value)
    assert manager.get_stock_size("Лот") == 3
    assert manager.reserve("Лот") == value  # вернулся в начало


def test_restore_multiline_into_emptied_stock(tmp_path):
    manager, stock = make_manager(tmp_path, "one:two\nтри\n---\n")
    value = manager.reserve("Лот")
    assert manager.get_stock_size("Лот") == 0
    manager.restore("Лот", value)
    assert manager.get_stock_size("Лот") == 1
    assert manager.reserve("Лот") == value


def test_deliver_formats_multiline(tmp_path):
    manager, _ = make_manager(tmp_path, BLOCK_STOCK)
    manager.delivery_text_template = "Ваш товар:\n{item}"
    assert manager.deliver("Лот") == "Ваш товар:\nlogin1:pass1\nрекомендую сменить пароль"


# ----------------------------------------------------------------------
# add_stock (публичное пополнение склада, используется TG-панелью)
# ----------------------------------------------------------------------

def test_add_stock_appends_lines(tmp_path):
    manager, _ = make_manager(tmp_path, "a\n")
    assert manager.add_stock("Лот", "b\n\nc\n") == 2
    assert manager.get_stock_size("Лот") == 3
    assert manager.reserve("Лот") == "a"  # старые позиции выдаются первыми


def test_add_stock_merges_multiline_blocks(tmp_path):
    manager, _ = make_manager(tmp_path, "a\n")
    assert manager.add_stock("Лот", "login:pass\nинструкция\n---\n") == 1
    assert manager.get_stock_size("Лот") == 2
    manager.reserve("Лот")
    assert manager.reserve("Лот") == "login:pass\nинструкция"


def test_add_stock_empty_text_is_noop(tmp_path):
    manager, stock = make_manager(tmp_path, "a\n")
    assert manager.add_stock("Лот", "  \n\n") == 0
    assert stock.read_text(encoding="utf-8") == "a\n"


def test_add_stock_creates_missing_file(tmp_path):
    path = tmp_path / "sub" / "new_stock.txt"
    manager = AutoDeliveryManager(config={"Лот": str(path)}, ledger_path=None)
    assert manager.add_stock("Лот", "x\ny\n") == 2
    assert manager.get_stock_size("Лот") == 2


def test_add_stock_unknown_lot_raises(tmp_path):
    manager, _ = make_manager(tmp_path, "a\n")
    try:
        manager.add_stock("Неизвестный", "x")
    except KeyError:
        pass
    else:
        raise AssertionError("ожидался KeyError для лота без склада")
