import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        MeetingRoom roomA = new MeetingRoom("Room-A");
        MeetingRoom roomB = new MeetingRoom("Room-B");
        Scheduler scheduler = new Scheduler();

        Person alice = new Person("Alice");
        Person bob = new Person("Bob");
        Person carol = new Person("Carol");

        LocalDateTime s1 = LocalDateTime.of(2024, 6, 10, 10, 0);
        LocalDateTime e1 = LocalDateTime.of(2024, 6, 10, 11, 0);

        System.out.println("=== booking Sprint Planning in Room-A, 10:00-11:00 ===");
        scheduler.schedule("Sprint Planning", roomA, s1, e1, alice, List.of(bob, carol));

        System.out.println("\n=== booking Design Review in Room-A, 10:30-11:30 (overlaps) ===");
        LocalDateTime s2 = LocalDateTime.of(2024, 6, 10, 10, 30);
        LocalDateTime e2 = LocalDateTime.of(2024, 6, 10, 11, 30);
        scheduler.schedule("Design Review", roomA, s2, e2, bob, List.of(alice));

        System.out.println("\n=== booking Retro in Room-A, 11:00-12:00 (back-to-back, no overlap) ===");
        LocalDateTime s3 = LocalDateTime.of(2024, 6, 10, 11, 0);
        LocalDateTime e3 = LocalDateTime.of(2024, 6, 10, 12, 0);
        scheduler.schedule("Retro", roomA, s3, e3, carol, List.of(alice, bob));

        System.out.println("\n=== booking 1:1 in Room-B, same 10:00-11:00 slot (different room, fine) ===");
        scheduler.schedule("1:1", roomB, s1, e1, bob, List.of(alice));
    }
}

interface Attendee {
    void onMeetingScheduled(Meeting meeting);

    void onMeetingRejected(String reason, Meeting attempted);
}

class Person implements Attendee {
    private final String name;

    Person(String name) {
        this.name = name;
    }

    @Override
    public void onMeetingScheduled(Meeting meeting) {
        System.out.println("  [notify] " + name + ": booked for \"" + meeting.getTitle()
                + "\" in " + meeting.getRoom().getName()
                + " (" + meeting.getStart() + " - " + meeting.getEnd() + ")");
    }

    @Override
    public void onMeetingRejected(String reason, Meeting attempted) {
        System.out.println("  [notify] " + name + ": \"" + attempted.getTitle()
                + "\" was NOT booked - " + reason);
    }
}

class MeetingRoom {
    private final String name;
    private final List<Meeting> bookings = new ArrayList<>();

    MeetingRoom(String name) {
        this.name = name;
    }

    String getName() {
        return name;
    }

    List<Meeting> getBookings() {
        return bookings;
    }

    void addBooking(Meeting meeting) {
        bookings.add(meeting);
    }
}

class Meeting {
    private final String title;
    private final MeetingRoom room;
    private final LocalDateTime start;
    private final LocalDateTime end;
    private final Attendee organizer;
    private final List<Attendee> attendees;

    Meeting(String title, MeetingRoom room, LocalDateTime start, LocalDateTime end,
            Attendee organizer, List<Attendee> attendees) {
        this.title = title;
        this.room = room;
        this.start = start;
        this.end = end;
        this.organizer = organizer;
        this.attendees = attendees;
    }

    // Standard half-open interval overlap: [start, end) intersects [otherStart, otherEnd).
    boolean overlaps(LocalDateTime otherStart, LocalDateTime otherEnd) {
        return start.isBefore(otherEnd) && otherStart.isBefore(end);
    }

    String getTitle() {
        return title;
    }

    MeetingRoom getRoom() {
        return room;
    }

    LocalDateTime getStart() {
        return start;
    }

    LocalDateTime getEnd() {
        return end;
    }

    Attendee getOrganizer() {
        return organizer;
    }

    List<Attendee> getAttendees() {
        return attendees;
    }
}

class Scheduler {

    boolean schedule(String title, MeetingRoom room, LocalDateTime start, LocalDateTime end,
                      Attendee organizer, List<Attendee> attendees) {
        for (Meeting existing : room.getBookings()) {
            if (existing.overlaps(start, end)) {
                String reason = "conflicts with \"" + existing.getTitle() + "\" ("
                        + existing.getStart() + " - " + existing.getEnd() + ") in " + room.getName();
                Meeting attempted = new Meeting(title, room, start, end, organizer, attendees);
                notifyRejected(reason, attempted, organizer, attendees);
                return false;
            }
        }

        Meeting meeting = new Meeting(title, room, start, end, organizer, attendees);
        room.addBooking(meeting);
        notifyScheduled(meeting, organizer, attendees);
        return true;
    }

    private void notifyScheduled(Meeting meeting, Attendee organizer, List<Attendee> attendees) {
        organizer.onMeetingScheduled(meeting);
        for (Attendee attendee : attendees) {
            attendee.onMeetingScheduled(meeting);
        }
    }

    private void notifyRejected(String reason, Meeting attempted, Attendee organizer, List<Attendee> attendees) {
        organizer.onMeetingRejected(reason, attempted);
        for (Attendee attendee : attendees) {
            attendee.onMeetingRejected(reason, attempted);
        }
    }
}
