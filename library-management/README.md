# Library Management System

## Problem
Design a small library system that tracks books and their physical copies, lets members check out and return copies, and notifies a member when a book they wanted becomes available again. A title can have zero or more physical copies in circulation at once, each with its own status.

## Design
- `Book` — catalog entry (isbn, title, author). Holds its `BookItem` copies and the list of members subscribed for a return notification.
- `BookItem` — one physical copy of a `Book`, with a `BookStatus` (`AVAILABLE`, `LOANED`, `RESERVED`).
- `BookStatus` — enum for a copy's fixed set of states.
- `Member` — a library patron; implements `BookAvailabilityObserver` so it can be notified directly.
- `BookAvailabilityObserver` — interface with `onAvailable(Book)`, implemented by `Member`.
- `Library` — the catalog/service layer: maps isbn to `Book`, maps member id to `Member`, and exposes `checkout`, `returnBook`, `subscribeForAvailability`.

## Patterns used
- **Observer** — `Book` keeps a list of `BookAvailabilityObserver`s and fires `notifySubscribers()` on return, so any member waiting on a title finds out the moment a copy comes back, without the `Library` having to poll or push manually to each interested member.

## How to run
```
cd library-management
java Main.java
```
