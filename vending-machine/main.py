from machine import VendingMachine
from models import Inventory, Product, Slot


def build_inventory() -> Inventory:
    inventory = Inventory()
    inventory.add_slot(Slot("A1", Product("Coke", 25.0), 2))
    inventory.add_slot(Slot("A2", Product("Chips", 20.0), 0))  # out of stock on purpose
    inventory.add_slot(Slot("A3", Product("Candy", 10.0), 5))
    return inventory


def main() -> None:
    machine = VendingMachine(build_inventory())

    print("--- Buying a Coke ---")
    machine.insert_coin(10)
    machine.insert_coin(10)
    machine.insert_coin(10)
    machine.select_product("A1")

    print("\n--- Trying an out-of-stock product ---")
    machine.insert_coin(20)
    machine.select_product("A2")
    machine.refund()

    print("\n--- Insufficient money, then topping up ---")
    machine.insert_coin(5)
    machine.select_product("A3")
    machine.insert_coin(5)
    machine.select_product("A3")


if __name__ == "__main__":
    main()
