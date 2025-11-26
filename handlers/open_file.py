from core.const import Colors
from core.models import FixedWidthFile
from handlers.validate import handle_validate_loaded


def handle_open():
    path = input("File path: ").strip()

    try:
        fw = FixedWidthFile.read_file(path)
    except Exception as e:
        print(Colors.RED.value+ f"Error: {e}" + Colors.RESET.value)
        return None, None

    print(Colors.GREEN.value + "File loaded." + Colors.RESET.value)

    try:
        with open(path, "r") as f:
            raw_lines = [line.rstrip("\n") for line in f.readlines()]
    except Exception as e:
        print(Colors.RED.value+ f"Failed to read file: {e}" + Colors.RESET.value)
        return fw, path

    header_raw = raw_lines[0]
    footer_raw = raw_lines[-1]
    tx_raw_lines = raw_lines[1:-1]

    print(Colors.YELLOW.value + "HEADER" + Colors.RESET.value)
    print(Colors.CYAN.value +
          f"{'field_id':>8} {'name':>28} {'surname':>30} {'patronymic':>30} {'address':>24}" +
          Colors.RESET.value)
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

    print(Colors.YELLOW.value + "TRANSACTION" + Colors.RESET.value)
    print(Colors.CYAN.value +
          f"{'field_id':>8} {'counter':>7} {'amount':>12} {'currency':>8} {'reserved':<85}" +
          Colors.RESET.value)
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
        print(Colors.YELLOW.value + f"... skipped {len(tx_raw_lines) - 5} transactions ..." + Colors.RESET.value)

    print(Colors.YELLOW.value + "FOOTER" + Colors.RESET.value)
    print(Colors.CYAN.value +
          f"{'field_id':>8} {'total_cnt':>10} {'control_sum':>12} {'reserved':<90}" +
          Colors.RESET.value)
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

    print(Colors.YELLOW.value + "\nVALIDATION" + Colors.RESET.value)

    handle_validate_loaded(fw)

    return fw, path
