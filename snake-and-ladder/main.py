import random
from abc import ABC, abstractmethod


class Dice(ABC):
    @abstractmethod
    def roll(self) -> int:
        """Return a value between 1 and 6."""


class StandardDice(Dice):
    """Swappable dice implementation - the Strategy angle. A LoadedDice or TwoDiceSum could drop in here."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def roll(self) -> int:
        return self._rng.randint(1, 6)


class Player:
    def __init__(self, name: str):
        self.name = name
        self.position = 0


class Board:
    FINAL_SQUARE = 100

    def __init__(self, snakes: dict[int, int], ladders: dict[int, int]):
        self.snakes = snakes
        self.ladders = ladders

    def resolve(self, square: int) -> int:
        if square in self.snakes:
            return self.snakes[square]
        if square in self.ladders:
            return self.ladders[square]
        return square


class Game:
    MAX_TURNS = 2000

    def __init__(self, board: Board, players: list[Player], dice: Dice):
        self.board = board
        self.players = players
        self.dice = dice

    def play(self) -> None:
        for turn in range(self.MAX_TURNS):
            player = self.players[turn % len(self.players)]
            roll = self.dice.roll()
            target = player.position + roll

            if target > self.board.FINAL_SQUARE:
                print(f"{player.name} rolls {roll}, stays at {player.position} (overshoots {self.board.FINAL_SQUARE})")
                continue

            player.position = target
            message = f"{player.name} rolls {roll}, moves to {player.position}"

            landed_on = self.board.resolve(player.position)
            if landed_on != player.position:
                kind = "snake" if player.position in self.board.snakes else "ladder"
                message += f", hits a {kind} -> {landed_on}"
                player.position = landed_on

            print(message)

            if player.position == self.board.FINAL_SQUARE:
                print(f"\n{player.name} wins in {turn + 1} turns!")
                return

        print("No winner within turn limit")


def main():
    ladders = {2: 38, 7: 14, 8: 31, 15: 26, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 78: 98, 87: 94}
    snakes = {16: 6, 46: 25, 49: 11, 62: 19, 64: 60, 74: 53, 89: 68, 92: 88, 95: 75, 99: 80}
    board = Board(snakes=snakes, ladders=ladders)

    players = [Player("Alice"), Player("Bob"), Player("Carol")]
    dice = StandardDice(seed=42)

    game = Game(board, players, dice)
    game.play()


if __name__ == "__main__":
    main()
