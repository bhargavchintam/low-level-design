from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Card:
    card_number: str
    pin: str


class Account:
    def __init__(self, account_number: str, balance: float) -> None:
        self.account_number = account_number
        self.balance = balance

    def has_sufficient_balance(self, amount: float) -> bool:
        return self.balance >= amount

    def withdraw(self, amount: float) -> None:
        if not self.has_sufficient_balance(amount):
            raise ValueError("insufficient balance")
        self.balance -= amount


class Bank:
    def __init__(self) -> None:
        self._cards: Dict[str, Card] = {}
        self._accounts: Dict[str, Account] = {}

    def register(self, card: Card, account: Account) -> None:
        self._cards[card.card_number] = card
        self._accounts[card.card_number] = account

    def get_card(self, card_number: str) -> Optional[Card]:
        return self._cards.get(card_number)

    def verify_pin(self, card_number: str, pin: str) -> bool:
        card = self._cards.get(card_number)
        return card is not None and card.pin == pin

    def get_account(self, card_number: str) -> Optional[Account]:
        return self._accounts.get(card_number)
