"""Position parsing at the application boundary."""

import chess

from chess_analysis_coach.errors import InvalidPositionError


def parse_fen(fen: str) -> chess.Board:
    """Parse a FEN string and reject positions that violate chess validity rules."""
    normalized_fen = fen.strip()
    if not normalized_fen:
        raise InvalidPositionError("FEN must not be empty.")

    try:
        board = chess.Board(normalized_fen)
    except ValueError as error:
        raise InvalidPositionError(f"Invalid FEN: {error}") from error

    if not board.is_valid():
        status_name = board.status().name or "UNKNOWN"
        readable_status = status_name.lower().replace("_", " ").replace("|", ", ")
        raise InvalidPositionError(
            f"Invalid chess position ({readable_status}). Check the FEN and try again."
        )

    return board
