import chess
import pytest

from chess_analysis_coach.errors import InvalidPositionError
from chess_analysis_coach.positions import parse_fen


def test_parse_fen_returns_the_requested_valid_position() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"

    board = parse_fen(fen)

    assert board.fen() == fen
    assert board.turn == chess.BLACK


@pytest.mark.parametrize(
    ("fen", "message"),
    [
        ("", "must not be empty"),
        ("not a FEN", "Invalid FEN"),
        ("8/8/8/8/8/8/8/8 w - - 0 1", "no white king"),
    ],
)
def test_parse_fen_rejects_unusable_input(fen: str, message: str) -> None:
    with pytest.raises(InvalidPositionError, match=message):
        parse_fen(fen)
