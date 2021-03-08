# Vending Machine

## Problem
Design a vending machine that accepts coins, lets a customer select a product by slot code, dispenses the product with change if enough money was inserted, and handles edge cases like an out-of-stock slot or insufficient payment.

## Design
- `Product` (dataclass) - name, price
- `Slot` (dataclass) - code, product, quantity; knows how to check/decrement its own stock
- `Inventory` - maps slot code to `Slot`
- `VendingMachineState` (ABC) - `insert_coin`, `select_product`, `dispense`, `refund`, implemented by `IdleState`, `HasMoneyState`, `DispensingState`, `SoldOutState`
- `VendingMachine` - holds `balance`, `selected_code`, `Inventory`, and the current state; every public method just delegates to `self.state`

State flow: `Idle` -> (coin inserted) -> `HasMoney` -> (valid selection, enough balance) -> `Dispensing` -> back to `Idle`. Selecting an empty slot from `HasMoney` moves to `SoldOut`, which still accepts more coins or a different in-stock selection before returning to `HasMoney`/`Idle`.

## Patterns used
- **State** (`VendingMachineState` and its four implementations) - what "insert coin" or "select product" actually does depends entirely on where the machine is in its lifecycle, so each state owns its own behavior instead of one method full of flags.
- Dataclasses for `Product`/`Slot` keep the plain data holders boilerplate-free while the state classes carry all the behavior.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/vending-machine
python3 main.py
```
