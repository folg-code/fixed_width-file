LINE_LENGTH = 120

FILE_STRUCTURE = {
    "header": {
        "field_id": {"width": 2, "value": "01"},
        "name": {"width": 28, "type": "str"},
        "surname": {"width": 30, "type": "str"},
        "patronymic": {"width": 30, "type": "str"},
        "address": {"width": 30, "type": "str"},
    },
    "transaction": {
        "field_id": {"width": 2, "value": "02"},
        "counter": {"width": 6, "type": "int"},
        "amount": {"width": 12, "type": "decimal"},
        "currency": {"width": 3, "type": "str"},
        "reserved": {"width": 97, "type": "str"},  # 120 - sum of previous fields
    },
    "footer": {
        "field_id": {"width": 2, "value": "03"},
        "total_counter": {"width": 6, "type": "int"},
        "control_sum": {"width": 12, "type": "int"},
        "reserved": {"width": 100, "type": "str"},  # 120 - sum of previous fields
    }
}

class C:
    R = "\033[31m" # red
    G = "\033[32m" # green
    Y = "\033[33m" # yellow
    B = "\033[34m" # blue
    M = "\033[35m" # magenta
    C = "\033[36m" # cyan
    W = "\033[37m" # white
    RESET = "\033[0m"

READONLY_FIELDS = {
    0: ["field_id"],    # header
    -1: ["field_id", "total_cnt", "control_sum"],   # footer
    "tx": ["field_id","counter"]  # transaction
}

ALLOWED_CURRENCIES = ["PLN", "EUR", "USD", "GBP"]
