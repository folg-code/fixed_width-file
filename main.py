from core.const import  Colors
from handlers import crud, validate
from handlers.open_file import handle_open
from handlers.settings import handle_settings

def edit_menu(fw, path):
    while True:
        print(Colors.YELLOW.value + "\n--- EDIT MENU ---" + Colors.RESET.value)
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

        match c:
            case "1":
                crud.get_field(fw)
            case "2":
                crud.set_field(fw)
            case "3":
                crud.add_transaction(fw)
            case "4":
                crud.delete_transaction(fw)
            case "5":
                crud.list_transactions(fw)
            case "6":
                validate.handle_validate_loaded(fw)
            case "7":
                fw.write_file(path)
                print("Saved.")
            case "8":
                handle_settings(fw)
            case "0":
                break
            case _:
                print("Unknown option.")

def main():
    while True:
        print(Colors.YELLOW.value + "\n=== MAIN MENU ===" + Colors.RESET.value)
        print("1. Create new file")
        print("2. Open file")
        print("0. Exit")

        choice = input("> ").strip()

        match choice:
            case "1":
                fw, path = crud.create_file()
                if fw:
                    edit_menu(fw, path)
            case "2":
                fw, path = handle_open()
                if fw:
                    edit_menu(fw, path)
            case "0":
                break
            case _:
                print("Unknown option.")


if __name__ == "__main__":
    main()
