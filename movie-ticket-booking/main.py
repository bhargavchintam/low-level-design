"""Movie ticket booking system - core domain model + a demo run."""

from __future__ import annotations

import itertools
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class SeatStatus(Enum):
    AVAILABLE = auto()
    LOCKED = auto()
    BOOKED = auto()


class SeatType(Enum):
    REGULAR = auto()
    PREMIUM = auto()


class BookingStatus(Enum):
    PENDING = auto()
    CONFIRMED = auto()
    FAILED = auto()


@dataclass
class Movie:
    title: str
    duration_minutes: int
    language: str = "English"


@dataclass
class Seat:
    seat_id: str
    row: str
    number: int
    seat_type: SeatType = SeatType.REGULAR
    status: SeatStatus = SeatStatus.AVAILABLE

    def lock(self) -> bool:
        if self.status != SeatStatus.AVAILABLE:
            return False
        self.status = SeatStatus.LOCKED
        return True

    def release(self) -> None:
        if self.status == SeatStatus.LOCKED:
            self.status = SeatStatus.AVAILABLE

    def book(self) -> bool:
        if self.status != SeatStatus.LOCKED:
            return False
        self.status = SeatStatus.BOOKED
        return True


class Theater:
    def __init__(self, name: str, city: str):
        self.name = name
        self.city = city


class Show:
    """A single screening of a movie at a theater, with its own seat map."""

    def __init__(self, movie: Movie, theater: Theater, start_time: datetime,
                 rows: int = 3, seats_per_row: int = 5):
        self.show_id = str(uuid.uuid4())[:8]
        self.movie = movie
        self.theater = theater
        self.start_time = start_time
        self.seats: dict[str, Seat] = {}
        self._build_seat_map(rows, seats_per_row)

    def _build_seat_map(self, rows: int, seats_per_row: int) -> None:
        row_labels = [chr(ord("A") + r) for r in range(rows)]
        for row in row_labels:
            for num in range(1, seats_per_row + 1):
                seat_type = SeatType.PREMIUM if row == row_labels[0] else SeatType.REGULAR
                seat_id = f"{row}{num}"
                self.seats[seat_id] = Seat(seat_id, row, num, seat_type)

    def price_for(self, seat: Seat) -> float:
        return 300.0 if seat.seat_type == SeatType.PREMIUM else 200.0

    def seat_map(self) -> str:
        by_row: dict[str, list[Seat]] = {}
        for seat in self.seats.values():
            by_row.setdefault(seat.row, []).append(seat)
        symbol = {
            SeatStatus.AVAILABLE: ".",
            SeatStatus.LOCKED: "L",
            SeatStatus.BOOKED: "X",
        }
        lines = []
        for row in sorted(by_row):
            seats = sorted(by_row[row], key=lambda s: s.number)
            lines.append(row + " " + " ".join(symbol[s.status] for s in seats))
        return "\n".join(lines)


class PaymentStatus(Enum):
    SUCCESS = auto()
    FAILED = auto()


@dataclass
class Payment:
    amount: float
    status: PaymentStatus = PaymentStatus.FAILED

    def process(self) -> bool:
        # a real gateway call would happen here; assume success if amount > 0
        self.status = PaymentStatus.SUCCESS if self.amount > 0 else PaymentStatus.FAILED
        return self.status == PaymentStatus.SUCCESS


@dataclass
class Booking:
    booking_id: str
    show: Show
    seats: list[Seat]
    user: str
    status: BookingStatus = BookingStatus.PENDING
    payment: Payment | None = None


class BookingObserver(ABC):
    """Notified whenever a booking is confirmed - decouples booking from side effects."""

    @abstractmethod
    def on_booking_confirmed(self, booking: Booking) -> None:
        raise NotImplementedError


class EmailConfirmationObserver(BookingObserver):
    def on_booking_confirmed(self, booking: Booking) -> None:
        seat_ids = ", ".join(s.seat_id for s in booking.seats)
        print(f"[email] booking {booking.booking_id} confirmed for {booking.user} "
              f"- seats {seat_ids} - {booking.show.movie.title}")


class SmsConfirmationObserver(BookingObserver):
    def on_booking_confirmed(self, booking: Booking) -> None:
        print(f"[sms] your seats ({len(booking.seats)}) for {booking.show.movie.title} are booked. "
              f"ref: {booking.booking_id}")


class BookingService:
    """Owns the lock -> pay -> confirm workflow and fans out confirmation events."""

    def __init__(self):
        self._observers: list[BookingObserver] = []
        self._bookings: dict[str, Booking] = {}
        self._counter = itertools.count(1)

    def add_observer(self, observer: BookingObserver) -> None:
        self._observers.append(observer)

    def lock_seats(self, show: Show, seat_ids: list[str]) -> list[Seat]:
        locked: list[Seat] = []
        for seat_id in seat_ids:
            seat = show.seats.get(seat_id)
            if seat is None or not seat.lock():
                for s in locked:
                    s.release()
                raise ValueError(f"seat {seat_id} is not available")
            locked.append(seat)
        return locked

    def confirm_booking(self, show: Show, seats: list[Seat], user: str) -> Booking:
        booking_id = f"BK{next(self._counter):04d}"
        amount = sum(show.price_for(s) for s in seats)
        payment = Payment(amount)
        booking = Booking(booking_id, show, seats, user, payment=payment)

        if not payment.process():
            for seat in seats:
                seat.release()
            booking.status = BookingStatus.FAILED
            return booking

        for seat in seats:
            seat.book()
        booking.status = BookingStatus.CONFIRMED
        self._bookings[booking_id] = booking
        self._notify(booking)
        return booking

    def _notify(self, booking: Booking) -> None:
        for observer in self._observers:
            observer.on_booking_confirmed(booking)


def main() -> None:
    movie = Movie("Interstellar", 169)
    theater = Theater("PVR Orion Mall", "Bengaluru")
    show = Show(movie, theater, datetime(2026, 7, 14, 19, 30), rows=3, seats_per_row=5)

    service = BookingService()
    service.add_observer(EmailConfirmationObserver())
    service.add_observer(SmsConfirmationObserver())

    print(f"show: {movie.title} at {theater.name}, {show.start_time:%Y-%m-%d %H:%M}")
    print("seat map before booking:")
    print(show.seat_map())

    print("\nlocking seats A1, A2 for booking...")
    seats = service.lock_seats(show, ["A1", "A2"])
    print("seat map after locking:")
    print(show.seat_map())

    booking = service.confirm_booking(show, seats, user="bindu")
    print(f"\nbooking status: {booking.status.name}, amount paid: {booking.payment.amount}")
    print("seat map after booking:")
    print(show.seat_map())

    print("\nattempting to book an already-booked seat (A1) again...")
    try:
        service.lock_seats(show, ["A1", "B3"])
    except ValueError as exc:
        print(f"booking rejected as expected: {exc}")
    print("seat map unaffected:")
    print(show.seat_map())


if __name__ == "__main__":
    main()
