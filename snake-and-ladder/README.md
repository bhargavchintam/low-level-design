# Snake and Ladder

## Problem
Design a multiplayer snake and ladder game on a 100-square board with fixed snake and ladder positions. Players take turns rolling a die and moving forward; landing on a snake's head sends them down, landing on a ladder's base sends them up. The first player to land exactly on square 100 wins.

## Design
- `Dice` — abstract base with `roll()`, so the die-rolling mechanism is swappable.
- `StandardDice` — concrete `Dice` returning a random value 1-6, backed by a seeded `random.Random` for reproducible demo output.
- `Player` — name and current board position.
- `Board` — holds the snake and ladder start->end mappings and resolves a landed-on square to its final square.
- `Game` — runs turns round-robin, applies rolls, reports snake/ladder hits, and stops when a player reaches square 100.

## Patterns used
- **Strategy** — `Dice` is an interface with `StandardDice` as one implementation; a loaded die, a two-dice-sum variant, or a scripted die for testing could be swapped in without touching `Game`.

## How to run
```
cd snake-and-ladder
python3 main.py
```
