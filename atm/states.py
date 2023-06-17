from abc import ABC, abstractmethod


class ATMState(ABC):
    @abstractmethod
    def insert_card(self, atm, card_number: str) -> None: ...

    @abstractmethod
    def enter_pin(self, atm, pin: str) -> None: ...

    @abstractmethod
    def withdraw(self, atm, amount: float) -> None: ...

    @abstractmethod
    def eject_card(self, atm) -> None: ...


class IdleState(ATMState):
    def insert_card(self, atm, card_number: str) -> None:
        card = atm.bank.get_card(card_number)
        if card is None:
            print(f"Card {card_number} not recognized.")
            return
        atm.current_card = card
        print(f"Card {card_number} inserted.")
        atm.set_state(atm.has_card_state)

    def enter_pin(self, atm, pin: str) -> None:
        print("Insert a card first.")

    def withdraw(self, atm, amount: float) -> None:
        print("Insert a card first.")

    def eject_card(self, atm) -> None:
        print("No card to eject.")


class HasCardState(ATMState):
    def insert_card(self, atm, card_number: str) -> None:
        print("A card is already inserted.")

    def enter_pin(self, atm, pin: str) -> None:
        if atm.bank.verify_pin(atm.current_card.card_number, pin):
            print("PIN correct.")
            atm.pin_attempts = 0
            atm.set_state(atm.authenticated_state)
        else:
            atm.pin_attempts += 1
            remaining = atm.max_pin_attempts - atm.pin_attempts
            if remaining <= 0:
                print("Too many incorrect attempts. Card retained.")
                atm.current_card = None
                atm.pin_attempts = 0
                atm.set_state(atm.idle_state)
            else:
                print(f"Incorrect PIN. {remaining} attempt(s) left.")

    def withdraw(self, atm, amount: float) -> None:
        print("Enter your PIN first.")

    def eject_card(self, atm) -> None:
        print("Card ejected.")
        atm.current_card = None
        atm.pin_attempts = 0
        atm.set_state(atm.idle_state)


class AuthenticatedState(ATMState):
    def insert_card(self, atm, card_number: str) -> None:
        print("A card is already inserted.")

    def enter_pin(self, atm, pin: str) -> None:
        print("Already authenticated.")

    def withdraw(self, atm, amount: float) -> None:
        account = atm.bank.get_account(atm.current_card.card_number)
        if not account.has_sufficient_balance(amount):
            print(f"Insufficient balance. Available: {account.balance:.2f}")
            return
        if not atm.cash_dispenser.can_dispense(amount):
            print("ATM cannot dispense that exact amount with available denominations.")
            return
        breakdown = atm.cash_dispenser.dispense(amount)
        account.withdraw(amount)
        notes = ", ".join(f"{count}x{note}" for note, count in sorted(breakdown.items(), reverse=True))
        print(f"Dispensing {amount}: {notes}")
        print(f"Remaining balance: {account.balance:.2f}")
        atm.current_card = None
        atm.set_state(atm.idle_state)  # a real ATM ends the session after a withdrawal

    def eject_card(self, atm) -> None:
        print("Card ejected.")
        atm.current_card = None
        atm.set_state(atm.idle_state)
