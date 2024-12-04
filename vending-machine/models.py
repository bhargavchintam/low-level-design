from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Product:
    name: str
    price: float


@dataclass
class Slot:
    code: str
    product: Product
    quantity: int

    def in_stock(self) -> bool:
        return self.quantity > 0

    def dispense_one(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"slot {self.code} is empty")
        self.quantity -= 1


class Inventory:
    def __init__(self) -> None:
        self._slots: Dict[str, Slot] = {}

    def add_slot(self, slot: Slot) -> None:
        self._slots[slot.code] = slot

    def get(self, code: str) -> Optional[Slot]:
        return self._slots.get(code)

    def slots(self):
        return self._slots.values()
