from core.const import C, READONLY_FIELDS

USER_READONLY_FIELDS = {
    0: [],      # Header
    "tx": [],   # Transaction
    -1: []     # Footer
}

def handle_settings(fw=None):
    while True:
        print(C.Y + "\n--- SETTINGS ---" + C.RESET)
        print("1. Show READONLY_FIELDS")
        print("2. Edit READONLY_FIELDS")
        print("3. Show ALLOWED_CURRENCIES")
        print("4. Edit ALLOWED_CURRENCIES")
        print("0. Back to menu")

        choice = input("> ").strip()
        if choice == "1":
            show_readonly_fields()
        elif choice == "2":
            edit_readonly_fields(fw)
        elif choice == "3":
            print(C.C + str(ALLOWED_CURRENCIES) + C.RESET)
        elif choice == "4":
            edit_allowed_currencies()
        elif choice == "0":
            break
        else:
            print(C.R + "Unknown option." + C.RESET)


def show_readonly_fields():
    print("--- READONLY_FIELDS ---")
    mapping = {0: "Header", "tx": "Transaction", -1: "Footer"}
    for key in [0, "tx", -1]:
        base_fields = READONLY_FIELDS.get(key, [])
        additional = USER_READONLY_FIELDS.get(key, [])
        all_fields = base_fields + additional
        fields_str = ", ".join(f"'{f}'" for f in all_fields)
        print(f"{mapping.get(key)} : {fields_str}")


def edit_readonly_fields(fw=None):
    print("Select record type to edit additional readonly fields:")
    print(" 0 - Header, -1 - Footer, tx - Transaction")
    key = input("> ").strip()
    if key == "0":
        key = 0
        obj = fw.header if fw else None
    elif key == "-1":
        key = -1
        obj = fw.footer if fw else None
    elif key.lower() == "tx":
        key = "tx"
        obj = fw.transactions[0] if fw and fw.transactions else None
    else:
        print(C.R + "Invalid key." + C.RESET)
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

        if choice == "3":
            break
        elif choice == "1":
            # Pola do dodania = wszystkie pola w obiekcie minus bazowe i już dodatkowe
            available_fields = [f for f in obj.__dataclass_fields__.keys()
                                if f not in base_fields and f not in current_additional]
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
        elif choice == "2":
            if not current_additional:
                print("No fields to remove.")
                continue
            print("Select fields to remove (names separated by comma):")
            for f in sorted(current_additional):
                print(f" - {f}")
            sel = input("> ").strip()
            for f in sel.split(","):
                current_additional.discard(f.strip())
        else:
            print("Unknown option.")

    USER_READONLY_FIELDS[key] = list(current_additional)
    print(C.G + f"Final additional readonly fields for {key}: {USER_READONLY_FIELDS[key]}" + C.RESET)

def edit_allowed_currencies():
    global ALLOWED_CURRENCIES

    while True:
        print("\nCurrent ALLOWED_CURRENCIES:", ALLOWED_CURRENCIES)
        print("Options:")
        print(" 1. Add new currencies")
        print(" 2. Remove a currency")
        print(" 0. Exit")
        choice = input("> ").strip()

        if choice == "0":
            break
        elif choice == "1":
            new_cur = input("Enter new currencies separated by comma: ").strip()
            if new_cur == "":
                print("Cancelled.")
                continue
            new_list = [c.strip().upper() for c in new_cur.split(",")]
            invalid = [c for c in new_list if len(c) != 3]
            if invalid:
                print(C.R + f"Invalid tickers (must be 3 letters): {invalid}" + C.RESET)
                continue
            # dodajemy tylko te, których jeszcze nie ma
            for c in new_list:
                if c not in ALLOWED_CURRENCIES:
                    ALLOWED_CURRENCIES.append(c)
            print(C.G + f"Updated ALLOWED_CURRENCIES: {ALLOWED_CURRENCIES}" + C.RESET)

        elif choice == "2":
            if not ALLOWED_CURRENCIES:
                print(C.Y + "No currencies to remove." + C.RESET)
                continue
            print("Select currency to remove:")
            for i, cur in enumerate(ALLOWED_CURRENCIES, 1):
                print(f" {i}. {cur}")
            try:
                idx = int(input("> ").strip())
                if 1 <= idx <= len(ALLOWED_CURRENCIES):
                    removed = ALLOWED_CURRENCIES.pop(idx - 1)
                    print(C.G + f"Removed {removed}. Updated list: {ALLOWED_CURRENCIES}" + C.RESET)
                else:
                    print(C.R + "Invalid selection." + C.RESET)
            except Exception:
                print(C.R + "Invalid input." + C.RESET)
        else:
            print(C.R + "Unknown option." + C.RESET)