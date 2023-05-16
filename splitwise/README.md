# Splitwise

## Problem
Design an expense-splitting system like Splitwise: a group of users records shared expenses that can be divided equally, by exact amounts, or by percentage, and the system must be able to report the net amount each person owes every other person across all recorded expenses.

## Design
- `User` - id + name.
- `Group` - a name and a list of member `User`s.
- `SplitStrategy` (interface) - `computeShares(totalAmount, participants) -> Map<User, Double>`; implemented by `EqualSplit`, `ExactSplit` (validates amounts sum to the total), and `PercentSplit` (validates percentages sum to 100). Both validating strategies throw `IllegalArgumentException` on mismatch.
- `Expense` - payer, amount, and the strategy used; computes and stores each participant's share at construction time.
- `Ledger` - records every `Expense` and maintains a debtor -> creditor -> net-amount map, updated incrementally as expenses are added, and can print the final net balances.

## Patterns used
- **Strategy** - `SplitStrategy` lets `Expense` be built with any split algorithm (equal/exact/percent) interchangeably, with validation logic isolated to the strategy that needs it.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/splitwise
java Main.java
```
