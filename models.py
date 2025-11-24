import logging

import const
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from const import ALLOWED_CURRENCIES, C

logger = logging.getLogger(__name__)

def validate_field_length(value: str, width: int, field_name: str):
    if len(value) > width:
        logger.warning(
            "Walidacja nie powiodła się dla pola '%s': %d > %d",
            field_name, len(value), width
        )
        raise ValueError(
            f"Wartość pola '{field_name}' jest za długa ({len(value)} > {width})"
        )

def right_pad_field(value: str, width: int) -> str:
    s = "" if value is None else str(value)
    if len(s) > width:
        return s[:width]
    return s.rjust(width)

def read_text_field(raw: str) -> str:
    return raw.lstrip()

def format_amount(dec: Decimal) -> str:
    q = dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cents = int((q * 100).to_integral_value())
    return str(cents).zfill(12)

def parse_amount(raw: str) -> Decimal:
    # raw like '000000002000' -> Decimal('20.00')
    if not raw.isdigit():
        raise ValueError("Amount contains non-digit chars")
    cents = int(raw)
    return Decimal(cents) / Decimal(100)

"""def read_line(line, type):

    datasource = mapping[type]

    for .....

    return setattr
"""
@dataclass
class Header:
    field_id: str = const.HEADER_FIELD_ID
    name: str = ""
    surname: str = ""
    patronymic: str = ""
    address: str = ""

    def __post_init__(self):
        self.validate_fields()

    def validate_fields(self):
        validate_field_length(self.name, const.HEADER_NAME_WIDTH, "name")
        validate_field_length(self.surname, const.HEADER_SURNAME_WIDTH, "surname")
        validate_field_length(self.patronymic, const.HEADER_PATRONYMIC_WIDTH, "patronymic")
        validate_field_length(self.address, const.HEADER_ADDRESS_WIDTH, "address")

    @classmethod
    def read_line(cls, line: str):
        errors = []
        if len(line) != const.LINE_LENGTH:
            errors.append(f"Header line length mismatch: {len(line)}")
        fid = line[0:2]
        if fid != cls.field_id:
            errors.append(f"Header field_id '{fid}' niezgodne z '01'")
        h = cls(
            name=read_text_field(line[2:30]),
            surname=read_text_field(line[30:60]),
            patronymic=read_text_field(line[60:90]),
            address=read_text_field(line[90:120])
        )
        return h, errors

    def write_line(self) -> str:
        parts = [
            self.field_id,
            right_pad_field(self.name, 28),
            right_pad_field(self.surname, 30),
            right_pad_field(self.patronymic, 30),
            right_pad_field(self.address, 30),
        ]
        line = "".join(parts)
        if len(line) != const.LINE_LENGTH:
            raise AssertionError("Header line length mismatch")
        return line

    def validate(self):
        errors = []
        if not self.name:
            errors.append("Header: name jest pusty")
        if not self.surname:
            errors.append("Header: surname jest pusty")
        return errors

@dataclass
class Transaction:
    field_id: str = "02"
    counter: int = 1
    amount: Decimal = Decimal(0)
    currency: str = ""
    reserved: str = ""

    def __post_init__(self):
        self.validate_fields()

    def validate_fields(self):
        # Walidacja counter
        if not isinstance(self.counter, int) or self.counter <= 0:
            raise ValueError(f"Transaction counter '{self.counter}' musi być liczbą całkowitą > 0")

        # Walidacja amount
        if self.amount < 0:
            raise ValueError(f"Transaction amount '{self.amount}' nie może być ujemna")
        str_amount = str(int(self.amount * 100))
        if len(str_amount) > 12:
            raise ValueError(f"Amount '{self.amount}' za duży, max 12 cyfr w centach")

        amount_rounded = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if self.amount != amount_rounded:
            raise ValueError(f"Transaction amount '{self.amount}' może mieć maks. 2 miejsca po przecinku")

        # Currency i reserved
        validate_field_length(self.currency, 3, "currency")
        validate_field_length(self.reserved, 110, "reserved")


    @classmethod
    def read_line(cls, line: str):
        errors = []
        if len(line) != const.LINE_LENGTH:
            errors.append(f"Transaction line length mismatch: {len(line)}")
            return cls(counter=0, amount=Decimal(0), currency="ERR", reserved=""), errors
        fid = line[0:2]
        if fid != cls.field_id:
            errors.append(f"Transaction field_id '{fid}' niezgodne z '02'")
        try:
            counter = int(line[2:8])
        except Exception:
            counter = 0
            errors.append("Transaction counter nie jest liczbą")
        try:
            amount = parse_amount(line[8:20])
        except Exception:
            amount = Decimal(0)
            errors.append("Transaction amount niepoprawny")
        currency = read_text_field(line[20:23])
        if currency not in ALLOWED_CURRENCIES:
            errors.append(f"Transaction currency '{currency}' nie należy do ALLOWED_CURRENCIES")
        reserved = read_text_field(line[23:120])
        return cls(counter=counter, amount=amount, currency=currency, reserved=reserved), errors

    def write_line(self) -> str:
        parts = [
            self.field_id,
            str(self.counter).zfill(6),
            format_amount(self.amount),
            right_pad_field(self.currency, 3),
            right_pad_field(self.reserved, 97),
        ]
        line = "".join(parts)
        if len(line) != const.LINE_LENGTH:
            raise AssertionError("Transaction line length mismatch")
        return line

    def validate(self):
        errors = []
        if self.counter <= 0:
            errors.append("Transaction counter <= 0")
        if self.amount < 0:
            errors.append("Transaction amount < 0")
        if self.currency not in ALLOWED_CURRENCIES:
            errors.append(f"Transaction currency '{self.currency}' niepoprawna")
        return errors

