import os
from decimal import Decimal, ROUND_HALF_UP

from core.const import READONLY_FIELDS, Colors
from core.models import FixedWidthFile, logger, Header, Footer
from ui.selection import select_currency, select_field, select_record



# ---------------- CREATE ----------------
def create_file():
    print(Colors.CYAN.value + "Create file..." + Colors.RESET.value)
    path = input("File path: ").strip()
    if os.path.exists(path):
        if input("File exists. Overwrite? (y/n): ") != "y":
            print(Colors.YELLOW.value + "Cancelled." + Colors.RESET.value)
            return
    print("Set Header:")
    name = input("Name: ").strip()
    surname = input("Surname: ").strip()
    patronymic = input("Patronymic: ").strip()
    address = input("Address: ").strip()

    fw = FixedWidthFile(
        header=Header(
            name=name,
            surname=surname,
            patronymic=patronymic,
            address=address
        ),
        transactions=[],
        footer=Footer(
            total_cnt=0,
            control_sum=Decimal("0.00"),
            reserved=""
        ),
    )
    try:
        fw.write_file(path)
    except Exception as e:
        print(Colors.RED.value+ f"Failed to create file: {e}" + Colors.RESET.value)
        logger.exception("Failed to create file %s", path)
        return

    print(Colors.GREEN.value + "A new file has been created." + Colors.RESET.value)
    return fw, path


def add_transaction(fw: FixedWidthFile):
    try:
        amount_str = input("Amount (e.g. 123.45): ").strip()
        amount = Decimal(amount_str)
    except Exception as e:
        print(Colors.RED.value+ f"Invalid amount '{amount_str}': {e}" + Colors.RESET.value)
        logger.warning("Invalid amount input: %s (%s)", amount_str, e)
        return

    currency = select_currency()
    if currency is None:
        return

    try:
        fw.add_transaction(amount, currency)
        print(Colors.GREEN.value + f"Transaction added ({currency})." + Colors.RESET.value)
        logger.info(
            "Transaction added: counter=%d amount=%s currency=%s",
            fw.transactions[-1].counter, amount, currency
        )
    except ValueError as e:
        print(Colors.RED.value+ f"Validation failed: {e}" + Colors.RESET.value)
        logger.warning("Validation failed adding transaction: %s", e)
    except Exception as e:
        print(Colors.RED.value+ "Unexpected error." + Colors.RESET.value)
        logger.exception("Unexpected error adding transaction: %s", e)


# ---------------- READ ----------------
def get_field(fw: FixedWidthFile):
    idx = select_record(fw)
    if idx is None:
        return


    if idx == 0:
        fields = list(fw.header.model_fields.keys())
    elif idx == -1:
        fields = list(fw.footer.model_fields.keys())
    else:
        fields = list(fw.transactions[0].model_fields.keys())

    field = select_field(fields)
    if not field:
        return

    try:
        val = fw.get_record(idx, field)
        print(Colors.CYAN.value + f"{field} = {val}" + Colors.RESET.value)
    except Exception as e:
        print(Colors.RED.value+ f"Error reading field '{field}': {e}." + Colors.RESET.value)
        logger.exception("Error reading record %s[%s]: %s", idx, field, e)


def list_transactions(fw: FixedWidthFile, page_size: int = 10):
    if not fw.transactions:
        print(Colors.YELLOW.value + "No transactions." + Colors.RESET.value)
        return

    total = len(fw.transactions)
    pages = (total + page_size - 1) // page_size

    print_header = (
        Colors.CYAN.value +
        f"{'field_id':>8} {'counter':>7} {'amount':>15} {'currency':>8} {'reserved':<60}" +
        Colors.RESET.value
    )

    page = 0
    while True:
        start = page * page_size
        end = min(start + page_size, total)

        print()
        print(Colors.YELLOW.value + f"TRANSACTION — page {page+1}/{pages}" + Colors.RESET.value)
        print(print_header)

        for t in fw.transactions[start:end]:
            counter_str = str(t.counter).zfill(6)
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

        print(Colors.YELLOW.value + f"-- Page {page+1}/{pages} — records {start+1}-{end} of {total} --" + Colors.RESET.value)

        if pages == 1:
            break

        cmd = input("n=next, p=prev, q=quit > ").strip().lower()
        if cmd == "n":
            if page < pages - 1:
                page += 1
            else:
                print(Colors.YELLOW.value + "Already last page." + Colors.RESET.value)
        elif cmd == "p":
            if page > 0:
                page -= 1
            else:
                print(Colors.YELLOW.value + "Already first page." + Colors.RESET.value)
        elif cmd in ("q", ""):
            break
        else:
            print(Colors.RED.value+ "Unknown command." + Colors.RESET.value)


# ---------------- UPDATE ----------------
def set_field(fw: FixedWidthFile):
    idx = select_record(fw)
    if idx is None:
        return

    if idx == 0:
        obj = fw.header
        readonly = READONLY_FIELDS["header"]
    elif idx == -1:
        obj = fw.footer
        readonly = READONLY_FIELDS["footer"]
    else:
        obj = fw.transactions[idx - 1]
        readonly = READONLY_FIELDS["txn"]

    editable_fields = [f for f in obj.model_fields if f not in readonly]

    print("Edit mode:")
    print("1. Single field")
    print("2. Full record")
    mode = input("> ").strip()
    if mode not in ("1", "2"):
        print(Colors.RED.value+ "Invalid mode." + Colors.RESET.value)
        return

    # ===== Full record =====
    if mode == "2":
        updates = {}
        print(Colors.YELLOW.value + "Editing full record (ENTER to skip a field)." + Colors.RESET.value)
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
            print(Colors.YELLOW.value + "No changes." + Colors.RESET.value)
            return

        try:
            fw.set_record(idx, updates)
            print(Colors.GREEN.value + "Record updated." + Colors.RESET.value)
        except Exception as e:
            print(Colors.RED.value+ "Failed to update record." + Colors.RESET.value)
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
        print(Colors.GREEN.value + f"Field '{field}' updated." + Colors.RESET.value)
    except ValueError as e:
        print(Colors.RED.value+ f"Invalid value: {e}" + Colors.RESET.value)
        logger.warning("Updating record %s[%s] failed: %s", idx, field, e)
    except Exception as e:
        print(Colors.RED.value+ "Unexpected error." + Colors.RESET.value)
        logger.exception("Updating record %s[%s] failed: %s", idx, field, e)


# ---------------- DELETE ----------------
def delete_transaction(fw: FixedWidthFile):
    if not fw.transactions:
        print(Colors.YELLOW.value + "No transactions to delete." + Colors.RESET.value)
        return

    for i, tx in enumerate(fw.transactions, 1):
        print(f"{i}: counter={tx.counter}, amount={tx.amount}, currency={tx.currency}")

    try:
        idx_str = input(f"Select transaction id (1-{len(fw.transactions)}): ").strip()
        idx = int(idx_str)
        fw.delete_record(idx)
        print(Colors.GREEN.value + f"Transaction {idx} deleted." + Colors.RESET.value)
    except ValueError as e:
        print(Colors.RED.value+ f"Invalid transaction id: {e}" + Colors.RESET.value)
        logger.warning("Invalid transaction id input: %s (%s)", idx_str, e)
    except Exception as e:
        print(Colors.RED.value+ "Unexpected error." + Colors.RESET.value)
        logger.exception("Unexpected error deleting transaction: %s", e)
