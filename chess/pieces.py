"""Piece hierarchy. Each piece knows its own move shape - polymorphism stands in
for a per-type strategy without needing a separate Strategy class per piece."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class Color(Enum):
    WHITE = "white"
    BLACK = "black"

    def opposite(self) -> "Color":
        return Color.BLACK if self is Color.WHITE else Color.WHITE


Position = tuple[int, int]  # (row, col), row 0 = rank 1, col 0 = file a


def in_bounds(pos: Position) -> bool:
    row, col = pos
    return 0 <= row < 8 and 0 <= col < 8


class Piece(ABC):
    symbol: str = "?"

    def __init__(self, color: Color):
        self.color = color
        self.has_moved = False

    @abstractmethod
    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        """Pseudo-legal moves: respects blocking/capture rules but not check."""
        raise NotImplementedError

    def display(self) -> str:
        return self.symbol.upper() if self.color is Color.WHITE else self.symbol.lower()

    def _slide(self, pos: Position, board: "Board", directions: list[Position]) -> list[Position]:
        moves: list[Position] = []
        for d_row, d_col in directions:
            row, col = pos
            while True:
                row, col = row + d_row, col + d_col
                if not in_bounds((row, col)):
                    break
                occupant = board.get_piece((row, col))
                if occupant is None:
                    moves.append((row, col))
                    continue
                if occupant.color != self.color:
                    moves.append((row, col))
                break
        return moves


class Pawn(Piece):
    symbol = "p"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        row, col = pos
        direction = 1 if self.color is Color.WHITE else -1
        start_row = 1 if self.color is Color.WHITE else 6
        moves: list[Position] = []

        one_step = (row + direction, col)
        if in_bounds(one_step) and board.get_piece(one_step) is None:
            moves.append(one_step)
            two_step = (row + 2 * direction, col)
            if row == start_row and board.get_piece(two_step) is None:
                moves.append(two_step)

        for d_col in (-1, 1):
            capture = (row + direction, col + d_col)
            if in_bounds(capture):
                occupant = board.get_piece(capture)
                if occupant is not None and occupant.color != self.color:
                    moves.append(capture)
        return moves


class Rook(Piece):
    symbol = "r"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        return self._slide(pos, board, [(1, 0), (-1, 0), (0, 1), (0, -1)])


class Bishop(Piece):
    symbol = "b"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        return self._slide(pos, board, [(1, 1), (1, -1), (-1, 1), (-1, -1)])


class Queen(Piece):
    symbol = "q"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        return self._slide(pos, board, [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ])


class Knight(Piece):
    symbol = "n"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        row, col = pos
        offsets = [
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2),
        ]
        moves = []
        for d_row, d_col in offsets:
            target = (row + d_row, col + d_col)
            if not in_bounds(target):
                continue
            occupant = board.get_piece(target)
            if occupant is None or occupant.color != self.color:
                moves.append(target)
        return moves


class King(Piece):
    symbol = "k"

    def valid_moves(self, pos: Position, board: "Board") -> list[Position]:
        row, col = pos
        moves = []
        for d_row in (-1, 0, 1):
            for d_col in (-1, 0, 1):
                if d_row == 0 and d_col == 0:
                    continue
                target = (row + d_row, col + d_col)
                if not in_bounds(target):
                    continue
                occupant = board.get_piece(target)
                if occupant is None or occupant.color != self.color:
                    moves.append(target)
        return moves
