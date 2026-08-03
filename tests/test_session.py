import chess
import pytest

from chess_analysis_coach.errors import InvalidMoveError, SessionStateError
from chess_analysis_coach.session import LocalGameSession


def test_session_applies_player_and_bot_moves_without_mutating_caller_board() -> None:
    caller_board = chess.Board()
    session = LocalGameSession(caller_board, player_color=chess.WHITE)

    player_move = session.apply_player_move("e4")
    bot_move = session.apply_bot_move(chess.Move.from_uci("e7e5"))

    assert player_move.san == "e4"
    assert player_move.uci == "e2e4"
    assert player_move.revision == 1
    assert bot_move.san == "e5"
    assert bot_move.revision == 2
    assert session.is_player_turn
    assert session.snapshot().piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert caller_board == chess.Board()


def test_session_rejects_illegal_input_without_changing_state() -> None:
    session = LocalGameSession(chess.Board(), player_color=chess.WHITE)
    original_fen = session.snapshot().fen()

    with pytest.raises(InvalidMoveError, match="not legal"):
        session.apply_player_move("e2e5")

    assert session.snapshot().fen() == original_fen
    assert session.revision == 0


def test_session_rejects_a_bot_move_during_the_player_turn() -> None:
    session = LocalGameSession(chess.Board(), player_color=chess.WHITE)

    with pytest.raises(SessionStateError, match="your turn"):
        session.apply_bot_move(chess.Move.from_uci("e2e4"))

    assert session.revision == 0


def test_session_undo_returns_to_the_previous_player_turn() -> None:
    session = LocalGameSession(chess.Board(), player_color=chess.WHITE)
    session.apply_player_move("e4")
    session.apply_bot_move(chess.Move.from_uci("e7e5"))

    undone_moves = session.undo_last_turn()

    assert undone_moves == 2
    assert session.snapshot() == chess.Board()
    assert session.is_player_turn
    assert session.revision == 3
