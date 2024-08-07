from atm import ATM
from cash_dispenser import CashDispenser
from models import Account, Bank, Card


def build_bank() -> Bank:
    bank = Bank()
    bank.register(Card("4111-1111", "1234"), Account("ACC-001", 5000.0))
    return bank


def main() -> None:
    bank = build_bank()
    dispenser = CashDispenser({2000: 5, 500: 10, 200: 10, 100: 20})
    atm = ATM(bank, dispenser)

    print("--- Successful withdrawal ---")
    atm.insert_card("4111-1111")
    atm.enter_pin("1234")
    atm.withdraw(3700)

    print("\n--- Wrong PIN three times, card retained ---")
    atm.insert_card("4111-1111")
    atm.enter_pin("0000")
    atm.enter_pin("1111")
    atm.enter_pin("2222")
    atm.withdraw(100)  # card already retained, ATM is back to idle

    print("\n--- Insufficient balance case ---")
    atm.insert_card("4111-1111")
    atm.enter_pin("1234")
    atm.withdraw(10000)


if __name__ == "__main__":
    main()
