# ----------------------------
# Helper: mock input sequence
# ----------------------------
from decimal import Decimal

from core.models import FixedWidthFile
from handlers import crud
from handlers.crud import delete_transaction, set_field, get_field, list_transactions, add_transaction, create_file
from main import main, edit_menu


class InputMock:
    def __init__(self, inputs):
        self.inputs = inputs
        self.index = 0

    def __call__(self, prompt=""):
        if self.index >= len(self.inputs):
            return ""
        val = self.inputs[self.index]
        self.index += 1
        return val

def test_create_file(monkeypatch, capsys, tmp_path):
    file_path = tmp_path / "testfile.txt"
    inputs = [
        str(file_path),  # file path
        "y",  # overwrite
        "Jan",  # name
        "Kowalski",  # surname
        "Patron",  # patronymic
        "Some address"  # address
    ]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    fw, path = create_file()
    captured = capsys.readouterr()

    assert fw.header.name == "Jan"
    assert fw.header.surname == "Kowalski"
    assert path == str(file_path)
    assert "A new file has been created." in captured.out

def test_add_transaction(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    inputs = [
        "123.45",
        "PLN"
    ]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    monkeypatch.setattr(crud, "select_currency", lambda default=None: "PLN")

    add_transaction(fw)
    captured = capsys.readouterr()

    assert len(fw.transactions) == 1
    tx = fw.transactions[0]
    assert tx.amount == Decimal("123.45")
    assert tx.currency == "PLN"
    assert "Transaction added" in captured.out

def test_list_transactions(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    for i in range(5):
        fw.add_transaction(Decimal(f"{i+1}.00"), "PLN")

    monkeypatch.setattr("builtins.input", InputMock(["n", "n", "q"]))

    list_transactions(fw, page_size=2)
    captured = capsys.readouterr()

    assert "TRANSACTION — page 1" in captured.out
    assert "TRANSACTION — page 2" in captured.out
    assert "TRANSACTION — page 3" in captured.out
    assert "records 1-2 of 5" in captured.out
    assert "records 3-4 of 5" in captured.out
    assert "records 5-5 of 5" in captured.out

def test_get_field(monkeypatch, capsys):
    # Tworzymy pusty plik z headerem
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    inputs = ["0", "2"]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    get_field(fw)

    captured = capsys.readouterr()

    assert "name = Jan" in captured.out


def test_set_field_single(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    inputs = [
        "0",
        "1",
        "1",
        "NewName"
    ]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    set_field(fw)
    captured = capsys.readouterr()

    assert fw.header.name == "NewName"

def test_delete_transaction(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    fw.add_transaction(Decimal("10.00"), "PLN")
    fw.add_transaction(Decimal("20.00"), "PLN")

    inputs = ["1"]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    delete_transaction(fw)
    captured = capsys.readouterr()

    assert len(fw.transactions) == 1
    assert "Transaction 1 deleted." in captured.out

def test_edit_menu_quit(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    inputs = ["0"]  # natychmiast wyjście
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    edit_menu(fw, "dummy_path")
    captured = capsys.readouterr()
    assert "--- EDIT MENU ---" in captured.out

def test_main_quit(monkeypatch, capsys):
    inputs = ["0"]  # natychmiast wyjście
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    main()
    captured = capsys.readouterr()
    assert "=== MENU GŁÓWNE ===" in captured.out
