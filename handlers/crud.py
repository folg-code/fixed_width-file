import logging
import os
from decimal import Decimal, ROUND_HALF_UP

from core.config_logging import setup_logging
from core.const import  C, READONLY_FIELDS
from core.models import FixedWidthFile, logger, Header, Footer
from ui.selection import select_currency, select_field, select_record

setup_logging()
logger = logging.getLogger(__name__)


# ---------------- CREATE ----------------
def create_file():
    print(C.C + "Create file..." + C.RESET)
    path = input("File path: ").strip()
    if os.path.exists(path):
        if input("File exists. Overwrite? (y/n): ") != "y":
            print(C.Y + "Cancelled." + C.RESET)
            return
    print("Set Header:")
    name = input("Name: ").strip()
    surname = input("Surname: ").strip()
    patronymic = input("Patronymic: ").strip()
    address = input("Address: ").strip()

    fw = FixedWidthFile(
        header=Header(name, surname, patronymic, address),
        transactions=[],
        footer=Footer(0, Decimal("0.00"), ""),
    )
    try:
        fw.write_file(path)
    except Exception as e:
        print(C.R + f"Failed to create file: {e}" + C.RESET)
        logger.exception("Failed to create file %s", path)
        return

    print(C.G + "A new file has been created." + C.RESET)
    return fw, path


def add_transaction(fw: FixedWidthFile):
    try:
        amount_str = input("Amount (e.g. 123.45): ").strip()
        amount = Decimal(amount_str)
    except Exception as e:
        print(C.R + f"Invalid amount '{amount_str}': {e}" + C.RESET)
        logger.warning("Invalid amount input: %s (%s)", amount_str, e)
        return

    currency = select_currency()
    if currency is None:
        return

    try:
        fw.add_transaction(amount, currency)
        print(C.G + f"Transaction added ({currency})." + C.RESET)
        logger.info(
            "Transaction added: counter=%d amount=%s currency=%s",
            fw.transactions[-1].counter, amount, currency
        )
    except ValueError as e:
        print(C.R + f"Validation failed: {e}" + C.RESET)
        logger.warning("Validation failed adding transaction: %s", e)
    except Exception as e:
        print(C.R + "Unexpected error." + C.RESET)
        logger.exception("Unexpected error adding transaction: %s", e)


# ---------------- READ ----------------
def get_field(fw: FixedWidthFile):
    idx = select_record(fw)
    if idx is None:
        return

    # pola zależnie od rekordu
    if idx == 0:
        fields = list(fw.header.__dataclass_fields__.keys())
    elif idx == -1:
        fields = list(fw.footer.__dataclass_fields__.keys())
    else:
        fields = list(fw.transactions[0].__dataclass_fields__.keys())

    field = select_field(fields)
    if not field:
        return

    try:
        val = fw.get_record(idx, field)
        print(C.C + f"{field} = {val}" + C.RESET)
    except Exception as e:
        print(C.R + f"Error reading field '{field}': {e}." + C.RESET)
        logger.exception("Error reading record %s[%s]: %s", idx, field, e)


def list_transactions(fw: FixedWidthFile, page_size: int = 10):
    if not fw.transactions:
        print(C.Y + "No transactions." + C.RESET)
        return

    total = len(fw.transactions)
    pages = (total + page_size - 1) // page_size

    print_header = (
        C.C +
        f"{'field_id':>8} {'counter':>7} {'amount':>15} {'currency':>8} {'reserved':<60}" +
        C.RESET
    )

    page = 0
    while True:
        start = page * page_size
        end = min(start + page_size, total)

        print()
        print(C.Y + f"TRANSACTION — page {page+1}/{pages}" + C.RESET)
        print(print_header)

        for t in fw.transactions[start:end]:
            counter_str = str(t.counter).zfill(6)

            # amount jako Decimal z 2 miejscami
            amt = t.amount
            if not isinstance(amt, Decimal):
                try:
                    amt = Decimal(amt)
                except:
                    amt = Decimal(0)

            amt = amt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            amt_str = f"{amt:.2f}"

            reserved_display = (t.reserved or "")[:58]

            print(
                f"{t.field_id:>8} {counter_str:>7} {amt_str:>15} "
                f"{t.currency:>8} {reserved_display:<60}"
            )

        print(C.Y + f"-- Page {page+1}/{pages} — records {start+1}-{end} of {total} --" + C.RESET)

        if pages == 1:
            break

        cmd = input("n=next, p=prev, q=quit > ").strip().lower()
        if cmd == "n":
            if page < pages - 1:
                page += 1
            else:
                print(C.Y + "Already last page." + C.RESET)
        elif cmd == "p":
            if page > 0:
                page -= 1
            else:
                print(C.Y + "Already first page." + C.RESET)
        elif cmd in ("q", ""):
            break
        else:
            print(C.R + "Unknown command." + C.RESET)


