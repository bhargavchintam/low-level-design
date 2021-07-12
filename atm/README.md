# ATM

## Problem
Design an ATM that walks through a real session: insert a card, verify a PIN (with a limited number of attempts before the card is retained), and withdraw cash which the machine breaks into actual note denominations. It should also reject withdrawals the account can't cover.

## Design
- `Card` (dataclass) - card number, PIN
- `Account` - account number, balance, `withdraw`/`has_sufficient_balance`
- `Bank` - registry mapping card number to `Card` and `Account`, verifies PINs
- `CashDispenser` - holds a denomination -> count map, greedily breaks a requested amount into notes, rejects amounts it can't make exactly
- `ATMState` (ABC) - `insert_card`, `enter_pin`, `withdraw`, `eject_card`, implemented by `IdleState`, `HasCardState`, `AuthenticatedState`
- `ATM` - current state, current card, `pin_attempts`, references to `Bank` and `CashDispenser`; every public method delegates to `self.state`

State flow: `Idle` -> (valid card) -> `HasCard` -> (correct PIN) -> `Authenticated` -> (withdrawal completes) -> back to `Idle`. Three wrong PINs from `HasCard` retains the card and drops back to `Idle`.

## Patterns used
- **State** (`ATMState` and its three implementations) - which actions are even legal ("enter PIN" before a card is inserted, "withdraw" before authentication) depends on where the session is, which is exactly what the state pattern is for.
- Denomination breakdown is isolated in `CashDispenser` so the withdrawal logic in `AuthenticatedState` doesn't need to know how notes are counted.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/atm
python3 main.py
```
