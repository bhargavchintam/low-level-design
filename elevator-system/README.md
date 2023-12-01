# Elevator System

## Problem
Design a multi-elevator control system that accepts hall calls (a floor + direction, e.g. "floor 3, going up to floor 9"), dispatches the best elevator for the call, and simulates each elevator moving floor-by-floor to service its stops, opening its doors when it arrives.

## Design
- `Direction` (enum) - UP, DOWN, IDLE
- `ElevatorState` (interface) - `handle(Elevator)`, implemented by `IdleState`, `MovingUpState`, `MovingDownState`, `DoorsOpenState`
- `Elevator` - id, current floor, current `ElevatorState`, a sorted set of pending stop floors; `step()` delegates to `state.handle(this)` each simulation tick
- `DispatchStrategy` (interface) - `select(elevators, floor)`, implemented by `NearestElevatorStrategy`
- `ElevatorController` - owns all elevators, dispatches hall calls via the strategy, and drives the simulation tick by tick until every elevator is idle with no pending stops

Each state's `handle()` both performs the physical action for that tick (move one floor, or open doors) and decides the next state - e.g. `MovingUpState` advances the floor by one and switches to `DoorsOpenState` if the new floor is a pending stop; `DoorsOpenState` clears that stop and switches to `IdleState`, or picks up direction again if more stops remain.

## Patterns used
- **State** (`ElevatorState` and its four implementations) - an elevator's behavior (what a tick does) genuinely depends on whether it's idle, moving, or doors-open, so the state itself owns that logic instead of a tangle of if/else on an enum.
- **Strategy** (`DispatchStrategy` / `NearestElevatorStrategy`) - which elevator answers a hall call is a swappable policy (nearest, least-busy, zone-based) independent of how the controller loops or how elevators move.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/elevator-system
java Main.java
```
