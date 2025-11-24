import argparse
import os

from decimal import Decimal
import logging

from config_logging import setup_logging
from const import C, ALLOWED_CURRENCIES, READONLY_FIELDS
from models import FixedWidthFile, Header, Footer

setup_logging()
logger = logging.getLogger(__name__)



# ------------------- HANDLERY -------------------
def handle_create():
    print(C.C + "Tworzenie nowego pliku..." + C.RESET)
    path = input("Ścieżka pliku: ").strip()
    if os.path.exists(path):
        if input("Plik istnieje. Nadpisać? (t/n): ") != "t":
            print(C.Y + "Anulowano." + C.RESET)
            return
    print("Podaj dane nagłówka:")
    name = input("Imię: ").strip()
    surname = input("Nazwisko: ").strip()
    patronymic = input("Drugie imię: ").strip()
    address = input("Adres: ").strip()

    fw = FixedWidthFile(
        header=Header(name, surname, patronymic, address),
        transactions=[],
        footer=Footer(0, Decimal("0.00"), ""),
    )
    fw.write_file(path)
    print(C.G + "Utworzono nowy plik." + C.RESET)

def handle_open():
    path = input("Ścieżka pliku: ").strip()

    try:
        fw = FixedWidthFile.read_file(path)
    except Exception as e:
        print(C.R + f"Błąd: {e}" + C.RESET)
        return None, None

    print(C.G + "Plik wczytano." + C.RESET)

    try:
        with open(path, "r") as f:
            raw_lines = [line.rstrip("\n") for line in f.readlines()]
    except Exception as e:
        print(C.R + f"Nie udało się odczytać pliku: {e}" + C.RESET)
        return fw, path

    header_raw = raw_lines[0]
    footer_raw = raw_lines[-1]
    tx_raw_lines = raw_lines[1:-1]


    # ==========================
    # HEADER
    # ==========================
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

    # ==========================
    # TRANSACTIONS
    # ==========================
    print(C.Y + "TRANSACTION" + C.RESET)
    print(C.C +
          f"{'field_id':>8} {'counter':>7} {'amount':>12} {'currency':>8} {'reserved':<110}" +
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
        print(f"{t[0]:>8} {t[1]:>7} {t[2]:>12} {t[3]:>8} {t[4]:<110}")

    if len(tx_raw_lines) > 5:
        print(C.Y + f"... pominięto {len(tx_raw_lines) - 5} transakcji ..." + C.RESET)


    # ==========================
    # FOOTER
    # ==========================
    print(C.Y + "FOOTER" + C.RESET)
    print(C.C +
          f"{'field_id':>8} {'total_cnt':>9} {'control_sum':>12} {'reserved':<100}" +
          C.RESET)

    def split_footer(line):
        return [
            line[0:2].strip(),
            line[2:8].strip(),
            line[8:20].strip(),
            line[20:120].rstrip()
        ]

    f = split_footer(footer_raw)
    print(f"{f[0]:>8} {f[1]:>9} {f[2]:>12} {f[3]:>110}")
    print()

    print(C.Y + "\nWALIDACJA" + C.RESET)

    handle_validate_loaded(fw)

    return fw, path


# ---- funkcje używane w edit_menu ----
def handle_get_loaded(fw: FixedWidthFile):
    """Odczytuje wartość wybranego pola rekordu."""
    n_tx = len(fw.transactions)
    print(f"Dostępne rekordy: 0=Header, -1=Footer, 1..{n_tx}=Transakcje")

    try:
        idx = int(input("Wybierz rekord: ").strip())
        if idx < -1 or idx > n_tx:
            raise ValueError("Niepoprawny indeks rekordu")
    except Exception as e:
        print(C.R + f"Niepoprawny numer rekordu: {e}" + C.RESET)
        return

    # Lista pól zależnie od rekordu
    if idx == 0:
        fields = list(fw.header.__dataclass_fields__.keys())
    elif idx == -1:
        fields = list(fw.footer.__dataclass_fields__.keys())
    else:
        fields = list(fw.transactions[0].__dataclass_fields__.keys())

    print("Dostępne pola:")
    for i, f in enumerate(fields, start=1):
        print(f" {i}. {f}")

    try:
        choice = int(input("Wybierz pole: ").strip())
        if not 1 <= choice <= len(fields):
            raise ValueError("Niepoprawny wybór pola")
        field = fields[choice - 1]
    except Exception as e:
        print(C.R + f"Niepoprawny wybór pola: {e}" + C.RESET)
        return

    try:
        val = fw.get_record(idx, field)
        print(C.C + f"Wartość pola '{field}' = {val}" + C.RESET)
    except Exception as e:
        print(C.R + "Wystąpił nieoczekiwany błąd przy odczycie pola." + C.RESET)
        logger.exception("Błąd przy odczycie pola rekordu %s[%s]: %s", idx, field, e)




def handle_set_loaded(fw: FixedWidthFile):
    """Ustawia wartość pola dla wybranego rekordu."""
    n_tx = len(fw.transactions)
    print(f"Dostępne rekordy: 0=Header, -1=Footer, 1..{n_tx}=Transakcje")
    try:
        idx = int(input("Wybierz rekord: ").strip())
        if idx < -1 or idx > n_tx:
            raise ValueError
    except Exception:
        print(C.R + "Niepoprawny numer rekordu." + C.RESET)
        return

    # pola zależnie od rekordu
    if idx == 0:
        fields = [f for f in fw.header.__dataclass_fields__.keys()]
        fields = [f for f in fields if f not in READONLY_FIELDS[0]]
    elif idx == -1:
        fields = [f for f in fw.footer.__dataclass_fields__.keys()]
        fields = [f for f in fields if f not in READONLY_FIELDS[-1]]
    else:
        fields = [f for f in fw.transactions[0].__dataclass_fields__.keys()]
        fields = [f for f in fields if f not in READONLY_FIELDS["tx"]]

    print("Dostępne pola do edycji:")
    for i, f in enumerate(fields, start=1):
        print(f" {i}. {f}")

    try:
        choice = int(input("Wybierz pole: ").strip())
        if not 1 <= choice <= len(fields):
            raise ValueError
        field = fields[choice - 1]
    except Exception:
        print(C.R + "Niepoprawny wybór pola." + C.RESET)
        return

    # Wartość pola
    if idx > 0 and field == "currency":
        print("Wybierz walutę:")
        for i, cur in enumerate(ALLOWED_CURRENCIES, start=1):
            print(f" {i}. {cur}")
        try:
            choice = int(input("> ").strip())
            if not 1 <= choice <= len(ALLOWED_CURRENCIES):
                raise ValueError
            val = ALLOWED_CURRENCIES[choice - 1]
        except Exception:
            print(C.R + "Niepoprawny wybór waluty." + C.RESET)
            return
    else:
        val = input("Nowa wartość: ").strip()

    try:
        fw.set_record(idx, field, val)
        print(C.G + f"Zmieniono pole '{field}'." + C.RESET)
    except ValueError as e:
        print(C.R + f"Niepoprawna wartość: {e}" + C.RESET)
        logger.warning("Nieudana próba ustawienia rekordu %s[%s]: %s", idx, field, e)
    except Exception as e:
        print(C.R + "Wystąpił nieoczekiwany błąd." + C.RESET)
        logger.exception("Błąd przy ustawianiu rekordu %s[%s]: %s", idx, field, e)




def handle_add_loaded(fw):
    try:
        amount_str = input("Kwota (np. 123.45): ").strip()
        amount = Decimal(amount_str)
    except Exception:
        print(C.R + "Niepoprawna kwota." + C.RESET)
        return

    # Interaktywny wybór waluty
    print("Wybierz walutę:")
    for i, cur in enumerate(ALLOWED_CURRENCIES, start=1):
        print(f" {i}. {cur}")

    try:
        choice = int(input("> ").strip())
        if not 1 <= choice <= len(ALLOWED_CURRENCIES):
            raise ValueError
        currency = ALLOWED_CURRENCIES[choice - 1]
    except Exception:
        print(C.R + "Niepoprawny wybór waluty." + C.RESET)
        return



    # Próba dodania transakcji z walidacją klas
    try:
        fw.add_transaction(amount, currency)
        print(C.G + f"Dodano transakcję w walucie {currency}." + C.RESET)
        logger.info("Dodano transakcję: counter=%d amount=%s currency=%s",
                    fw.transactions[-1].counter, amount, currency)
    except ValueError as e:
        # walidacja klasy Transaction nie powiodła się
        print(C.R + f"Nie udało się dodać transakcji: {e}" + C.RESET)
        logger.warning("Nieudana próba dodania transakcji: %s", e)
    except Exception as e:
        print(C.R + f"Wystąpił nieoczekiwany błąd." + C.RESET)
        logger.exception("Nieoczekiwany błąd przy dodawaniu transakcji: %s", e)

def handle_delete_loaded(fw: FixedWidthFile):
    """Usuwa wybraną transakcję z walidacją i logowaniem."""
    if not fw.transactions:
        print(C.Y + "Brak transakcji do usunięcia." + C.RESET)
        return

    print(C.M + "Dostępne transakcje:" + C.RESET)
    for i, tx in enumerate(fw.transactions, start=1):
        print(f"{i}: counter={tx.counter}, amount={tx.amount}, currency={tx.currency}")

    try:
        idx = int(input(f"Podaj numer rekordu do usunięcia (1..{len(fw.transactions)}): ").strip())
        fw.delete_record(idx)
        print(C.G + f"Usunięto transakcję nr {idx}." + C.RESET)
    except ValueError as e:
        print(C.R + f"Niepoprawny numer rekordu: {e}" + C.RESET)
        logger.warning("Nieudana próba usunięcia rekordu: %s", e)
    except Exception as e:
        print(C.R + "Wystąpił nieoczekiwany błąd podczas usuwania rekordu." + C.RESET)
        logger.exception("Błąd przy usuwaniu rekordu %s: %s", idx, e)


def handle_list_loaded(fw):
    print(C.M + "\nTransakcje:" + C.RESET)
    for t in fw.transactions:
        print(f"{t.counter}: {t.amount} {t.currency}")




def handle_validate_loaded(fw):
    errors = fw.validate(verbose=False)

    # dodajemy też błędy z samego odczytu linii
    if hasattr(fw, "_read_errors"):
        re = fw._read_errors
        for err in re.get("header", []):
            errors.append(f"Header: {err}")
        for idx, tx_errs in re.get("transactions", []):
            for e in tx_errs:
                errors.append(f"Transaction {idx}: {e}")
        for err in re.get("footer", []):
            errors.append(f"Footer: {err}")

    if errors:
        print(C.R + "Znaleziono błędy:" + C.RESET)
        for e in errors:
            print(C.R + " - " + e + C.RESET)
    else:
        print(C.G + "Brak błędów walidacji." + C.RESET)



def edit_menu(fw, path):
    while True:
        print(C.Y + "\n--- EDYCJA PLIKU ---" + C.RESET)
        print("1. Pobierz pole")
        print("2. Ustaw pole")
        print("3. Dodaj transakcję")
        print("4. Usuń transakcję")
        print("5. Lista transakcji")
        print("6. Waliduj")
        print("7. Zapisz")
        print("0. Zamknij")


        c = input("> ").strip()


        if c == "1": handle_get_loaded(fw)
        elif c == "2": handle_set_loaded(fw)
        elif c == "3": handle_add_loaded(fw)
        elif c == "4": handle_delete_loaded(fw)
        elif c == "5": handle_list_loaded(fw)
        elif c == "6": handle_validate_loaded(fw)
        elif c == "7": fw.write_file(path); print(C.G + "Zapisano." + C.RESET)
        elif c == "0": break
        else:
            print(C.R + "Nieznana opcja." + C.RESET)

# ------------------- MENU GŁÓWNE -------------------
def main():
    while True:
        print(C.Y + "\n=== MENU GŁÓWNE ===" + C.RESET)
        print("1. Utwórz nowy plik")
        print("2. Otwórz plik")
        print("0. Wyjście")


        choice = input("> ").strip()
        if choice == "1": handle_create()
        elif choice == "2":
            fw, path = handle_open()
            if fw: edit_menu(fw, path)
        elif choice == "0": break
        else:
            print("Nieznana opcja.")




if __name__ == "__main__":
    main()

