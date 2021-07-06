# Car Rental

## Problem
Design a car rental branch that manages a fleet of vehicles, lets a customer search for available vehicles by type, reserve one, and pay a bill computed from the rental duration once the vehicle is returned.

## Design
- `VehicleType` enum - CAR, SUV, BIKE.
- `Vehicle` (abstract) - plate number, type, base daily rate, availability flag; `Car`, `Suv`, `Bike` subclasses set their own base rate.
- `VehicleFactory` - `create(type, plateNumber)` builds the right subclass without the caller knowing the concrete class.
- `PricingStrategy` interface - `calculateFare(vehicle, days)`; `DailyRateStrategy` charges per day, `WeeklyRateStrategy` rounds up to whole weeks with a discount.
- `ReservationStatus` enum - RESERVED, ONGOING, COMPLETED, CANCELLED.
- `Reservation` - links a `Vehicle`, date range, chosen `PricingStrategy`, and its status.
- `RentalBranch` - owns the fleet, exposes `searchAvailable`, `reserve`, `startRental`, `returnVehicle` (computes and returns the bill), `cancel`.

## Patterns used
- **Factory Method** - `VehicleFactory` centralizes vehicle construction so adding a new vehicle type doesn't ripple into branch/reservation code.
- **Strategy** - `PricingStrategy` lets the same `Reservation`/`RentalBranch` flow bill daily or weekly (or any future scheme) without branching on type inside the branch.

## How to run
```
java Main.java
```
(Java 17+ single-file source launch, no separate compile step.)
