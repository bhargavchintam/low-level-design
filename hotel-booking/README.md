# Hotel Booking

## Problem
Design a hotel system where guests can search for available rooms of a given type over a date range, book one, and check out to receive an invoice priced by a configurable rate strategy (e.g. weekend surcharge).

## Design
- `RoomType` enum - SINGLE, DOUBLE, DELUXE.
- `RoomStatus` enum - AVAILABLE, BOOKED, MAINTENANCE.
- `Room` - room number, type, base nightly rate, status.
- `RoomFactory` - `create(type, roomNumber)` builds a `Room` with the right base rate for its type.
- `PricingStrategy` interface - `priceFor(room, checkIn, checkOut)`; `WeekendPricingStrategy` charges a premium for Friday/Saturday nights and base rate otherwise.
- `ReservationStatus` enum - RESERVED, CHECKED_IN, COMPLETED, CANCELLED.
- `Reservation` - room, guest, date range, chosen pricing strategy, status; `overlaps(...)` checks date-range collision.
- `Guest` - name and email.
- `Invoice` - room number, nights stayed, base rate, computed total.
- `Hotel` - owns rooms and reservations; `searchAvailable` filters by type and by scanning existing reservations for date overlap (not just the room's current status flag, so multiple future bookings per room are handled correctly); `book` creates a `Reservation`; `checkout` prices it via the strategy and returns an `Invoice`.

## Patterns used
- **Factory Method** - `RoomFactory` centralizes room construction and base-rate assignment per type.
- **Strategy** - `PricingStrategy` decouples rate calculation (flat, weekend-surcharge, seasonal, ...) from `Hotel`/`Reservation`, which just delegate to whichever strategy was chosen at booking time.

## How to run
```
java Main.java
```
(Java 17+ single-file source launch, no separate compile step.)
