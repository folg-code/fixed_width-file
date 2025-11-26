from enum import Enum

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
        "total_cnt": {"width": 6, "type": "int"},
        "control_sum": {"width": 12, "type": "decimal"},
        "reserved": {"width": 100, "type": "str"},  # 120 - sum of previous fields
    }
}

class Colors(str, Enum):
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

READONLY_FIELDS = {
    "header": ["field_id"],
    "txn": ["field_id","counter"],
    "footer": ["field_id", "total_cnt", "control_sum"],

}

ALLOWED_CURRENCIES = ["PLN", "EUR", "USD", "GBP"]
