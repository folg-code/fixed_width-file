def show_header(header):
    print("HEADER")
    print(f"Name: {header.name}, Surname: {header.surname}, Patronymic: {header.patronymic}, Address: {header.address}")

def show_transactions(transactions, max_rows=5):
    print("TRANSACTIONS")
    for tx in transactions[:max_rows]:
        print(f"{tx.counter}: {tx.amount} {tx.currency} {tx.reserved}")
    if len(transactions) > max_rows:
        print(f"... skipped {len(transactions)-max_rows} transactions ...")

def show_footer(footer):
    print("FOOTER")
    print(f"Total counter: {footer.total_cnt}, Control sum: {footer.control_sum}, Reserved: {footer.reserved}")