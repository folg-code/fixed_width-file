from core.const import Colors


def handle_validate_loaded(fw):
    data_errors = fw.validate(verbose=False)
    line_errors = []

    if hasattr(fw, "_read_errors"):
        re = fw._read_errors
        line_errors.extend([f"Header: {e}" for e in re.get("header", [])])
        for idx, tx_errs in re.get("transactions", []):
            for e in tx_errs:
                line_errors.append(f"Transaction {idx}: {e}")
        line_errors.extend([f"Footer: {e}" for e in re.get("footer", [])])

    all_errors = line_errors + data_errors

    if all_errors:
        print(Colors.RED.value+ "Errors found:" + Colors.RESET.value)
        for e in all_errors:
            print(Colors.RED.value+ " - " + e + Colors.RESET.value)
    else:
        print(Colors.GREEN.value + "No errors found." + Colors.RESET.value)
