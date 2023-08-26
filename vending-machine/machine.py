from models import Inventory
from states import DispensingState, HasMoneyState, IdleState, SoldOutState


class VendingMachine:
    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory
        self.balance = 0.0
        self.selected_code = None

        self.idle_state = IdleState()
        self.has_money_state = HasMoneyState()
        self.dispensing_state = DispensingState()
        self.sold_out_state = SoldOutState()

        self.state = self.idle_state

    def set_state(self, state) -> None:
        self.state = state

    def insert_coin(self, amount: float) -> None:
        self.state.insert_coin(self, amount)

    def select_product(self, code: str) -> None:
        self.state.select_product(self, code)

    def dispense(self) -> None:
        self.state.dispense(self)

    def refund(self) -> None:
        self.state.refund(self)
