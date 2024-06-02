# Parking Lot

## Problem
Design a multi-floor parking lot that can park motorcycles, cars, and buses into appropriately sized spots, issue a ticket on entry, and compute a parking fee on exit. The lot should automatically find an available spot on any floor and support different pricing per vehicle type.

## Design
- `VehicleType` (enum) - MOTORCYCLE, CAR, BUS
- `SpotType` (enum) - SMALL, MEDIUM, LARGE, with a `fits(VehicleType)` rule (motorcycles fit any spot, cars need MEDIUM/LARGE, buses need LARGE)
- `Vehicle` - license plate + type
- `ParkingSpot` - id, type, floor number, current occupant
- `ParkingFloor` - owns a list of spots, finds the tightest free spot for a vehicle type
- `ParkingLot` - owns floors, assigns/releases spots across floors, issues `Ticket`s, tracks active tickets
- `Ticket` - id, vehicle, assigned spot, entry time
- `FeeStrategy` (interface) - `calculateFee(ticket, exitTime)`, implemented by `HourlyFeeStrategy` (per-vehicle-type hourly rate, rounds up partial hours)

`ParkingLot.park()` walks floors in order and asks each `ParkingFloor` for the best-fit free spot; if a floor has no room it moves to the next floor. `unpark()` delegates fee computation to the injected `FeeStrategy` and frees the spot.

## Patterns used
- **Strategy** (`FeeStrategy` / `HourlyFeeStrategy`) - pricing rules can change (flat rate, per-vehicle rate, weekend rate, etc.) without touching `ParkingLot` or spot-assignment logic.
- **Enum-based fixed categories** (`VehicleType`, `SpotType`) - closed sets of values with behavior (`fits`) attached, instead of scattered if/else on strings.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/parking-lot
java Main.java
```
