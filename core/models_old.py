import logging

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Any

from core.const import (
    ALLOWED_CURRENCIES, READONLY_FIELDS,
    FILE_STRUCTURE, LINE_LENGTH, Colors
)
from core.errors import (
    LineLengthMismatch, FileReadError, FileWriteError,
    InvalidRecordIndexError, ReadOnlyFieldUpdateError,
    AmountTooLargeError, MaxTransactionLimitError,
    AtomicUpdateError, ValidationError, FooterValidationError,
    TransactionValidationError, HeaderValidationError,
    EmptyFileError)

logger = logging.getLogger(__name__)


@dataclass
class FixedWidthRecord:

    def __post_init__(self):
        self.coerce_types([])

    def coerce_types(self, errors: list[str]):

        for fname, finfo in self.FIELD_DEF.items():
            val = getattr(self, fname)
            field_type = finfo.get("type", "str")

            if field_type == "int":
                if isinstance(val, int):
                    continue
                try:
                    coerced = int(str(val).strip()) if str(val).strip() != "" else 0
                    setattr(self, fname, coerced)
                except Exception:
                    msg = f"IntegerCoercionError: {self.__class__.__name__}.{fname}: cannot parse '{val}' as int"
                    errors.append(msg)
                    setattr(self, fname, 0)

            elif field_type == "decimal":
                if isinstance(val, Decimal):
                    continue
                try:
                    sval = str(val).strip()
                    if sval == "":
                        setattr(self, fname, Decimal(0))
                    else:
                        cents = int(sval)
                        setattr(self, fname, Decimal(cents) / Decimal(100))
                except Exception:
                    msg = f"DecimalCoercionError: {self.__class__.__name__}.{fname}: cannot parse '{val}' as decimal (expected cents int)"
                    errors.append(msg)
                    setattr(self, fname, Decimal(0))

            else:
                continue

    @classmethod
    def read_line(cls, line: str):

        errors: List[str] = []
        if len(line) != LINE_LENGTH:
            raise LineLengthMismatch(
                f"{cls.__name__} line length mismatch: expected {LINE_LENGTH}, got {len(line)}"
            )

        start = 0
        field_values: Dict[str, str] = {}
        for fname, finfo in cls.FIELD_DEF.items():
            width = finfo["width"]
            raw = line[start:start + width]
            start += width
            if "value" in finfo:
                value = raw.strip()
                if value != finfo["value"]:
                    errors.append(f"{cls.__name__}.{fname}: expected '{finfo['value']}', got '{value}'")
            else:
                value = raw.strip()
            field_values[fname] = value

        obj = cls(**field_values)
        obj.coerce_types(errors)
        return obj, errors

    def write_line(self) -> str:
        parts = []
        for fname, finfo in self.FIELD_DEF.items():
            val = getattr(self, fname)
            width = finfo["width"]
            field_type = finfo.get("type", "str")

            if "value" in finfo:
                val = finfo["value"]
            elif field_type == "int":
                val = str(int(val)).zfill(width)
            elif field_type == "decimal":
                cents = int((Decimal(val) * 100).to_integral_value())
                val = str(cents).zfill(width)
            else:
                val = str(val).ljust(width)
            parts.append(val)

        line = "".join(parts)
        if len(line) != LINE_LENGTH:
            raise LineLengthMismatch(
                f"{self.__class__.__name__} line length mismatch: expected {LINE_LENGTH}, got {len(line)}")
        return line

    def validate_fields(self):
        errors = []
        for fname, finfo in self.FIELD_DEF.items():
            width = finfo["width"]
            val = getattr(self, fname)
            if len(str(val)) > width:
                errors.append(f"{fname}: length {len(str(val))} > {width}")
        return errors


@dataclass
class Header(FixedWidthRecord):
    FIELD_DEF = FILE_STRUCTURE["header"]
    field_id: str = FILE_STRUCTURE["header"]["field_id"]["value"]
    name: str = ""
    surname: str = ""
    patronymic: str = ""
    address: str = ""

    def validate(self):
        errors = self.validate_fields()
        if not self.name:
            errors.append("Header: name jest pusty")
        if not self.surname:
            errors.append("Header: surname jest pusty")

        if errors:
            raise HeaderValidationError("; ".join(errors))


@dataclass
class Transaction(FixedWidthRecord):
    FIELD_DEF = FILE_STRUCTURE["transaction"]
    field_id: str = FILE_STRUCTURE["transaction"]["field_id"]["value"]
    counter: int = 0
    amount: Decimal = Decimal(0)
    currency: str = ""
    reserved: str = ""

    def validate(self):
        errors = self.validate_fields()
        if self.counter <= 0:
            errors.append("Transaction counter <= 0")
        if self.currency not in ALLOWED_CURRENCIES:
            errors.append(
                f"Transaction currency '{self.currency}' niepoprawna"
            )
        if self.amount <= 0:
            errors.append(
                f"Transaction amount must be positive: {self.amount}"
            )

        if errors:
            raise TransactionValidationError("; ".join(errors))


