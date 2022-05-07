from abc import ABC, abstractmethod


class VendingMachineState(ABC):
    @abstractmethod
    def insert_coin(self, machine, amount: float) -> None: ...

    @abstractmethod
    def select_product(self, machine, code: str) -> None: ...

    @abstractmethod
    def dispense(self, machine) -> None: ...

    @abstractmethod
    def refund(self, machine) -> None: ...


class IdleState(VendingMachineState):
    def insert_coin(self, machine, amount: float) -> None:
        machine.balance += amount
        print(f"Inserted {amount:.2f}. Balance: {machine.balance:.2f}")
        machine.set_state(machine.has_money_state)

    def select_product(self, machine, code: str) -> None:
        print("Insert coins before selecting a product.")

    def dispense(self, machine) -> None:
        print("Select a product first.")

    def refund(self, machine) -> None:
        print("Nothing to refund.")


class HasMoneyState(VendingMachineState):
    def insert_coin(self, machine, amount: float) -> None:
        machine.balance += amount
        print(f"Inserted {amount:.2f}. Balance: {machine.balance:.2f}")

    def select_product(self, machine, code: str) -> None:
        slot = machine.inventory.get(code)
        if slot is None or not slot.in_stock():
            print(f"Slot {code} is sold out.")
            machine.set_state(machine.sold_out_state)
            return
        if machine.balance < slot.product.price:
            shortfall = slot.product.price - machine.balance
            print(f"Insufficient funds for {slot.product.name} (need {shortfall:.2f} more).")
            return
        machine.selected_code = code
        machine.set_state(machine.dispensing_state)
        machine.dispense()

    def dispense(self, machine) -> None:
        print("Select a product first.")

    def refund(self, machine) -> None:
        print(f"Refunding {machine.balance:.2f}.")
        machine.balance = 0.0
        machine.set_state(machine.idle_state)


class DispensingState(VendingMachineState):
    # transient state - a product was already paid for, entry into this state
    # immediately triggers dispense() from HasMoneyState.select_product
    def insert_coin(self, machine, amount: float) -> None:
        print("Please wait, dispensing in progress.")

    def select_product(self, machine, code: str) -> None:
        print("Please wait, dispensing in progress.")

    def dispense(self, machine) -> None:
        slot = machine.inventory.get(machine.selected_code)
        slot.dispense_one()
        change = machine.balance - slot.product.price
        machine.balance = 0.0
        machine.selected_code = None
        print(f"Dispensed {slot.product.name}. Change returned: {change:.2f}")
        machine.set_state(machine.idle_state)

    def refund(self, machine) -> None:
        print("Cannot refund while dispensing.")


class SoldOutState(VendingMachineState):
    def insert_coin(self, machine, amount: float) -> None:
        machine.balance += amount
        print(f"Inserted {amount:.2f}. Balance: {machine.balance:.2f}")
        machine.set_state(machine.has_money_state)

    def select_product(self, machine, code: str) -> None:
        slot = machine.inventory.get(code)
        if slot is None or not slot.in_stock():
            print(f"Slot {code} is sold out. Pick another or ask for a refund.")
            return
        # a different, in-stock product was picked - hand off to the money-state logic
        machine.set_state(machine.has_money_state)
        machine.select_product(code)

    def dispense(self, machine) -> None:
        print("Nothing to dispense.")

    def refund(self, machine) -> None:
        print(f"Refunding {machine.balance:.2f}.")
        machine.balance = 0.0
        machine.set_state(machine.idle_state)
