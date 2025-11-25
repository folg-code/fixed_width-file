import pytest
from decimal import Decimal

from core.errors import AtomicUpdateError
from core.models import (
    Header, Transaction, Footer, FixedWidthFile,
    LineLengthMismatch, HeaderValidationError,
    TransactionValidationError, FooterValidationError,
    ReadOnlyFieldUpdateError, InvalidRecordIndexError,
    AmountTooLargeError, MaxTransactionLimitError
)

def test_header_default_values():
    h = Header(name="Jan", surname="Kowalski")
    assert h.name == "Jan"
    assert h.surname == "Kowalski"
    assert isinstance(h.field_id, str)

def test_transaction_default_values():
    tx = Transaction(counter="5", amount="1000", currency="PLN")
    # coerce_types powinno wykonać się w __post_init__
    assert isinstance(tx.counter, int)
    assert tx.counter == 5
    assert isinstance(tx.amount, Decimal)
    assert tx.amount == Decimal("10.00")  # 1000 groszy -> 10.00
    assert tx.currency == "PLN"

def test_footer_default_values():
    f = Footer(total_counter=0, control_sum=Decimal(0))
    assert f.total_counter == 0
    assert f.control_sum == Decimal(0)

def test_header_validation_missing_fields():
    h = Header(name="", surname="")
    with pytest.raises(HeaderValidationError):
        h.validate()

def test_transaction_validation_invalid_currency():
    tx = Transaction(counter=1, amount=Decimal("10.0"), currency="XXX")
    with pytest.raises(TransactionValidationError):
        tx.validate()

def test_transaction_validation_negative_counter():
    tx = Transaction(counter=0, amount=Decimal("10.0"), currency="PLN")
    with pytest.raises(TransactionValidationError):
        tx.validate()

def test_footer_validation_negative_values():
    f = Footer(total_counter=-1, control_sum=Decimal(-5))
    with pytest.raises(FooterValidationError):
        f.validate()

def make_sample_file():
    h = Header(name="Jan", surname="Kowalski")
    t1 = Transaction(counter=1, amount=Decimal("10.0"), currency="PLN")
    t2 = Transaction(counter=2, amount=Decimal("20.0"), currency="PLN")
    f = Footer(total_counter=2, control_sum=Decimal("30.0"))
    return FixedWidthFile(header=h, transactions=[t1, t2], footer=f)

def test_add_transaction_ok():
    fw = make_sample_file()
    fw.add_transaction(amount=Decimal("15.0"), currency="PLN")
    assert fw.total_counter == 3
    assert fw.control_sum == Decimal("45.0")
    assert fw.transactions[-1].counter == 3

def test_add_transaction_amount_too_large():
    fw = make_sample_file()
    with pytest.raises(AmountTooLargeError):
        fw.add_transaction(amount=Decimal("1000000000000.0"), currency="PLN")

def test_add_transaction_max_limit():
    fw = make_sample_file()
    fw.transactions = [Transaction(counter=i, amount=Decimal("1.0"), currency="PLN") for i in range(1, 20001)]
    with pytest.raises(MaxTransactionLimitError):
        fw.add_transaction(amount=Decimal("1.0"), currency="PLN")

def test_delete_record_ok():
    fw = make_sample_file()
    fw.delete_record(1)
    assert len(fw.transactions) == 1
    assert fw.transactions[0].counter == 1
    assert fw.control_sum == Decimal("20.0")

def test_delete_record_invalid_index():
    fw = make_sample_file()
    with pytest.raises(InvalidRecordIndexError):
        fw.delete_record(0)
    with pytest.raises(InvalidRecordIndexError):
        fw.delete_record(100)

def test_set_record_readonly_field():
    fw = make_sample_file()
    with pytest.raises(ReadOnlyFieldUpdateError):
        fw.set_record(1, {"counter": 5})  # counter jest readonly według READONLY_FIELDS

def test_set_record_atomic_update():
    fw = make_sample_file()
    old_amount = fw.transactions[0].amount
    with pytest.raises(AtomicUpdateError):
        fw.set_record(1, {"amount": "-100"})  # walidacja powinna rzucić, rollback
    # wartość powinna pozostać niezmieniona
    assert fw.transactions[0].amount == old_amount

def test_write_line_length_mismatch(monkeypatch):
    h = Header(name="a"*100, surname="b"*100)
    with pytest.raises(LineLengthMismatch):
        h.write_line()

def test_read_line_invalid_length():
    short_line = "12345"
    from core.models import Transaction
    with pytest.raises(LineLengthMismatch):
        Transaction.read_line(short_line)

def test_validate_full_file():
    fw = make_sample_file()
    errors = fw.validate(verbose=False)
    assert errors == []

def test_validate_full_file_with_errors():
    fw = make_sample_file()
    fw.transactions[0].counter = 0  # złe dane
    errors = fw.validate(verbose=False)
    assert any("Transaction 1" in e for e in errors)