@dataclass
class Footer(FixedWidthRecord):
    FIELD_DEF = FILE_STRUCTURE["footer"]
    field_id: str = FILE_STRUCTURE["footer"]["field_id"]["value"]
    total_cnt: int = 0
    control_sum: Decimal = Decimal(0)
    reserved: str = ""

    def validate(self):
        errors = self.validate_fields()
        if self.total_cnt < 0:
            errors.append(f"Footer total_cnt < 0: {self.total_cnt}")
        if self.control_sum < 0:
            errors.append(f"Footer control_sum < 0: {self.control_sum}")
        if errors:
            raise FooterValidationError("; ".join(errors))


class FixedWidthFile:
    def __init__(
            self,
            header: Header,
            transactions: List[Transaction],
            footer: Footer
    ) -> None :
        self.header = header
        self.transactions = transactions
        self.footer = footer

    @property
    def total_cnt(self) -> int:
        return len(self.transactions)

    @property
    def control_sum(self) -> Decimal:
        return sum(t.amount for t in self.transactions)

    @classmethod
    def _read_lines(cls, path: str) -> List[str]:
        try:
            with open(path, "r", newline=None, encoding="utf-8") as f:
                return [line.rstrip("\r\n") for line in f]
        except Exception as e:
            logger.exception("Błąd odczytu pliku %s", path)
            raise FileReadError(f"Cannot read file {path}: {e}")

    @classmethod
    def _make_placeholder_tx(cls) -> "Transaction":
        placeholder_vals = {k: "" for k in Transaction.FIELD_DEF.keys()}
        return Transaction(**placeholder_vals)

    @classmethod
    def _parse_header(cls, lines: List[str], read_errors: Dict[str, List[Any]]) -> Any:
        try:
            try:
                header, errors = Header.read_line(lines[0])
                if errors:
                    read_errors["header"].extend(errors)
            except LineLengthMismatch as e:
                read_errors["header"].append(str(e))
                header = None
        except Exception as e:
            read_errors["header"].append(str(e))
            header = None
        return header

    @classmethod
    def _parse_footer(cls, lines: List[str], read_errors: Dict[str, List[Any]]) -> Any:
        try:
            try:
                footer, errors = Footer.read_line(lines[-1])
                if errors:
                    read_errors["footer"].extend(errors)
            except LineLengthMismatch as e:
                read_errors["footer"].append(str(e))
                footer = None
        except Exception as e:
            read_errors["footer"].append(str(e))
            footer = None
        return footer

    @classmethod
    def _parse_transactions(cls, lines: List[str], read_errors: Dict[str, List[Any]]) -> List["Transaction"]:
        transactions: List[Transaction] = []
        for idx, line in enumerate(lines[1:-1], start=1):
            try:
                tx, errors = Transaction.read_line(line)
                transactions.append(tx)
                if errors:
                    read_errors["transactions"].append((idx, errors))
            except LineLengthMismatch as e:
                read_errors["transactions"].append((idx, [str(e)]))
                tx = cls._make_placeholder_tx()
                transactions.append(tx)
            except Exception as e:
                read_errors["transactions"].append((idx, [str(e)]))
                tx = cls._make_placeholder_tx()
                transactions.append(tx)
        return transactions

    @classmethod
    def read_file(cls, path: str):
        _read_errors = {"header": [], "transactions": [], "footer": []}

        lines = cls._read_lines(path)

        if len(lines) < 2:
            raise EmptyFileError(f"File too short: {len(lines)} lines")

        header = cls._parse_header(lines, _read_errors)

        footer = cls._parse_footer(lines, _read_errors)

        transactions = cls._parse_transactions(lines, _read_errors)

        fw = cls(header, transactions, footer)
        fw._read_errors = _read_errors

        if any(_read_errors.values()):
            logger.warning("File loaded, but errors were found in structure/content")
        else:
            logger.info("File loaded successfully (structure OK)")

        return fw

    def validate(self, verbose=True):

        errors = []

        if self.header:
            try:
                self.header.validate()
            except HeaderValidationError as e:
                print("DEBUG HEADER ERROR:", e)
                errors.append(f"Header validation error: {e}")

        for i, tx in enumerate(self.transactions, start=1):
            try:
                tx.validate()
            except TransactionValidationError as e:
                errors.append(f"Transaction {i}: {e}")

        if self.footer:
            try:
                self.footer.validate()
            except FooterValidationError as e:
                errors.append(str(e))
        else:
            errors.append("Footer: missing or invalid")

        if verbose:
            if errors:
                print(Colors.RED.value+ "Data validation errors:" + Colors.RESET.value)
                for e in errors:
                    print(Colors.RED.value+ " - " + e + Colors.RESET.value)
            else:
                print(Colors.GREEN.value + "File data is valid." + Colors.RESET.value)

        return errors

    def write_file(self, path: str):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(self.header.write_line() + "\n")
                for t in self.transactions:
                    f.write(t.write_line() + "\n")
                f.write(self.footer.write_line() + "\n")
            logger.info("File saved successfully: %s", path)
        except Exception as e:
            logger.exception("Failed to save file %s", path)
            raise FileWriteError(f"Cannot write file {path}: {e}")

    def get_record(self, record_index: int, field_name: str):
        if record_index == 0:
            val = getattr(self.header, field_name)
        elif record_index == -1:
            val = getattr(self.footer, field_name)
        else:
            val = getattr(self.transactions[record_index - 1], field_name)
        logger.info("Read record %s[%s] = %s", record_index, field_name, val)
        return val

    def set_record(self, record_index: int, updates: dict):

        if not isinstance(updates, dict) or not updates:
            raise ValueError("updates must be a non-empty dict")

        if record_index == 0:
            obj = self.header
            readonly = READONLY_FIELDS["header"]
        elif record_index == -1:
            obj = self.footer
            readonly = READONLY_FIELDS["footer"]
        else:
            if not (1 <= record_index <= len(self.transactions)):
                raise InvalidRecordIndexError(
                    f"Invalid transaction index: {record_index}"
                )
            obj = self.transactions[record_index - 1]
            readonly = READONLY_FIELDS["txn"]

        for f in updates:
            if f in readonly:
                raise ReadOnlyFieldUpdateError(f"Field '{f}' is read-only")

        old_values = {f: getattr(obj, f) for f in updates}

        try:
            for field, value in updates.items():
                if isinstance(obj, Transaction):
                    if field == "amount":
                        value = Decimal(value)
                    elif field == "counter":
                        value = int(value)

                setattr(obj, field, value)

            field_len_errors = obj.validate_fields()
            if field_len_errors:
                raise AtomicUpdateError(
                    f"Field length validation failed: {field_len_errors}"
                )

            try:
                obj.validate()
            except ValidationError as e:
                raise AtomicUpdateError(
                    f"Business validation failed after update: {e}"
                )

        except AtomicUpdateError:
            for field, old in old_values.items():
                setattr(obj, field, old)
            raise

        except Exception as e:
            for field, old in old_values.items():
                setattr(obj, field, old)
            raise AtomicUpdateError(f"Atomic update failed: {e}")

        if isinstance(obj, Transaction):
            self.recalculate_footer()

        logger.info(
            "Record updated atomically: idx=%s updates=%s",
            record_index, updates
        )

    def add_transaction(
            self,
            amount: Decimal,
            currency: str,
            reserved: str = ""
    ) -> None:
        cents = int((amount * 100).to_integral_value())
        if len(str(abs(cents))) > 12:
            raise AmountTooLargeError(
                "Amount too large: max 12 digits including cents"
            )

        next_counter = 1 + (self.transactions[-1].counter if self.transactions else 0)
        if next_counter > 20000:
            raise MaxTransactionLimitError(
                "Maximum number of transactions reached (20000)"
            )

        tx = Transaction(
            counter=next_counter, amount=amount,
            currency=currency, reserved=reserved
        )
        self.transactions.append(tx)
        self.recalculate_footer()
        logger.info(
            "Transaction added: counter=%d amount=%s currency=%s",
            next_counter, amount, currency
        )

    def delete_record(self, record_index: int):
        if record_index <= 0 or record_index > len(self.transactions):
            logger.error(
                "Cannot delete record %s – only transactions 1..%s are allowed",
                record_index, len(self.transactions),
            )
            raise InvalidRecordIndexError("Invalid record index for deletion")

        tx = self.transactions.pop(record_index - 1)

        for i, t in enumerate(self.transactions, start=1):
            t.counter = i

        self.recalculate_footer()

        logger.info(
            "Record %s deleted: counter=%s, amount=%s, currency=%s, reserved='%s'",
            record_index, tx.counter, tx.amount, tx.currency, tx.reserved,
        )

    def recalculate_footer(self):
        if not hasattr(self, "footer") or self.footer is None:
            raise ValueError("Footer record is missing")

        total_count = len(self.transactions)
        total_amount_cents = 0
        for tx in self.transactions:
            total_amount_cents += int((tx.amount * 100).to_integral_value())
        self.footer.total_cnt = total_count
        self.footer.control_sum = Decimal(total_amount_cents)

        logger.info(
            "Footer recalculated: total_cnt=%d, control_sum=%s",
            self.footer.total_cnt,
            self.footer.control_sum,
        )

    @classmethod
    def create_empty(cls, name="", surname="", patronymic="", address=""):
        header = Header(
            name=name, surname=surname, patronymic=patronymic, address=address)
        footer = Footer(
            total_cnt=0, control_sum=Decimal(0), reserved="")
        logger.info("Created empty FixedWidthFile")
        return cls(header=header, transactions=[], footer=footer)
