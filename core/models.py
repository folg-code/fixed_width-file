import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import ClassVar, Dict, Any, List, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from core.const import FILE_STRUCTURE, ALLOWED_CURRENCIES, LINE_LENGTH, READONLY_FIELDS
from core.errors import HeaderValidationError, TransactionValidationError, FooterValidationError, LineLengthMismatch, \
    InvalidRecordIndexError, MaxTransactionLimitError, AmountTooLargeError, AtomicUpdateError, ValidationError, \
    ReadOnlyFieldUpdateError

logger = logging.getLogger(__name__)


class FixedWidthRecord(BaseModel):
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

    @classmethod
    def read_line(cls, line: str) -> Tuple["FixedWidthRecord", List[str]]:
        errors: List[str] = []
        if len(line) != LINE_LENGTH:
            errors.append(f"{cls.__name__} line length mismatch: expected {LINE_LENGTH}, got {len(line)}")
            defaults = {fname: finfo.get("value", "") for fname, finfo in cls.FIELD_DEF.items()}
            obj = cls.model_construct(**defaults)
            return obj, errors

        start = 0
        data: Dict[str, Any] = {}
        for fname, finfo in cls.FIELD_DEF.items():
            width = finfo["width"]
            raw = line[start:start+width]
            start += width
            if "value" in finfo:
                got = raw.strip()
                expected = finfo["value"]
                if got != expected:
                    errors.append(f"{cls.__name__}.{fname}: expected '{expected}', got '{got}'")
                data[fname] = expected
            else:
                data[fname] = raw.strip()
        try:
            obj = cls(**data)
        except Exception as e:
            errors.append(f"{cls.__name__} instantiation error: {e}")
            obj = cls.model_construct(**data)
        return obj, errors

    def write_line(self) -> str:
        parts: List[str] = []
        for fname, finfo in self.FIELD_DEF.items():
            width = finfo["width"]
            if "value" in finfo:
                parts.append(str(finfo["value"]).ljust(width)[:width])
                continue

            val = getattr(self, fname)
            ftype = finfo.get("type", "str")
            if ftype == "int":
                s = str(int(val)).zfill(width)
            elif ftype == "decimal":
                cents = int((Decimal(val) * 100).to_integral_value())
                s = str(cents).zfill(width)
            else:
                s = str(val).ljust(width)[:width]
            parts.append(s)

        line = "".join(parts)
        if len(line) != LINE_LENGTH:
            raise LineLengthMismatch(f"{self.__class__.__name__} line length mismatch: expected {LINE_LENGTH}, got {len(line)}")
        return line

    @classmethod
    def coerce_int(cls, v, field_name: str):
        if v is None or v == "":
            return 0
        return int(v)

    @classmethod
    def coerce_decimal(cls, v, field_name: str):
        if isinstance(v, Decimal):
            return v
        s = str(v).strip()
        if s == "":
            return Decimal(0)
        return Decimal(int(s)) / Decimal(100)

    def validate_fields_length(self) -> List[str]:
        errs = []
        for fname, finfo in self.FIELD_DEF.items():
            val = getattr(self, fname)
            if len(str(val)) > finfo["width"]:
                errs.append(f"{fname}: length {len(str(val))} > {finfo['width']}")
        return errs

class Header(FixedWidthRecord):
    FIELD_DEF: ClassVar[dict] = FILE_STRUCTURE["header"]
    field_id: str = Field(FILE_STRUCTURE["header"]["field_id"]["value"])
    name: str = Field("")
    surname: str = Field("")
    patronymic: str = Field("")
    address: str = Field("")

    @model_validator(mode="after")
    def business_validate(self):
        errs = []
        if not self.name:
            errs.append("Header: name is empty")
        if not self.surname:
            errs.append("Header: surname is empty")
        flen = self.validate_fields_length()
        if flen:
            errs.extend(flen)
        if errs:
            raise HeaderValidationError("; ".join(errs))
        return self


