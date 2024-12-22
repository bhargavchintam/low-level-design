"""Chess - board, game loop and a scripted demo.

Scope cut (deliberate): no castling, no en passant, no check/checkmate/stalemate
detection, no promotion choice (auto-queens). Each piece only validates its own
move shape plus blocking/capture; a full legality checker is out of scope for
this exercise. See README for the reasoning.
"""

from __future__ import annotations

from pieces import Bishop, Color, King, Knight, Pawn, Piece, Position, Queen, Rook, in_bounds


class Board:
    def __init__(self):
        self._grid: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]

    def get_piece(self, pos: Position) -> Piece | None:
        row, col = pos
        return self._grid[row][col]

    def set_piece(self, pos: Position, piece: Piece | None) -> None:
        row, col = pos
        self._grid[row][col] = piece

    def move_piece(self, src: Position, dst: Position) -> Piece | None:
        piece = self.get_piece(src)
        captured = self.get_piece(dst)
        self.set_piece(dst, piece)
        self.set_piece(src, None)
        if piece is not None:
            piece.has_moved = True
        return captured

    def __str__(self) -> str:
        lines = []
        for row in range(7, -1, -1):
            cells = []
            for col in range(8):
                piece = self._grid[row][col]
                cells.append(piece.display() if piece else ".")
            lines.append(f"{row + 1} " + " ".join(cells))
        lines.append("  " + " ".join("abcdefgh"))
        return "\n".join(lines)


class BoardFactory:
    """Sets up the standard starting position."""

    _BACK_RANK = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]

    @classmethod
    def standard_board(cls) -> Board:
        board = Board()
        for col, piece_cls in enumerate(cls._BACK_RANK):
            board.set_piece((0, col), piece_cls(Color.WHITE))
            board.set_piece((7, col), piece_cls(Color.BLACK))
        for col in range(8):
            board.set_piece((1, col), Pawn(Color.WHITE))
            board.set_piece((6, col), Pawn(Color.BLACK))
        return board


def square_to_pos(square: str) -> Position:
    file_char, rank_char = square[0], square[1]
    col = ord(file_char) - ord("a")
    row = int(rank_char) - 1
    pos = (row, col)
    if not in_bounds(pos):
        raise ValueError(f"square out of bounds: {square}")
    return pos


def pos_to_square(pos: Position) -> str:
    row, col = pos
    return f"{chr(ord('a') + col)}{row + 1}"


class IllegalMoveError(Exception):
    pass


class Game:
    def __init__(self, board: Board | None = None):
        self.board = board or BoardFactory.standard_board()
        self.turn = Color.WHITE
        self.move_count = 0

    def move(self, src_square: str, dst_square: str) -> None:
        src, dst = square_to_pos(src_square), square_to_pos(dst_square)
        piece = self.board.get_piece(src)

        if piece is None:
            raise IllegalMoveError(f"no piece on {src_square}")
        if piece.color != self.turn:
            raise IllegalMoveError(f"it is {self.turn.value}'s turn, not {piece.color.value}'s")

        legal_targets = piece.valid_moves(src, self.board)
        if dst not in legal_targets:
            raise IllegalMoveError(f"{type(piece).__name__} cannot move {src_square} -> {dst_square}")

        captured = self.board.move_piece(src, dst)
        self.move_count += 1
        note = f" (captures {type(captured).__name__})" if captured else ""
        print(f"{self.move_count}. {self.turn.value} {type(piece).__name__} {src_square}-{dst_square}{note}")
        self.turn = self.turn.opposite()


def main() -> None:
    game = Game()
    print("Starting position:")
    print(game.board)

    moves = [
        ("e2", "e4"),
        ("e7", "e5"),
        ("g1", "f3"),
        ("b8", "c6"),
        ("f1", "c4"),
    ]
    for src, dst in moves:
        game.move(src, dst)
        print(game.board)
        print()

    print("Attempting an illegal move: black knight g8 to e4 (not an L-shape)...")
    try:
        game.move("g8", "e4")
    except IllegalMoveError as exc:
        print(f"rejected as expected: {exc}")


if __name__ == "__main__":
    main()
