from core.const import C, READONLY_FIELDS, ALLOWED_CURRENCIES
from handlers import crud, validate
from handlers.open_file import handle_open
from handlers.settings import handle_settings

def edit_menu(fw, path):
    while True:
        print(C.Y + "\n--- EDIT MENU ---" + C.RESET)
        print("1. Get field")
        print("2. Set field / Edit record")
        print("3. Add transaction")
        print("4. Delete transaction")
        print("5. List transactions")
        print("6. Validate")
        print("7. Save")
        print("8. Settings")
        print("0. Exit")
        c = input("> ").strip()
        if c == "1": crud.get_field(fw)
        elif c == "2": crud.set_field(fw)
        elif c == "3": crud.add_transaction(fw)
        elif c == "4": crud.delete_transaction(fw)
        elif c == "5": crud.list_transactions(fw)
        elif c == "6": validate.handle_validate_loaded(fw)
        elif c == "7": fw.write_file(path); print("Saved.")
        elif c == "8": handle_settings(fw)
        elif c == "0": break

def main():
    while True:
        print(C.Y + "\n=== MAIN MENU ===" + C.RESET)
        print("1. Create new file")
        print("2. Open file")
        print("0. Exit")

        choice = input("> ").strip()
        if choice == "1":
            fw, path = crud.create_file()
            if fw:
                edit_menu(fw, path)
        elif choice == "2":
            fw, path = handle_open()
            if fw:
                edit_menu(fw, path)
        elif choice == "0":
            break
        else:
            print("Unknown option.")


if __name__ == "__main__":
    main()