class Transaction(FixedWidthRecord):
    FIELD_DEF: ClassVar[dict] = FILE_STRUCTURE["transaction"]
    field_id: str = Field(FILE_STRUCTURE["transaction"]["field_id"]["value"])
    counter: int = Field(0)
    amount: Decimal = Field(Decimal("0.00"))
    currency: str = Field("")
    reserved: str = Field("")

    @field_validator("counter", mode="before")
    def _coerce_counter(cls, v):
        return cls.coerce_int(v, "counter")

    @field_validator("amount", mode="before")
    def _coerce_amount(cls, v):
        return cls.coerce_decimal(v, "amount")

    @model_validator(mode="after")
    def business_validate(self):
        errs = []
        flen = self.validate_fields_length()
        if flen:
            errs.extend(flen)
        if self.counter <= 0:
            errs.append("Transaction counter <= 0")
        if not isinstance(self.amount, Decimal) or self.amount <= 0:
            errs.append(f"Transaction amount must be positive: {self.amount}")
        if self.currency not in ALLOWED_CURRENCIES:
            errs.append(f"Transaction currency '{self.currency}' not allowed")
        if errs:
            raise TransactionValidationError("; ".join(errs))
        return self


class Footer(FixedWidthRecord):
    FIELD_DEF: ClassVar[dict] = FILE_STRUCTURE["footer"]
    field_id: str = Field(FILE_STRUCTURE["footer"]["field_id"]["value"])
    total_cnt: int = Field(0)
    control_sum: Decimal = Field(Decimal("0.00"))
    reserved: str = Field("")

    @field_validator("total_cnt", mode="before")
    def _coerce_total_cnt(cls, v):
        return cls.coerce_int(v, "total_cnt")

    @field_validator("control_sum", mode="before")
    def _coerce_control_sum(cls, v):
        return cls.coerce_decimal(v, "control_sum")

    @model_validator(mode="after")
    def business_validate(self):
        errs = []
        flen = self.validate_fields_length()
        if flen:
            errs.extend(flen)
        if self.total_cnt < 0:
            errs.append("Footer total_cnt < 0")
        if self.control_sum < 0:
            errs.append("Footer control_sum < 0")
        if errs:
            raise FooterValidationError("; ".join(errs))
        return self

