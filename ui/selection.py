from core.const import ALLOWED_CURRENCIES


def select_record(fw):
    n_tx = len(fw.transactions)
    print(f"Available records: 0=Header, -1=Footer, 1-{n_tx}=Transactions")
    try:
        idx = int(input("Select record: ").strip())
        if not (-1 <= idx <= n_tx):
            raise ValueError
        return idx
    except:
        print("Invalid record index.")
        return None

def select_field(fields):
    for i, f in enumerate(fields, 1):
        print(f"{i}. {f}")
    try:
        choice = int(input("Select field: ").strip())
        if 1 <= choice <= len(fields):
            return fields[choice - 1]
    except:
        pass
    print("Invalid field.")
    return None

def select_currency(old_val=None):
    for i, cur in enumerate(ALLOWED_CURRENCIES, 1):
        print(f"{i}. {cur}")
    if old_val:
        print(f"[ENTER to keep '{old_val}']")
    choice = input("> ").strip()
    if choice == "":
        return None
    try:
        idx = int(choice)
        if 1 <= idx <= len(ALLOWED_CURRENCIES):
            return ALLOWED_CURRENCIES[idx - 1]
    except:
        pass
    print("Invalid currency choice.")
    return None