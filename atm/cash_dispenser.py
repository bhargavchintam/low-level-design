from typing import Dict, Optional


class CashDispenser:
    def __init__(self, denominations: Dict[int, int]) -> None:
        # note value -> count of notes currently loaded
        self.denominations = dict(denominations)

    def can_dispense(self, amount: int) -> bool:
        return self._breakdown(amount) is not None

    def dispense(self, amount: int) -> Dict[int, int]:
        breakdown = self._breakdown(amount)
        if breakdown is None:
            raise ValueError(f"cannot dispense {amount} with available denominations")
        for note, count in breakdown.items():
            self.denominations[note] -= count
        return breakdown

    def _breakdown(self, amount: int) -> Optional[Dict[int, int]]:
        # greedy from largest denomination down - good enough for a demo dispenser
        remaining = amount
        breakdown: Dict[int, int] = {}
        for note in sorted(self.denominations, reverse=True):
            if remaining <= 0:
                break
            available = self.denominations[note]
            count = min(available, remaining // note)
            if count > 0:
                breakdown[note] = count
                remaining -= count * note
        return breakdown if remaining == 0 else None
