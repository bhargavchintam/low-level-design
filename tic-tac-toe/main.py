from abc import ABC, abstractmethod
from enum import Enum


class Symbol(Enum):
    X = "X"
    O = "O"
    EMPTY = "-"


class Player(ABC):
    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol

    @abstractmethod
    def next_move(self) -> tuple[int, int]:
        """Return the (row, col) this player wants to play next."""


class HumanPlayer(Player):
    """Stands in for a real human - moves come from a pre-scripted queue so the demo is non-interactive."""

    def __init__(self, name: str, symbol: Symbol, scripted_moves: list[tuple[int, int]]):
        super().__init__(name, symbol)
        self._moves = iter(scripted_moves)

    def next_move(self) -> tuple[int, int]:
        return next(self._moves)


class Board:
    SIZE = 3

    def __init__(self):
        self.grid = [[Symbol.EMPTY for _ in range(self.SIZE)] for _ in range(self.SIZE)]

    def place(self, row: int, col: int, symbol: Symbol) -> None:
        if not (0 <= row < self.SIZE and 0 <= col < self.SIZE):
            raise ValueError(f"({row},{col}) is off the board")
        if self.grid[row][col] != Symbol.EMPTY:
            raise ValueError(f"({row},{col}) is already taken")
        self.grid[row][col] = symbol

    def is_full(self) -> bool:
        return all(cell != Symbol.EMPTY for row in self.grid for cell in row)

    def winner(self) -> Symbol | None:
        lines = list(self.grid)
        lines += [[self.grid[r][c] for r in range(self.SIZE)] for c in range(self.SIZE)]
        lines.append([self.grid[i][i] for i in range(self.SIZE)])
        lines.append([self.grid[i][self.SIZE - 1 - i] for i in range(self.SIZE)])

        for line in lines:
            if line[0] != Symbol.EMPTY and all(cell == line[0] for cell in line):
                return line[0]
        return None

    def __str__(self) -> str:
        return "\n".join(" ".join(cell.value for cell in row) for row in self.grid)


class Game:
    def __init__(self, players: list[Player]):
        self.board = Board()
        self.players = players

    def play(self) -> None:
        turn = 0
        while True:
            player = self.players[turn % len(self.players)]
            row, col = player.next_move()
            self.board.place(row, col, player.symbol)

            print(f"{player.name} ({player.symbol.value}) -> ({row}, {col})")
            print(self.board)
            print()

            winner = self.board.winner()
            if winner is not None:
                print(f"{player.name} wins!")
                return
            if self.board.is_full():
                print("It's a draw!")
                return

            turn += 1


def main():
    # scripted so X takes the top row on its 3rd move - a clean, reproducible win
    player_x = HumanPlayer("Alice", Symbol.X, [(0, 0), (0, 1), (0, 2)])
    player_o = HumanPlayer("Bob", Symbol.O, [(1, 0), (1, 1)])

    game = Game([player_x, player_o])
    game.play()


if __name__ == "__main__":
    main()
