from core.const import READONLY_FIELDS, Colors

USER_READONLY_FIELDS = {
    "header" : [],
    "txn": [],
    "footer": []
}

def handle_settings(fw=None):
    while True:
        print(Colors.YELLOW.value + "\n--- SETTINGS ---" + Colors.RESET.value)
        print("1. Show READONLY_FIELDS")
        print("2. Edit READONLY_FIELDS")
        print("3. Show ALLOWED_CURRENCIES")
        print("4. Edit ALLOWED_CURRENCIES")
        print("0. Back to menu")

        choice = input("> ").strip()

        match choice:
            case "1":
                show_readonly_fields()
            case "2":
                edit_readonly_fields(fw)
            case "3":
                print(Colors.CYAN.value + str(ALLOWED_CURRENCIES) + Colors.RESET.value)
            case "4":
                edit_allowed_currencies()
            case "0":
                break
            case _:
                print(Colors.RED.value+ "Unknown option." + Colors.RESET.value)



def show_readonly_fields():
    print("--- READONLY_FIELDS ---")
    mapping = {"header": "Header", "txn": "Transaction", -1: "Footer"}
    for key in ["header", "txn", "footer"]:
        base_fields = READONLY_FIELDS.get(key, [])
        additional = USER_READONLY_FIELDS.get(key, [])
        all_fields = base_fields + additional
        fields_str = ", ".join(f"'{f}'" for f in all_fields)
        print(f"{mapping.get(key)} : {fields_str}")


def edit_readonly_fields(fw=None):
    print("Select record type to edit additional readonly fields:")
    print("  header, txn , footer")

    key_input = input("> ").strip()

    match key_input:
        case "header":
            key = "header"
            obj = fw.header if fw else None
        case "footer":
            key = "footer"
            obj = fw.footer if fw else None
        case s if s.lower() == "txn":
            key = "txn"
            obj = fw.transactions[0] if fw and fw.transactions else None
        case _:
            print(Colors.RED.value+ "Invalid key." + Colors.RESET.value)
            return

    if not obj:
        print("No example object available to list fields.")
        return

    base_fields = set(READONLY_FIELDS.get(key, []))
    current_additional = set(USER_READONLY_FIELDS.get(key, []))

    while True:
        print("\n--- Edit Additional Readonly Fields ---")
        print("Current additional readonly fields:", ", ".join(current_additional) or "(none)")
        print("Options:")
        print(" 1. Add fields")
        print(" 2. Remove fields")
        print(" 3. Quit")

        choice = input("> ").strip()

        match choice:
            case "3":
                break

            case "1":
                available_fields = [
                    f for f in obj.__dataclass_fields__.keys()
                    if f not in base_fields and f not in current_additional
                ]
                if not available_fields:
                    print("No fields available to add.")
                    continue

                print("Select fields to add (numbers separated by comma):")
                for i, f in enumerate(available_fields, start=1):
                    print(f" {i}. {f}")

                sel = input("> ").strip()
                try:
                    indexes = [int(x.strip()) - 1 for x in sel.split(",")]
                    for i in indexes:
                        if 0 <= i < len(available_fields):
                            current_additional.add(available_fields[i])
                except Exception:
                    print("Invalid selection.")

            case "2":
                if not current_additional:
                    print("No fields to remove.")
                    continue

                print("Select fields to remove (names separated by comma):")
                for f in sorted(current_additional):
                    print(f" - {f}")

                sel = input("> ").strip()
                for f in sel.split(","):
                    current_additional.discard(f.strip())

            case _:
                print("Unknown option.")

    USER_READONLY_FIELDS[key] = list(current_additional)
    print(Colors.GREEN.value + f"Final additional readonly fields for {key}: {USER_READONLY_FIELDS[key]}" + Colors.RESET.value)

def edit_allowed_currencies():
    global ALLOWED_CURRENCIES

    while True:
        print("\nCurrent ALLOWED_CURRENCIES:", ALLOWED_CURRENCIES)
        print("Options:")
        print(" 1. Add new currencies")
        print(" 2. Remove a currency")
        print(" 0. Exit")

        choice = input("> ").strip()

        match choice:
            case "0":
                break

            case "1":
                new_cur = input("Enter new currencies separated by comma: ").strip()
                if new_cur == "":
                    print("Cancelled.")
                    continue

                new_list = [c.strip().upper() for c in new_cur.split(",")]
                invalid = [c for c in new_list if len(c) != 3]

                if invalid:
                    print(Colors.RED.value+ f"Invalid tickers (must be 3 letters): {invalid}" + Colors.RESET.value)
                    continue

                for c in new_list:
                    if c not in ALLOWED_CURRENCIES:
                        ALLOWED_CURRENCIES.append(c)

                print(Colors.GREEN.value + f"Updated ALLOWED_CURRENCIES: {ALLOWED_CURRENCIES}" + Colors.RESET.value)

            case "2":
                if not ALLOWED_CURRENCIES:
                    print(Colors.YELLOW.value + "No currencies to remove." + Colors.RESET.value)
                    continue

                print("Select currency to remove:")
                for i, cur in enumerate(ALLOWED_CURRENCIES, 1):
                    print(f" {i}. {cur}")

                try:
                    idx = int(input("> ").strip())
                    if 1 <= idx <= len(ALLOWED_CURRENCIES):
                        removed = ALLOWED_CURRENCIES.pop(idx - 1)
                        print(Colors.GREEN.value + f"Removed {removed}. Updated list: {ALLOWED_CURRENCIES}" + Colors.RESET.value)
                    else:
                        print(Colors.RED.value+ "Invalid selection." + Colors.RESET.value)
                except Exception:
                    print(Colors.RED.value+ "Invalid input." + Colors.RESET.value)

            case _:
                print(Colors.RED.value+ "Unknown option." + Colors.RESET.value)
