import java.util.*;

public class Main {
    public static void main(String[] args) {
        ElevatorController controller = new ElevatorController(
                List.of(new Elevator(1, 1), new Elevator(2, 8)),
                new NearestElevatorStrategy()
        );

        System.out.println("--- Hall calls coming in ---");
        controller.requestElevator(3, Direction.UP, 9);
        controller.requestElevator(6, Direction.DOWN, 2);
        controller.requestElevator(1, Direction.UP, 5);

        System.out.println("\n--- Simulating floor-by-floor movement ---");
        controller.run();

        System.out.println("\nAll elevators idle. Final positions:");
        controller.printStatus();
    }
}

enum Direction {
    UP, DOWN, IDLE
}

interface ElevatorState {
    void handle(Elevator elevator);

    String name();
}

class IdleState implements ElevatorState {
    @Override
    public void handle(Elevator elevator) {
        if (elevator.getStops().isEmpty()) {
            return; // nothing requested, stay put
        }
        int next = elevator.nearestStop();
        if (next > elevator.getCurrentFloor()) {
            elevator.setState(new MovingUpState());
        } else if (next < elevator.getCurrentFloor()) {
            elevator.setState(new MovingDownState());
        } else {
            elevator.setState(new DoorsOpenState());
        }
    }

    @Override
    public String name() {
        return "IDLE";
    }
}

class MovingUpState implements ElevatorState {
    @Override
    public void handle(Elevator elevator) {
        elevator.setCurrentFloor(elevator.getCurrentFloor() + 1);
        System.out.printf("  Elevator #%d moving up -> floor %d%n", elevator.getId(), elevator.getCurrentFloor());
        if (elevator.getStops().contains(elevator.getCurrentFloor())) {
            elevator.setState(new DoorsOpenState());
        }
    }

    @Override
    public String name() {
        return "MOVING_UP";
    }
}

class MovingDownState implements ElevatorState {
    @Override
    public void handle(Elevator elevator) {
        elevator.setCurrentFloor(elevator.getCurrentFloor() - 1);
        System.out.printf("  Elevator #%d moving down -> floor %d%n", elevator.getId(), elevator.getCurrentFloor());
        if (elevator.getStops().contains(elevator.getCurrentFloor())) {
            elevator.setState(new DoorsOpenState());
        }
    }

    @Override
    public String name() {
        return "MOVING_DOWN";
    }
}

class DoorsOpenState implements ElevatorState {
    @Override
    public void handle(Elevator elevator) {
        System.out.printf("  Elevator #%d doors open at floor %d, doors closing%n", elevator.getId(), elevator.getCurrentFloor());
        elevator.getStops().remove(elevator.getCurrentFloor());
        if (elevator.getStops().isEmpty()) {
            elevator.setState(new IdleState());
        } else {
            int next = elevator.nearestStop();
            elevator.setState(next > elevator.getCurrentFloor() ? new MovingUpState() : new MovingDownState());
        }
    }

    @Override
    public String name() {
        return "DOORS_OPEN";
    }
}

class Elevator {
    private final int id;
    private int currentFloor;
    private ElevatorState state = new IdleState();
    private final TreeSet<Integer> stops = new TreeSet<>();

    Elevator(int id, int startFloor) {
        this.id = id;
        this.currentFloor = startFloor;
    }

    int getId() {
        return id;
    }

    int getCurrentFloor() {
        return currentFloor;
    }

    void setCurrentFloor(int floor) {
        this.currentFloor = floor;
    }

    ElevatorState getState() {
        return state;
    }

    void setState(ElevatorState state) {
        this.state = state;
    }

    TreeSet<Integer> getStops() {
        return stops;
    }

    void addStop(int floor) {
        stops.add(floor);
    }

    int nearestStop() {
        return stops.stream()
                .min(Comparator.comparingInt(f -> Math.abs(f - currentFloor)))
                .orElse(currentFloor);
    }

    boolean isIdle() {
        return state instanceof IdleState && stops.isEmpty();
    }

    void step() {
        state.handle(this);
    }

    @Override
    public String toString() {
        return String.format("Elevator #%d [floor=%d, state=%s, pendingStops=%s]", id, currentFloor, state.name(), stops);
    }
}

// picks whichever elevator is physically closest to the hall call floor
interface DispatchStrategy {
    Elevator select(List<Elevator> elevators, int floor);
}

class NearestElevatorStrategy implements DispatchStrategy {
    @Override
    public Elevator select(List<Elevator> elevators, int floor) {
        return elevators.stream()
                .min(Comparator.comparingInt(e -> Math.abs(e.getCurrentFloor() - floor)))
                .orElseThrow();
    }
}

class ElevatorController {
    private final List<Elevator> elevators;
    private final DispatchStrategy dispatchStrategy;

    ElevatorController(List<Elevator> elevators, DispatchStrategy dispatchStrategy) {
        this.elevators = elevators;
        this.dispatchStrategy = dispatchStrategy;
    }

    void requestElevator(int originFloor, Direction direction, int destinationFloor) {
        Elevator chosen = dispatchStrategy.select(elevators, originFloor);
        System.out.printf("Hall call: floor %d going %s -> dispatched Elevator #%d (currently at floor %d)%n",
                originFloor, direction, chosen.getId(), chosen.getCurrentFloor());
        chosen.addStop(originFloor);
        chosen.addStop(destinationFloor);
    }

    void run() {
        int tick = 1;
        int maxTicks = 200; // safety guard against an infinite loop bug
        while (!allIdle() && tick <= maxTicks) {
            System.out.printf(" tick %d:%n", tick);
            for (Elevator e : elevators) {
                if (!e.isIdle()) {
                    e.step();
                }
            }
            tick++;
        }
    }

    boolean allIdle() {
        return elevators.stream().allMatch(Elevator::isIdle);
    }

    void printStatus() {
        elevators.forEach(e -> System.out.println("  " + e));
    }
}
