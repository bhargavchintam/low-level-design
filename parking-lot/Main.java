import java.util.*;
import java.time.Duration;
import java.time.LocalDateTime;

public class Main {
    public static void main(String[] args) {
        ParkingLot lot = new ParkingLot("Reva Mall Parking", new HourlyFeeStrategy());
        lot.addFloor(new ParkingFloor(1, List.of(
                new ParkingSpot("1-S1", SpotType.SMALL),
                new ParkingSpot("1-M1", SpotType.MEDIUM),
                new ParkingSpot("1-M2", SpotType.MEDIUM),
                new ParkingSpot("1-L1", SpotType.LARGE)
        )));
        lot.addFloor(new ParkingFloor(2, List.of(
                new ParkingSpot("2-M1", SpotType.MEDIUM),
                new ParkingSpot("2-L1", SpotType.LARGE)
        )));

        Vehicle bike = new Vehicle("KA-01-AA-1111", VehicleType.MOTORCYCLE);
        Vehicle car1 = new Vehicle("KA-01-BB-2222", VehicleType.CAR);
        Vehicle car2 = new Vehicle("KA-01-CC-3333", VehicleType.CAR);
        Vehicle bus = new Vehicle("KA-01-DD-4444", VehicleType.BUS);

        System.out.println("--- Parking vehicles ---");
        Ticket t1 = lot.park(bike);
        printTicket(t1);
        Ticket t2 = lot.park(car1);
        printTicket(t2);
        Ticket t3 = lot.park(car2);
        printTicket(t3);
        Ticket t4 = lot.park(bus);
        printTicket(t4);

        // floor 1 only had two MEDIUM spots, so a third car should spill over to floor 2
        Vehicle car3 = new Vehicle("KA-01-EE-5555", VehicleType.CAR);
        Ticket t5 = lot.park(car3);
        printTicket(t5);

        System.out.println("\n--- Lot occupancy ---");
        lot.printStatus();

        System.out.println("\n--- Unparking car1 after a simulated 3.5 hour stay ---");
        t2.setEntryTime(LocalDateTime.now().minusMinutes(210));
        double fee = lot.unpark(t2);
        System.out.printf("Vehicle %s left spot %s, fee charged: Rs.%.2f%n", car1.getLicensePlate(), t2.getSpot().getId(), fee);

        System.out.println("\n--- Lot occupancy after unparking ---");
        lot.printStatus();
    }

    private static void printTicket(Ticket ticket) {
        if (ticket == null) {
            System.out.println("Parking failed: lot is full for this vehicle type");
            return;
        }
        System.out.printf("Issued ticket %s -> vehicle %s parked at %s (floor %d)%n",
                ticket.getId(), ticket.getVehicle().getLicensePlate(), ticket.getSpot().getId(), ticket.getSpot().getFloorNumber());
    }
}

enum VehicleType {
    MOTORCYCLE, CAR, BUS
}

enum SpotType {
    SMALL, MEDIUM, LARGE;

    // whether a vehicle of the given type can use a spot of this type
    boolean fits(VehicleType type) {
        return switch (type) {
            case MOTORCYCLE -> true; // motorcycles fit anywhere
            case CAR -> this == MEDIUM || this == LARGE;
            case BUS -> this == LARGE;
        };
    }
}

class Vehicle {
    private final String licensePlate;
    private final VehicleType type;

    Vehicle(String licensePlate, VehicleType type) {
        this.licensePlate = licensePlate;
        this.type = type;
    }

    String getLicensePlate() {
        return licensePlate;
    }

    VehicleType getType() {
        return type;
    }
}

class ParkingSpot {
    private final String id;
    private final SpotType type;
    private int floorNumber;
    private Vehicle occupiedBy;

    ParkingSpot(String id, SpotType type) {
        this.id = id;
        this.type = type;
    }

    String getId() {
        return id;
    }

    SpotType getType() {
        return type;
    }

    int getFloorNumber() {
        return floorNumber;
    }

    void setFloorNumber(int floorNumber) {
        this.floorNumber = floorNumber;
    }

    boolean isFree() {
        return occupiedBy == null;
    }

