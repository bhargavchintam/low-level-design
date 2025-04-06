import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class Main {
    public static void main(String[] args) {
        Hotel hotel = new Hotel("Lakeview Grand");
        hotel.addRoom(RoomFactory.create(RoomType.SINGLE, "101"));
        hotel.addRoom(RoomFactory.create(RoomType.SINGLE, "102"));
        hotel.addRoom(RoomFactory.create(RoomType.DOUBLE, "201"));
        hotel.addRoom(RoomFactory.create(RoomType.DELUXE, "301"));

        LocalDate checkIn = LocalDate.of(2026, 7, 17);  // Friday
        LocalDate checkOut = LocalDate.of(2026, 7, 20); // Monday - spans a weekend

        System.out.println("Available DELUXE rooms for " + checkIn + " to " + checkOut + ":");
        List<Room> available = hotel.searchAvailable(RoomType.DELUXE, checkIn, checkOut);
        for (Room r : available) {
            System.out.println("  " + r);
        }

        Guest guest = new Guest("Bindu Bhargava", "bindubhargavareddy@gmail.com");
        Room room = available.get(0);
        PricingStrategy pricing = new WeekendPricingStrategy();

        Reservation reservation = hotel.book(room, guest, checkIn, checkOut, pricing);
        System.out.println("\nBooked room " + room.getRoomNumber() + " for " + guest.getName()
                + ", status " + reservation.getStatus());

        System.out.println("\nSame room available for the same range now? "
                + !hotel.searchAvailable(RoomType.DELUXE, checkIn, checkOut).contains(room));

        Invoice invoice = hotel.checkout(reservation);
        System.out.println("\n--- Invoice ---");
        System.out.println("Room:        " + invoice.getRoomNumber());
        System.out.println("Nights:      " + invoice.getNights());
        System.out.println("Base rate:   Rs." + invoice.getBaseRate() + "/night");
        System.out.printf ("Total:       Rs.%.2f%n", invoice.getTotal());
        System.out.println("Reservation status after checkout: " + reservation.getStatus());
        System.out.println("Room status after checkout: " + room.getStatus());
    }
}

enum RoomType { SINGLE, DOUBLE, DELUXE }

enum RoomStatus { AVAILABLE, BOOKED, MAINTENANCE }

enum ReservationStatus { RESERVED, CHECKED_IN, COMPLETED, CANCELLED }

class Room {
    private final String roomNumber;
    private final RoomType type;
    private final double baseRate;
    private RoomStatus status = RoomStatus.AVAILABLE;

    Room(String roomNumber, RoomType type, double baseRate) {
        this.roomNumber = roomNumber;
        this.type = type;
        this.baseRate = baseRate;
    }

    String getRoomNumber() { return roomNumber; }
    RoomType getType() { return type; }
    double getBaseRate() { return baseRate; }
    RoomStatus getStatus() { return status; }
    void setStatus(RoomStatus status) { this.status = status; }

    @Override
    public String toString() {
        return String.format("%s room %s, base Rs.%.0f/night, %s", type, roomNumber, baseRate, status);
    }
}

class RoomFactory {
    static Room create(RoomType type, String roomNumber) {
        switch (type) {
            case SINGLE: return new Room(roomNumber, RoomType.SINGLE, 2000.0);
            case DOUBLE: return new Room(roomNumber, RoomType.DOUBLE, 3500.0);
            case DELUXE: return new Room(roomNumber, RoomType.DELUXE, 6000.0);
            default: throw new IllegalArgumentException("unknown room type: " + type);
        }
    }
}

interface PricingStrategy {
    double priceFor(Room room, LocalDate checkIn, LocalDate checkOut);
}

/** Weekday nights at base rate, Fri/Sat nights at a premium. */
class WeekendPricingStrategy implements PricingStrategy {
    private static final double WEEKEND_MULTIPLIER = 1.3;

    @Override
    public double priceFor(Room room, LocalDate checkIn, LocalDate checkOut) {
        double total = 0;
        for (LocalDate date = checkIn; date.isBefore(checkOut); date = date.plusDays(1)) {
            boolean weekendNight = date.getDayOfWeek() == DayOfWeek.FRIDAY || date.getDayOfWeek() == DayOfWeek.SATURDAY;
            total += weekendNight ? room.getBaseRate() * WEEKEND_MULTIPLIER : room.getBaseRate();
        }
        return total;
    }
}

