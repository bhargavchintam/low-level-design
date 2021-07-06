# Tic-Tac-Toe

## Problem
Design a two-player tic-tac-toe game on a 3x3 board. Players alternate placing their symbol in an empty cell; the game ends when a player lines up three symbols in a row, column, or diagonal, or when the board fills up with no winner.

## Design
- `Symbol` — enum for `X`, `O`, and `EMPTY` (the fixed set of things a cell can hold).
- `Player` — abstract base with `next_move()`; keeps the game engine decoupled from how a move is decided.
- `HumanPlayer` — concrete `Player` that plays back a pre-scripted list of moves, which is what makes the demo non-interactive and reproducible.
- `Board` — owns the 3x3 grid, cell placement, full/draw check, and win detection across rows, columns, and both diagonals.
- `Game` — owns turn order, drives the loop, and reports the outcome.

## Patterns used
- **Strategy-ish polymorphism via `Player`** — `next_move()` is abstract on `Player`, so a `HumanPlayer` (scripted here) can later sit next to an `AIPlayer` or a real interactive player without the `Game` changing.

## How to run
```
cd tic-tac-toe
python3 main.py
```