class FixedWidthFile:
    def __init__(self, header: Header, transactions: List[Transaction], footer: Footer):
        self.header = header
        self.transactions = transactions
        self.footer = footer
        self._read_errors: Dict[str, Any] = {"header": [], "transactions": [], "footer": []}

    @property
    def total_cnt(self) -> int:
        return len(self.transactions)

    @property
    def control_sum(self) -> Decimal:
        return sum((t.amount for t in self.transactions), Decimal(0))

    @classmethod
    def read_file(cls, path: str) -> "FixedWidthFile":
        try:
            lines = cls._read_lines(path)
        except Exception as e:
            logger.exception("Cannot read file %s", path)
            raise

        if len(lines) < 2:
            raise ValueError("File too short")

        read_errs = {"header": [], "transactions": [], "footer": []}

        header_obj, header_errs = cls._parse_header(lines[0])
        read_errs["header"].extend(header_errs)

        footer_obj, footer_errs = cls._parse_footer(lines[-1])
        read_errs["footer"].extend(footer_errs)

        txs, tx_errs = cls._parse_transactions(lines[1:-1])
        read_errs["transactions"].extend(tx_errs)

        fw = cls(header_obj, txs, footer_obj)
        fw._read_errors = read_errs

        if any(read_errs.values()):
            logger.warning("File loaded with read/parse errors")
        else:
            logger.info("File loaded OK")

        return fw

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        with open(path, "r", encoding="utf-8", newline=None) as fh:
            return [ln.rstrip("\r\n") for ln in fh]

    @staticmethod
    def _parse_header(line: str) -> tuple[Header, list[str]]:
        try:
            obj, errs = Header.read_line(line)
        except Exception as e:
            obj, errs = None, [str(e)]
        return obj, errs

    @staticmethod
    def _parse_footer(line: str) -> tuple[Footer, list[str]]:
        try:
            obj, errs = Footer.read_line(line)
        except Exception as e:
            obj, errs = None, [str(e)]
        return obj, errs

    @staticmethod
    def _parse_transactions(lines: list[str]) -> tuple[list[Transaction], list[tuple[int, list[str]]]]:
        txs = []
        errs: list[tuple[int, list[str]]] = []
        for idx, ln in enumerate(lines, start=1):
            try:
                obj, e = Transaction.read_line(ln)
                txs.append(obj)
                if e:
                    errs.append((idx, e))
            except Exception as ex:
                errs.append((idx, [str(ex)]))
                txs.append(Transaction(counter=0, amount=Decimal(0), currency="", reserved=""))
        return txs, errs

    def _validate_header(self) -> List[str]:
        errs: List[str] = []
        if self.header is None:
            errs.append("Header: missing or invalid")
        else:
            try:
                self.header.business_validate()
            except HeaderValidationError as e:
                errs.append(str(e))
        return errs

    def _validate_transactions(self) -> List[str]:
        errs: List[str] = []
        for i, tx in enumerate(self.transactions, start=1):
            try:
                tx.business_validate()
            except TransactionValidationError as e:
                errs.append(f"Transaction {i}: {e}")
        return errs

    def _validate_footer(self) -> List[str]:
        errs: List[str] = []
        if self.footer is None:
            errs.append("Footer: missing or invalid")
        else:
            try:
                self.footer.business_validate()
            except FooterValidationError as e:
                errs.append(str(e))

            actual_count = len(self.transactions)
            actual_sum = sum((t.amount for t in self.transactions), Decimal(0))
            if getattr(self.footer, "total_cnt", None) != actual_count:
                errs.append(f"Footer total_cnt ({getattr(self.footer,'total_cnt')}) != transaction count ({actual_count})")
            if getattr(self.footer, "control_sum", None) != actual_sum:
                errs.append(f"Footer control_sum ({getattr(self.footer,'control_sum')}) != transaction sum ({actual_sum})")
        return errs

    def _append_read_errors(self, errors: List[str]) -> None:
        if not hasattr(self, "_read_errors"):
            return
        re = self._read_errors
        for err in re.get("header", []):
            errors.append(f"Header: {err}")
        for idx, tx_errs in re.get("transactions", []):
            for e in tx_errs:
                errors.append(f"Transaction {idx}: {e}")
        for err in re.get("footer", []):
            errors.append(f"Footer: {err}")

    def validate(self, verbose: bool = True) -> List[str]:
        errors: List[str] = []
        errors.extend(self._validate_header())
        errors.extend(self._validate_transactions())
        errors.extend(self._validate_footer())
        self._append_read_errors(errors)

        if verbose:
            if errors:
                print("ERRORS:")
                for e in errors:
                    print(" -", e)
            else:
                print("NO ERRORS.")

        return errors

    def write_file(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(self.header.write_line() + "\n")
                for t in self.transactions:
                    fh.write(t.write_line() + "\n")
                fh.write(self.footer.write_line() + "\n")
            logger.info("File saved: %s", path)
        except Exception as e:
            logger.exception("Failed to write file %s", path)
            raise

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

            field_len_errors = obj.validate_fields_length()
            if field_len_errors:
                raise AtomicUpdateError(
                    f"Field length validation failed: {field_len_errors}"
                )

            try:
                obj.business_validate()
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
        if not self.footer:
            raise ValueError("Footer record is missing")
        self.footer.total_cnt = len(self.transactions)
        self.footer.control_sum = sum(t.amount for t in self.transactions)


    @classmethod
    def create_empty(cls, name="", surname="", patronymic="", address=""):
        header = Header(
            name=name, surname=surname, patronymic=patronymic, address=address)
        footer = Footer(
            total_cnt=0, control_sum=Decimal(0), reserved="")
        logger.info("Created empty FixedWidthFile")
        return cls(header=header, transactions=[], footer=footer)
