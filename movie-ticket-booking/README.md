# Movie Ticket Booking

## Problem
Design a system to browse movie shows, pick seats from a seat map, and book them with payment. Seats must not be double-booked when multiple users try to book the same seat, and interested parties should be notified when a booking is confirmed.

## Design
- `Movie` - title, duration, language.
- `Theater` - name and city.
- `Show` - a screening of a `Movie` at a `Theater` at a given time; owns a seat map (`dict[str, Seat]`) and computes price per seat by type.
- `Seat` - id, row, number, `SeatType` (REGULAR/PREMIUM), and a `SeatStatus` enum (AVAILABLE, LOCKED, BOOKED) with `lock()`/`release()`/`book()` transitions guarding invalid state changes.
- `Payment` - amount + `PaymentStatus`, processed independently of the booking so failure can roll back seat locks.
- `Booking` - ties a `Show`, a list of `Seat`s, a user, and a `Payment` together with its own `BookingStatus`.
- `BookingObserver` (ABC) - `on_booking_confirmed(booking)`; `EmailConfirmationObserver` and `SmsConfirmationObserver` implement it.
- `BookingService` - orchestrates the workflow: `lock_seats` -> `confirm_booking` (charges payment, books seats, notifies observers). Holds the list of registered observers.

## Patterns used
- **Observer** - `BookingService` notifies every registered `BookingObserver` on confirmation, so adding a new notification channel (push, webhook, ...) doesn't touch the booking logic.
- **State (lightweight, enum-based)** - `Seat.status` plus its guarded transition methods model AVAILABLE -> LOCKED -> BOOKED without a full class-per-state hierarchy, which would be overkill for three states with no per-state behavior beyond the transition rules.

## Scope cuts
No concurrency/locking primitives (threads/DB row locks) - `lock_seats` is illustrative of the workflow, not thread-safe. No seat-hold expiry timer.

## How to run
```
python3 main.py
```
