# STRUKTURA PLIKÓW
LINE_LENGTH = 120
HEADER_FIELD_ID = "01"
HEADER_FIELD_ID_WIDTH = 2
HEADER_NAME_WIDTH = 28
HEADER_SURNAME_WIDTH = 30
HEADER_PATRONYMIC_WIDTH = 30
HEADER_ADDRESS_WIDTH = 30



# ------------------- KOLORY -------------------
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

ALLOWED_CURRENCIES = ["PLN", "EUR", "USD"]



# ZAPYTAĆ O LOGI - KTÓRE ZOSTAWIĆ
# CZY WYEKSPORTOWAĆ STRUKTURĘ PLIKU DO CONST
# ZISTAWIĆ DELETE CZY NIE