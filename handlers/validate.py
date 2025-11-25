from core.const import C


def handle_validate_loaded(fw):
    """
    Łączy walidację danych i błędów odczytu linii, wyświetla w CLI.
    """
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
        print(C.R + "Errors found:" + C.RESET)
        for e in all_errors:
            print(C.R + " - " + e + C.RESET)
    else:
        print(C.G + "No errors found." + C.RESET)
