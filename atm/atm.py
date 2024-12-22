from cash_dispenser import CashDispenser
from models import Bank
from states import AuthenticatedState, HasCardState, IdleState


class ATM:
    def __init__(self, bank: Bank, cash_dispenser: CashDispenser, max_pin_attempts: int = 3) -> None:
        self.bank = bank
        self.cash_dispenser = cash_dispenser
        self.max_pin_attempts = max_pin_attempts
        self.pin_attempts = 0
        self.current_card = None

        self.idle_state = IdleState()
        self.has_card_state = HasCardState()
        self.authenticated_state = AuthenticatedState()

        self.state = self.idle_state

    def set_state(self, state) -> None:
        self.state = state

    def insert_card(self, card_number: str) -> None:
        self.state.insert_card(self, card_number)

    def enter_pin(self, pin: str) -> None:
        self.state.enter_pin(self, pin)

    def withdraw(self, amount: float) -> None:
        self.state.withdraw(self, amount)

    def eject_card(self) -> None:
        self.state.eject_card(self)
