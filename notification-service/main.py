"""Notification service demo - Strategy for delivery channels, Observer for subscriber management."""

from abc import ABC, abstractmethod
from enum import Enum


class ChannelType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, user: "User", message: str):
        ...


class EmailChannel(NotificationChannel):
    def send(self, user: "User", message: str):
        print(f"[EMAIL -> {user.email}] {message}")


class SmsChannel(NotificationChannel):
    def send(self, user: "User", message: str):
        print(f"[SMS -> {user.phone}] {message}")


class PushChannel(NotificationChannel):
    def send(self, user: "User", message: str):
        print(f"[PUSH -> device:{user.device_id}] {message}")


CHANNEL_REGISTRY: dict[ChannelType, NotificationChannel] = {
    ChannelType.EMAIL: EmailChannel(),
    ChannelType.SMS: SmsChannel(),
    ChannelType.PUSH: PushChannel(),
}


class User:
    def __init__(self, name: str, email: str, phone: str, device_id: str):
        self.name = name
        self.email = email
        self.phone = phone
        self.device_id = device_id

    def __repr__(self):
        return f"User({self.name})"


class Notifier:
    """Subject in the Observer pattern - keeps subscribers and broadcasts to them."""

    def __init__(self):
        self._subscribers: dict[User, list[ChannelType]] = {}

    def subscribe(self, user: User, channels: list[ChannelType]):
        self._subscribers[user] = channels
        print(f"{user.name} subscribed via {[c.value for c in channels]}")

    def unsubscribe(self, user: User):
        if self._subscribers.pop(user, None) is not None:
            print(f"{user.name} unsubscribed")

    def notify_all(self, message: str):
        print(f'-- broadcasting: "{message}" --')
        for user, channels in self._subscribers.items():
            for channel_type in channels:
                CHANNEL_REGISTRY[channel_type].send(user, message)


def main():
    alice = User("Alice", "alice@example.com", "555-0100", "dev-alice-1")
    bob = User("Bob", "bob@example.com", "555-0101", "dev-bob-1")
    carol = User("Carol", "carol@example.com", "555-0102", "dev-carol-1")

    notifier = Notifier()
    notifier.subscribe(alice, [ChannelType.EMAIL])
    notifier.subscribe(bob, [ChannelType.SMS, ChannelType.PUSH])
    notifier.subscribe(carol, [ChannelType.PUSH])

    print()
    notifier.notify_all("Your order has shipped!")

    print()
    notifier.unsubscribe(bob)

    print()
    notifier.notify_all("Flash sale starts in 1 hour!")


if __name__ == "__main__":
    main()