# ---------------- UPDATE ----------------
def set_field(fw: FixedWidthFile):
    idx = select_record(fw)
    if idx is None:
        return

    if idx == 0:
        obj = fw.header
        readonly = READONLY_FIELDS[0]
    elif idx == -1:
        obj = fw.footer
        readonly = READONLY_FIELDS[-1]
    else:
        obj = fw.transactions[idx - 1]
        readonly = READONLY_FIELDS["tx"]

    editable_fields = [f for f in obj.__dataclass_fields__ if f not in readonly]

    print("Edit mode:")
    print("1. Single field")
    print("2. Full record")
    mode = input("> ").strip()
    if mode not in ("1", "2"):
        print(C.R + "Invalid mode." + C.RESET)
        return

    # ===== Full record =====
    if mode == "2":
        updates = {}
        print(C.Y + "Editing full record (ENTER to skip a field)." + C.RESET)
        for f in editable_fields:
            old_val = getattr(obj, f)
            if f == "currency":
                val = select_currency(old_val)
                if val is None:
                    continue
                updates[f] = val
                continue
            val = input(f"{f} [{old_val}]: ").strip()
            if val == "":
                continue
            updates[f] = val

        if not updates:
            print(C.Y + "No changes." + C.RESET)
            return

        try:
            fw.set_record(idx, updates)
            print(C.G + "Record updated." + C.RESET)
        except Exception as e:
            print(C.R + "Failed to update record." + C.RESET)
            logger.exception("Failed updating record %s: %s", idx, e)
        return

    # ===== Single field =====
    field = select_field(editable_fields)
    if not field:
        return

    if field == "currency":
        val = select_currency(getattr(obj, field))
        if val is None:
            return
    else:
        val = input(f"New value [{getattr(obj, field)}]: ").strip()
        if val == "":
            return

    try:
        fw.set_record(idx, {field: val})
        print(C.G + f"Field '{field}' updated." + C.RESET)
    except ValueError as e:
        print(C.R + f"Invalid value: {e}" + C.RESET)
        logger.warning("Updating record %s[%s] failed: %s", idx, field, e)
    except Exception as e:
        print(C.R + "Unexpected error." + C.RESET)
        logger.exception("Updating record %s[%s] failed: %s", idx, field, e)


# ---------------- DELETE ----------------
def delete_transaction(fw: FixedWidthFile):
    if not fw.transactions:
        print(C.Y + "No transactions to delete." + C.RESET)
        return

    for i, tx in enumerate(fw.transactions, 1):
        print(f"{i}: counter={tx.counter}, amount={tx.amount}, currency={tx.currency}")

    try:
        idx_str = input(f"Select transaction id (1-{len(fw.transactions)}): ").strip()
        idx = int(idx_str)
        fw.delete_record(idx)
        print(C.G + f"Transaction {idx} deleted." + C.RESET)
    except ValueError as e:
        print(C.R + f"Invalid transaction id: {e}" + C.RESET)
        logger.warning("Invalid transaction id input: %s (%s)", idx_str, e)
    except Exception as e:
        print(C.R + "Unexpected error." + C.RESET)
        logger.exception("Unexpected error deleting transaction: %s", e)
