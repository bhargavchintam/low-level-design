# Chess

## Problem
Model a chess board and the mechanics of making moves: an 8x8 board, the six piece types each with their own movement rules, turn order between two players, and rejecting moves that don't match a piece's shape or are played out of turn.

## Scope cut
Deliberately out of scope: castling, en passant, promotion choice (would auto-queen if implemented), check/checkmate/stalemate detection, and draw rules. `valid_moves` returns *pseudo-legal* moves - correct shape plus blocking/capture - not moves filtered by whether they leave your own king in check. This keeps the focus on the piece-polymorphism and board mechanics rather than full chess legality.

## Design
- `Color` enum (`pieces.py`) - WHITE, BLACK, with `opposite()`.
- `Piece` (ABC, `pieces.py`) - holds `color`/`has_moved`; abstract `valid_moves(pos, board)`. `Pawn`, `Rook`, `Knight`, `Bishop`, `Queen`, `King` each implement their own move shape. Sliding pieces (Rook/Bishop/Queen) share a `_slide` helper that walks a direction until it hits the edge, a friendly piece, or an enemy piece to capture.
- `Board` (`main.py`) - an 8x8 grid of `Piece | None`, with `get_piece`/`set_piece`/`move_piece` and a text `__str__` renderer.
- `BoardFactory` - `standard_board()` lays out the initial position.
- `Game` - tracks `turn` (a `Color`), takes moves as algebraic squares (`"e2"`, `"e4"`), resolves them to board positions, validates the piece exists, belongs to the player to move, and that the destination is in that piece's `valid_moves` before executing and flipping the turn. Raises `IllegalMoveError` otherwise.

## Patterns used
- **Strategy via polymorphism** - each `Piece` subclass supplies its own move-shape logic behind the same `valid_moves` contract, so `Game` never branches on piece type.
- **Factory Method** - `BoardFactory.standard_board()` builds the initial 32-piece layout in one place, separate from board mechanics.

## How to run
```
python3 main.py
```
