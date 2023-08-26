import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class Main {
    public static void main(String[] args) {
        RentalBranch branch = new RentalBranch("Koramangala Branch");
        branch.addVehicle(VehicleFactory.create(VehicleType.CAR, "KA-01-AB-1234"));
        branch.addVehicle(VehicleFactory.create(VehicleType.CAR, "KA-01-AB-5678"));
        branch.addVehicle(VehicleFactory.create(VehicleType.SUV, "KA-01-CD-1111"));
        branch.addVehicle(VehicleFactory.create(VehicleType.BIKE, "KA-01-EF-2222"));

        System.out.println("Available cars:");
        for (Vehicle v : branch.searchAvailable(VehicleType.CAR)) {
            System.out.println("  " + v);
        }

        Vehicle chosen = branch.searchAvailable(VehicleType.CAR).get(0);
        LocalDate start = LocalDate.of(2026, 7, 14);
        LocalDate plannedEnd = LocalDate.of(2026, 7, 17);

        Reservation reservation = branch.reserve(chosen, start, plannedEnd, new DailyRateStrategy());
        System.out.println("\nReserved: " + chosen.getPlateNumber() + " -> status " + reservation.getStatus());

        branch.startRental(reservation);
        System.out.println("Rental started, status " + reservation.getStatus());

        LocalDate actualReturn = LocalDate.of(2026, 7, 19);
        double bill = branch.returnVehicle(reservation, actualReturn);
        System.out.printf("Returned on %s, status %s, bill = Rs.%.2f%n", actualReturn, reservation.getStatus(), bill);

        System.out.println("\nAvailable cars after return:");
        for (Vehicle v : branch.searchAvailable(VehicleType.CAR)) {
            System.out.println("  " + v);
        }

        System.out.println("\n-- Weekly pricing example --");
        Vehicle suv = branch.searchAvailable(VehicleType.SUV).get(0);
        Reservation weekly = branch.reserve(suv, start, LocalDate.of(2026, 7, 21), new WeeklyRateStrategy());
        branch.startRental(weekly);
        double weeklyBill = branch.returnVehicle(weekly, LocalDate.of(2026, 7, 21));
        System.out.printf("SUV rented for a week, bill = Rs.%.2f%n", weeklyBill);
    }
}

enum VehicleType { CAR, SUV, BIKE }

enum ReservationStatus { RESERVED, ONGOING, COMPLETED, CANCELLED }

abstract class Vehicle {
    private final String plateNumber;
    private final VehicleType type;
    private final double baseDailyRate;
    private boolean available = true;

    Vehicle(String plateNumber, VehicleType type, double baseDailyRate) {
        this.plateNumber = plateNumber;
        this.type = type;
        this.baseDailyRate = baseDailyRate;
    }

    String getPlateNumber() { return plateNumber; }
    VehicleType getType() { return type; }
    double getBaseDailyRate() { return baseDailyRate; }
    boolean isAvailable() { return available; }
    void setAvailable(boolean available) { this.available = available; }

    @Override
    public String toString() {
        return String.format("%s [%s] plate=%s rate=Rs.%.0f/day", type, getClass().getSimpleName(), plateNumber, baseDailyRate);
    }
}

class Car extends Vehicle {
    Car(String plateNumber) { super(plateNumber, VehicleType.CAR, 1500.0); }
}

class Suv extends Vehicle {
    Suv(String plateNumber) { super(plateNumber, VehicleType.SUV, 2500.0); }
}

class Bike extends Vehicle {
    Bike(String plateNumber) { super(plateNumber, VehicleType.BIKE, 500.0); }
}

class VehicleFactory {
    static Vehicle create(VehicleType type, String plateNumber) {
        switch (type) {
            case CAR: return new Car(plateNumber);
            case SUV: return new Suv(plateNumber);
            case BIKE: return new Bike(plateNumber);
            default: throw new IllegalArgumentException("unknown vehicle type: " + type);
        }
    }
}

interface PricingStrategy {
    double calculateFare(Vehicle vehicle, long days);
}

class DailyRateStrategy implements PricingStrategy {
    @Override
    public double calculateFare(Vehicle vehicle, long days) {
        long billableDays = Math.max(days, 1);
        return billableDays * vehicle.getBaseDailyRate();
    }
}

class WeeklyRateStrategy implements PricingStrategy {
    private static final double WEEKLY_DISCOUNT = 0.85; // 15% off for booking by the week

    @Override
    public double calculateFare(Vehicle vehicle, long days) {
        long weeks = Math.max(1, (days + 6) / 7);
        return weeks * 7 * vehicle.getBaseDailyRate() * WEEKLY_DISCOUNT;
    }
}

class Reservation {
    private final String id;
    private final Vehicle vehicle;
    private final LocalDate startDate;
    private final LocalDate plannedEndDate;
    private final PricingStrategy pricingStrategy;
    private ReservationStatus status;

    Reservation(Vehicle vehicle, LocalDate startDate, LocalDate plannedEndDate, PricingStrategy pricingStrategy) {
        this.id = UUID.randomUUID().toString().substring(0, 8);
        this.vehicle = vehicle;
        this.startDate = startDate;
        this.plannedEndDate = plannedEndDate;
        this.pricingStrategy = pricingStrategy;
        this.status = ReservationStatus.RESERVED;
    }

    String getId() { return id; }
    Vehicle getVehicle() { return vehicle; }
    LocalDate getStartDate() { return startDate; }
    PricingStrategy getPricingStrategy() { return pricingStrategy; }
    ReservationStatus getStatus() { return status; }
    void setStatus(ReservationStatus status) { this.status = status; }
}

class RentalBranch {
    private final String name;
    private final List<Vehicle> fleet = new ArrayList<>();

    RentalBranch(String name) { this.name = name; }

    void addVehicle(Vehicle vehicle) { fleet.add(vehicle); }

    List<Vehicle> searchAvailable(VehicleType type) {
        List<Vehicle> result = new ArrayList<>();
        for (Vehicle v : fleet) {
            if (v.getType() == type && v.isAvailable()) {
                result.add(v);
            }
        }
        return result;
    }

    Reservation reserve(Vehicle vehicle, LocalDate start, LocalDate plannedEnd, PricingStrategy strategy) {
        if (!vehicle.isAvailable()) {
            throw new IllegalStateException("vehicle " + vehicle.getPlateNumber() + " is not available");
        }
        vehicle.setAvailable(false);
        return new Reservation(vehicle, start, plannedEnd, strategy);
    }

    void startRental(Reservation reservation) {
        if (reservation.getStatus() != ReservationStatus.RESERVED) {
            throw new IllegalStateException("reservation must be RESERVED to start");
        }
        reservation.setStatus(ReservationStatus.ONGOING);
    }

    double returnVehicle(Reservation reservation, LocalDate actualReturnDate) {
        if (reservation.getStatus() != ReservationStatus.ONGOING) {
            throw new IllegalStateException("reservation must be ONGOING to return");
        }
        long days = ChronoUnit.DAYS.between(reservation.getStartDate(), actualReturnDate);
        double bill = reservation.getPricingStrategy().calculateFare(reservation.getVehicle(), days);
        reservation.setStatus(ReservationStatus.COMPLETED);
        reservation.getVehicle().setAvailable(true);
        return bill;
    }

    void cancel(Reservation reservation) {
        reservation.setStatus(ReservationStatus.CANCELLED);
        reservation.getVehicle().setAvailable(true);
    }
}