class Guest {
    private final String name;
    private final String email;

    Guest(String name, String email) {
        this.name = name;
        this.email = email;
    }

    String getName() { return name; }
    String getEmail() { return email; }
}

class Reservation {
    private final String id;
    private final Room room;
    private final Guest guest;
    private final LocalDate checkIn;
    private final LocalDate checkOut;
    private final PricingStrategy pricingStrategy;
    private ReservationStatus status;

    Reservation(Room room, Guest guest, LocalDate checkIn, LocalDate checkOut, PricingStrategy pricingStrategy) {
        this.id = UUID.randomUUID().toString().substring(0, 8);
        this.room = room;
        this.guest = guest;
        this.checkIn = checkIn;
        this.checkOut = checkOut;
        this.pricingStrategy = pricingStrategy;
        this.status = ReservationStatus.RESERVED;
    }

    String getId() { return id; }
    Room getRoom() { return room; }
    Guest getGuest() { return guest; }
    LocalDate getCheckIn() { return checkIn; }
    LocalDate getCheckOut() { return checkOut; }
    PricingStrategy getPricingStrategy() { return pricingStrategy; }
    ReservationStatus getStatus() { return status; }
    void setStatus(ReservationStatus status) { this.status = status; }

    boolean overlaps(LocalDate otherCheckIn, LocalDate otherCheckOut) {
        return checkIn.isBefore(otherCheckOut) && otherCheckIn.isBefore(checkOut);
    }
}

class Invoice {
    private final String roomNumber;
    private final long nights;
    private final double baseRate;
    private final double total;

    Invoice(String roomNumber, long nights, double baseRate, double total) {
        this.roomNumber = roomNumber;
        this.nights = nights;
        this.baseRate = baseRate;
        this.total = total;
    }

    String getRoomNumber() { return roomNumber; }
    long getNights() { return nights; }
    double getBaseRate() { return baseRate; }
    double getTotal() { return total; }
}

class Hotel {
    private final String name;
    private final List<Room> rooms = new ArrayList<>();
    private final List<Reservation> reservations = new ArrayList<>();

    Hotel(String name) { this.name = name; }

    void addRoom(Room room) { rooms.add(room); }

    List<Room> searchAvailable(RoomType type, LocalDate checkIn, LocalDate checkOut) {
        List<Room> result = new ArrayList<>();
        for (Room room : rooms) {
            if (room.getType() != type || room.getStatus() == RoomStatus.MAINTENANCE) {
                continue;
            }
            if (isFreeForRange(room, checkIn, checkOut)) {
                result.add(room);
            }
        }
        return result;
    }

    private boolean isFreeForRange(Room room, LocalDate checkIn, LocalDate checkOut) {
        for (Reservation r : reservations) {
            if (r.getRoom() != room) continue;
            if (r.getStatus() == ReservationStatus.CANCELLED || r.getStatus() == ReservationStatus.COMPLETED) continue;
            if (r.overlaps(checkIn, checkOut)) return false;
        }
        return true;
    }

    Reservation book(Room room, Guest guest, LocalDate checkIn, LocalDate checkOut, PricingStrategy pricingStrategy) {
        if (!isFreeForRange(room, checkIn, checkOut)) {
            throw new IllegalStateException("room " + room.getRoomNumber() + " is not free for that range");
        }
        Reservation reservation = new Reservation(room, guest, checkIn, checkOut, pricingStrategy);
        reservations.add(reservation);
        room.setStatus(RoomStatus.BOOKED);
        return reservation;
    }

    Invoice checkout(Reservation reservation) {
        if (reservation.getStatus() == ReservationStatus.CANCELLED || reservation.getStatus() == ReservationStatus.COMPLETED) {
            throw new IllegalStateException("reservation already closed");
        }
        double total = reservation.getPricingStrategy().priceFor(
                reservation.getRoom(), reservation.getCheckIn(), reservation.getCheckOut());
        long nights = java.time.temporal.ChronoUnit.DAYS.between(reservation.getCheckIn(), reservation.getCheckOut());
        reservation.setStatus(ReservationStatus.COMPLETED);
        reservation.getRoom().setStatus(RoomStatus.AVAILABLE);
        return new Invoice(reservation.getRoom().getRoomNumber(), nights, reservation.getRoom().getBaseRate(), total);
    }
}
