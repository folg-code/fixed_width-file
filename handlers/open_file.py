from core.const import C
from core.models import FixedWidthFile
from handlers.validate import handle_validate_loaded


def handle_open():
    path = input("File path: ").strip()

    try:
        fw = FixedWidthFile.read_file(path)
    except Exception as e:
        print(C.R + f"Error: {e}" + C.RESET)
        return None, None

    print(C.G + "File loaded." + C.RESET)

    try:
        with open(path, "r") as f:
            raw_lines = [line.rstrip("\n") for line in f.readlines()]
    except Exception as e:
        print(C.R + f"Failed to read file: {e}" + C.RESET)
        return fw, path

    header_raw = raw_lines[0]
    footer_raw = raw_lines[-1]
    tx_raw_lines = raw_lines[1:-1]

    print(C.Y + "HEADER" + C.RESET)
    print(C.C +
          f"{'field_id':>8} {'name':>28} {'surname':>30} {'patronymic':>30} {'address':>24}" +
          C.RESET)
    def split_header(line):
        return [
            line[0:2].strip(),
            line[2:30].strip(),
            line[30:60].strip(),
            line[60:90].strip(),
            line[90:120].strip()
        ]
    h = split_header(header_raw)
    print(f"{h[0]:>8} {h[1]:>28} {h[2]:>30} {h[3]:>30} {h[4]:>24}")

    print(C.Y + "TRANSACTION" + C.RESET)
    print(C.C +
          f"{'field_id':>8} {'counter':>7} {'amount':>12} {'currency':>8} {'reserved':<85}" +
          C.RESET)
    def split_tx(line):
        return [
            line[0:2].strip(),
            line[2:8].strip(),
            line[8:20].strip(),
            line[20:23].strip(),
            line[23:120].rstrip()
        ]

    for line in tx_raw_lines[:5]:
        t = split_tx(line)
        print(f"{t[0]:>8} {t[1]:>7} {t[2]:>12} {t[3]:>8} {t[4]:<85}")

    if len(tx_raw_lines) > 5:
        print(C.Y + f"... skipped {len(tx_raw_lines) - 5} transactions ..." + C.RESET)

    print(C.Y + "FOOTER" + C.RESET)
    print(C.C +
          f"{'field_id':>8} {'total_cnt':>10} {'control_sum':>12} {'reserved':<90}" +
          C.RESET)
    def split_footer(line):
        return [
            line[0:2].strip(),
            line[2:8].strip(),
            line[8:20].strip(),
            line[20:120].rstrip()
        ]

    f = split_footer(footer_raw)
    print(f"{f[0]:>8} {f[1]:>10} {f[2]:>12} {f[3]:>90}")
    print()

    print(C.Y + "\nVALIDATION" + C.RESET)

    handle_validate_loaded(fw)

    return fw, path
