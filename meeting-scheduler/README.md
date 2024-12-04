# Meeting Scheduler

## Problem
Design a scheduler that books meetings into shared meeting rooms while preventing double-booking. A booking request must be checked against every existing booking in that room for a time overlap, rejected if one exists, and otherwise confirmed - with organizer and attendees notified either way.

## Design
- `MeetingRoom` - a name plus the list of `Meeting`s already booked into it.
- `Meeting` - title, room, start/end `LocalDateTime`, organizer, attendee list, and `overlaps(start, end)` doing a real half-open interval check (`start < otherEnd && otherStart < end`).
- `Attendee` (interface) - the observer contract: `onMeetingScheduled(meeting)`, `onMeetingRejected(reason, attempted)`.
- `Person` - concrete `Attendee` that just prints what it was notified of.
- `Scheduler` - given a room and a proposed time range, scans that room's existing bookings for an overlap; on conflict it notifies the organizer and attendees why the booking failed, otherwise it books the room and notifies everyone it succeeded.

## Patterns used
- **Observer** - `Attendee` is the observer interface; `Scheduler` (the subject) pushes scheduled/rejected events to the organizer and every attendee without knowing what they do with them.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/meeting-scheduler
java Main.java
```