@dataclass
class Footer:
    field_id: str = "03"
    total_counter: int = 0
    control_sum: Decimal = Decimal(0)
    reserved: str = ""

    def __post_init__(self):
        self.validate_fields()

    def validate_fields(self):
        validate_field_length(self.reserved, 100, "reserved")

    @classmethod
    def read_line(cls, line: str):
        errors = []
        if len(line) != const.LINE_LENGTH:
            errors.append(f"Footer line length mismatch: {len(line)}")
            return cls(0, Decimal(0), ""), errors
        fid = line[0:2]
        if fid != cls.field_id:
            errors.append(f"Footer field_id '{fid}' niezgodne z '03'")
        try:
            total_counter = int(line[2:8])
        except Exception:
            total_counter = 0
            errors.append("Footer total_counter niepoprawny")
        try:
            control_sum = parse_amount(line[8:20])
        except Exception:
            control_sum = Decimal(0)
            errors.append("Footer control_sum niepoprawny")
        reserved = read_text_field(line[20:120])
        return cls(reserved=reserved), errors

    def write_line(self) -> str:
        """Zwraca linię fixed-width z podanymi total_counter i control_sum."""
        parts = [
            self.field_id,
            str(self.total_counter).zfill(6),
            format_amount(self.control_sum),
            right_pad_field(self.reserved, 100),
        ]
        line = "".join(parts)
        if len(line) != const.LINE_LENGTH:
            raise AssertionError("Footer line length mismatch")
        return line

    def validate(self, total_counter: int, control_sum: Decimal):
        errors = []
        if total_counter < 0:
            errors.append("Footer total_counter < 0")
        if control_sum < 0:
            errors.append("Footer control_sum < 0")
        return errors