    void occupy(Vehicle vehicle) {
        this.occupiedBy = vehicle;
    }

    void release() {
        this.occupiedBy = null;
    }
}

class ParkingFloor {
    private final int floorNumber;
    private final List<ParkingSpot> spots;

    ParkingFloor(int floorNumber, List<ParkingSpot> spots) {
        this.floorNumber = floorNumber;
        this.spots = new ArrayList<>(spots);
        this.spots.forEach(s -> s.setFloorNumber(floorNumber));
    }

    int getFloorNumber() {
        return floorNumber;
    }

    Optional<ParkingSpot> findSpotFor(VehicleType type) {
        return spots.stream()
                .filter(ParkingSpot::isFree)
                .filter(s -> s.getType().fits(type))
                .min(Comparator.comparing(s -> s.getType().ordinal())); // prefer the tightest fit first
    }

    List<ParkingSpot> getSpots() {
        return spots;
    }
}

class Ticket {
    private final String id;
    private final Vehicle vehicle;
    private final ParkingSpot spot;
    private LocalDateTime entryTime;

    Ticket(String id, Vehicle vehicle, ParkingSpot spot) {
        this.id = id;
        this.vehicle = vehicle;
        this.spot = spot;
        this.entryTime = LocalDateTime.now();
    }

    String getId() {
        return id;
    }

    Vehicle getVehicle() {
        return vehicle;
    }

    ParkingSpot getSpot() {
        return spot;
    }

    LocalDateTime getEntryTime() {
        return entryTime;
    }

    void setEntryTime(LocalDateTime entryTime) {
        this.entryTime = entryTime;
    }
}

// using strategy here so pricing rules can vary per vehicle type without touching ParkingLot
interface FeeStrategy {
    double calculateFee(Ticket ticket, LocalDateTime exitTime);
}

class HourlyFeeStrategy implements FeeStrategy {
    private final Map<VehicleType, Double> hourlyRate = Map.of(
            VehicleType.MOTORCYCLE, 10.0,
            VehicleType.CAR, 20.0,
            VehicleType.BUS, 50.0
    );

    @Override
    public double calculateFee(Ticket ticket, LocalDateTime exitTime) {
        long minutes = Duration.between(ticket.getEntryTime(), exitTime).toMinutes();
        double hours = Math.max(1, Math.ceil(minutes / 60.0)); // partial hour rounds up, minimum 1 hour
        return hours * hourlyRate.get(ticket.getVehicle().getType());
    }
}

class ParkingLot {
    private final String name;
    private final List<ParkingFloor> floors = new ArrayList<>();
    private final FeeStrategy feeStrategy;
    private final Map<String, Ticket> activeTickets = new HashMap<>();
    private int ticketSequence = 1;

    ParkingLot(String name, FeeStrategy feeStrategy) {
        this.name = name;
        this.feeStrategy = feeStrategy;
    }

    void addFloor(ParkingFloor floor) {
        floors.add(floor);
    }

    Ticket park(Vehicle vehicle) {
        for (ParkingFloor floor : floors) {
            Optional<ParkingSpot> spot = floor.findSpotFor(vehicle.getType());
            if (spot.isPresent()) {
                spot.get().occupy(vehicle);
                Ticket ticket = new Ticket("T-" + ticketSequence++, vehicle, spot.get());
                activeTickets.put(ticket.getId(), ticket);
                return ticket;
            }
        }
        return null; // lot full for this vehicle type
    }

    double unpark(Ticket ticket) {
        double fee = feeStrategy.calculateFee(ticket, LocalDateTime.now());
        ticket.getSpot().release();
        activeTickets.remove(ticket.getId());
        return fee;
    }

    void printStatus() {
        for (ParkingFloor floor : floors) {
            long free = floor.getSpots().stream().filter(ParkingSpot::isFree).count();
            System.out.printf("Floor %d: %d/%d free%n", floor.getFloorNumber(), free, floor.getSpots().size());
            for (ParkingSpot spot : floor.getSpots()) {
                System.out.printf("  %s [%s] - %s%n", spot.getId(), spot.getType(), spot.isFree() ? "free" : "occupied");
            }
        }
    }
}
