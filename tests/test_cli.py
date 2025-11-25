# ----------------------------
# Helper: mock input sequence
# ----------------------------
from decimal import Decimal

from core.models import FixedWidthFile
from handlers import crud
from handlers.crud import delete_transaction, set_field, get_field, list_transactions, add_transaction, create_file
from main import main, edit_menu
from ui import selection


class InputMock:
    """Symulacja input() w testach CLI."""
    def __init__(self, inputs):
        self.inputs = inputs
        self.index = 0

    def __call__(self, prompt=""):
        if self.index >= len(self.inputs):
            return ""
        val = self.inputs[self.index]
        self.index += 1
        return val


# ----------------------------
# 1. Test tworzenia nowego pliku
# ----------------------------
def test_create_file(monkeypatch, capsys, tmp_path):
    file_path = tmp_path / "testfile.txt"
    inputs = [
        str(file_path),  # file path
        "y",  # overwrite (nieistotne bo plik nie istnieje)
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


# ----------------------------
# 2. Test dodania transakcji
# ----------------------------
def test_add_transaction(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    # mock input: amount, currency
    inputs = [
        "123.45",  # amount
        "PLN"  # currency
    ]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    # podmiana select_currency w crud
    monkeypatch.setattr(crud, "select_currency", lambda default=None: "PLN")

    add_transaction(fw)
    captured = capsys.readouterr()

    assert len(fw.transactions) == 1
    tx = fw.transactions[0]
    assert tx.amount == Decimal("123.45")
    assert tx.currency == "PLN"
    assert "Transaction added" in captured.out


# ----------------------------
# 3. Test wylistowania transakcji (list_transactions)
# ----------------------------
def test_list_transactions(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    for i in range(5):
        fw.add_transaction(Decimal(f"{i+1}.00"), "PLN")

    # symulujemy page navigation: next, next, quit
    monkeypatch.setattr("builtins.input", InputMock(["n", "n", "q"]))

    list_transactions(fw, page_size=2)
    captured = capsys.readouterr()

    assert "TRANSACTION — page 1" in captured.out
    assert "TRANSACTION — page 2" in captured.out
    assert "TRANSACTION — page 3" in captured.out
    assert "records 1-2 of 5" in captured.out
    assert "records 3-4 of 5" in captured.out
    assert "records 5-5 of 5" in captured.out


# ----------------------------
# 4. Test pobrania pola (get_field)
# ----------------------------
def test_get_field(monkeypatch, capsys):
    # Tworzymy pusty plik z headerem
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    # symulujemy wybór rekordu 0 (Header) i pola "name" (numer 2)
    inputs = ["0", "2"]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    # wywołujemy funkcję CLI
    get_field(fw)

    captured = capsys.readouterr()

    # sprawdzamy, że wyświetlono wartość pola
    assert "name = Jan" in captured.out


# ----------------------------
# 5. Test edycji pola (set_field) single field
# ----------------------------
def test_set_field_single(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")

    # editable_fields dla headera: ['name', 'surname', 'patronymic', 'address']
    # pole 'name' jest pierwsze w tej liście → numer 1 w CLI
    inputs = [
        "0",  # select header
        "1",  # single field
        "1",  # wybór pola 'name'
        "NewName"  # nowa wartość
    ]
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    set_field(fw)
    captured = capsys.readouterr()

    assert fw.header.name == "NewName"


# ----------------------------
# 6. Test usunięcia transakcji
# ----------------------------
def test_delete_transaction(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    fw.add_transaction(Decimal("10.00"), "PLN")
    fw.add_transaction(Decimal("20.00"), "PLN")

    inputs = ["1"]  # wybór pierwszej transakcji do usunięcia
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    delete_transaction(fw)
    captured = capsys.readouterr()

    assert len(fw.transactions) == 1
    assert "Transaction 1 deleted." in captured.out


# ----------------------------
# 7. Test menu edycji (edit_menu) minimal flow
# ----------------------------
def test_edit_menu_quit(monkeypatch, capsys):
    fw = FixedWidthFile.create_empty("Jan", "Kowalski")
    inputs = ["0"]  # natychmiast wyjście
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    edit_menu(fw, "dummy_path")
    captured = capsys.readouterr()
    assert "--- EDIT MENU ---" in captured.out


# ----------------------------
# 8. Test main menu (main) minimal flow
# ----------------------------
def test_main_quit(monkeypatch, capsys):
    inputs = ["0"]  # natychmiast wyjście
    monkeypatch.setattr("builtins.input", InputMock(inputs))

    main()
    captured = capsys.readouterr()
    assert "=== MENU GŁÓWNE ===" in captured.out