class FixedWidthFile:
    def __init__(self, header: Header, transactions: list[Transaction], footer: Footer):
        self.header = header
        self.transactions = transactions
        self.footer = footer

    @property
    def total_counter(self) -> int:
        return len(self.transactions)

    @property
    def control_sum(self) -> Decimal:
        return sum(t.amount for t in self.transactions)

    @classmethod
    def read_file(cls, path: str):
        try:
            with open(path, "r", newline=None) as f:
                lines = [line.rstrip("\r\n") for line in f]
        except Exception as e:
            logger.exception("Błąd odczytu pliku %s", path)
            raise

        if len(lines) < 2:
            raise ValueError("File too short")

        header, _ = Header.read_line(lines[0])
        footer, _ = Footer.read_line(lines[-1])
        transactions = [Transaction.read_line(l)[0] for l in lines[1:-1]]

        fw = cls(header, transactions, footer)

        errors = fw.validate(verbose=False)
        if errors:
            for e in errors:
                logger.warning(e)
            logger.warning("Plik wczytany, ale znaleziono błędy walidacji")
        else:
            logger.info("Plik wczytany poprawnie")

        return fw

    def write_file(self, path: str):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(self.header.write_line() + "\n")
                for t in self.transactions:
                    f.write(t.write_line() + "\n")
                f.write(self.footer.write_line() + "\n")
            logger.info("Plik zapisano poprawnie: %s", path)
        except Exception as e:
            logger.exception("Nie udało się zapisać pliku %s", path)
            raise

    def get_record(self, record_index: int, field_name: str):
        if record_index == 0:
            val = getattr(self.header, field_name)
        elif record_index == -1:
            val = getattr(self.footer, field_name)
        else:
            val = getattr(self.transactions[record_index - 1], field_name)
        logger.info("Odczyt rekordu %s[%s] = %s", record_index, field_name, val)
        return val

    def set_record(self, record_index: int, field_name: str, value):
        if record_index == 0:  # Header
            old_value = getattr(self.header, field_name)
            setattr(self.header, field_name, value)
            try:
                self.header.validate_fields()
            except ValueError as e:
                setattr(self.header, field_name, old_value)  # przywracamy starą wartość
                logger.warning("Header[%s] validation failed: %s", field_name, e)
                raise

        elif record_index == -1:  # Footer
            old_value = getattr(self.footer, field_name)
            setattr(self.footer, field_name, value)
            try:
                self.footer.validate_fields()
            except ValueError as e:
                setattr(self.footer, field_name, old_value)
                logger.warning("Footer[%s] validation failed: %s", field_name, e)
                raise

        else:  # Transaction
            tx = self.transactions[record_index - 1]
            old_value = getattr(tx, field_name)
            if field_name == "amount":
                try:
                    new_amount = Decimal(value)
                except Exception:
                    logger.warning("Nieprawidłowa kwota: %s", value)
                    raise ValueError(f"Nieprawidłowa wartość amount: {value}")
                tx.amount = new_amount
            elif field_name == "counter":
                tx.counter = int(value)
            else:
                setattr(tx, field_name, value)
            try:
                tx.validate_fields()
            except ValueError as e:
                setattr(tx, field_name, old_value)
                logger.warning("Transaction %d[%s] validation failed: %s", tx.counter, field_name, e)
                raise

        self.recalculate_footer()
        logger.info(
            "Record updated: index=%s field=%s old=%s new=%s",
            record_index, field_name, old_value, value
        )

    def add_transaction(self, amount: Decimal, currency: str, reserved: str = ""):
        next_counter = 1 + (self.transactions[-1].counter if self.transactions else 0)
        if next_counter > 20000:
            logger.error("Maximum number of transactions reached")
            raise ValueError("Maximum number of transactions reached (20000)")

        tx = Transaction(counter=next_counter, amount=amount, currency=currency, reserved=reserved)
        try:
            tx.validate_fields()
        except ValueError as e:
            logger.warning(
                "Transaction %d validation failed: %s. Transaction not added.",
                next_counter, e
            )
            raise

        self.transactions.append(tx)
        self.recalculate_footer()
        logger.info(
            "Transaction added: counter=%d amount=%s currency=%s",
            next_counter, amount, currency
        )

    def delete_record(self, record_index: int):

        if record_index <= 0 or record_index > len(self.transactions):
            logger.error("Nie można usunąć rekordu %s – tylko transakcje 1..%s", record_index, len(self.transactions))
            raise ValueError("Niepoprawny indeks rekordu do usunięcia")

        tx = self.transactions.pop(record_index - 1)
        self.recalculate_footer()
        logger.info(
            "Usunięto rekord %s: counter=%s, amount=%s, currency=%s, reserved='%s'",
            record_index, tx.counter, tx.amount, tx.currency, tx.reserved
        )

    def recalculate_footer(self):
        self.footer.total_counter = len(self.transactions)
        self.footer.control_sum = sum(t.amount for t in self.transactions)

    def validate(self, verbose=True):
        errors = []
        errors.extend(self.header.validate())
        for i, tx in enumerate(self.transactions, start=1):
            tx_errors = tx.validate()
            for e in tx_errors:
                errors.append(f"Transaction {i}: {e}")
        errors.extend(self.footer.validate(self.total_counter, self.control_sum))

        if verbose:
            if errors:
                print(C.R + "Błędy walidacji:" + C.RESET)
                for e in errors:
                    print(C.R + " - " + e + C.RESET)
            else:
                print(C.G + "Plik jest poprawny." + C.RESET)

        return errors

    @classmethod
    def create_empty(cls, name="", surname="", patronymic="", address=""):
        header = Header(name=name, surname=surname, patronymic=patronymic, address=address)
        footer = Footer(reserved="")
        logger.info("Utworzono pusty plik FixedWidthFile")
        return cls(header=header, transactions=[], footer=footer)