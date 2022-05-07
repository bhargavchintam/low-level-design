# Notification Service

## Problem
Design a notification service that can broadcast a message to a set of subscribed users, where each user can receive it through one or more delivery channels (email, SMS, push). Users can subscribe and unsubscribe at any time, and adding a new delivery channel shouldn't require changing the broadcast logic.

## Design
- `ChannelType` (enum) - `EMAIL`, `SMS`, `PUSH`, the fixed set of supported delivery mechanisms.
- `NotificationChannel` (ABC) - defines `send(user, message)`; `EmailChannel`, `SmsChannel`, `PushChannel` are concrete delivery strategies.
- `User` - plain data holder for a subscriber's contact details (email, phone, device id).
- `Notifier` - the subject: holds a map of subscribed `User` -> list of preferred `ChannelType`s, with `subscribe`, `unsubscribe`, and `notify_all` (broadcast) methods.

## Patterns used
- **Strategy** - `NotificationChannel` implementations are interchangeable delivery algorithms selected per user preference, looked up via a small channel registry.
- **Observer** - `Notifier` is the subject and subscribed `User`s are observers; `notify_all` pushes an update to every currently-subscribed observer, and `unsubscribe` removes them from future broadcasts.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/notification-service
python3 main.py
```
