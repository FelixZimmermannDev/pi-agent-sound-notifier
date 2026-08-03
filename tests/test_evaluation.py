import chess
import pytest

from chess_analysis_coach.evaluation import summarize_evaluation, terminal_evaluation
from chess_analysis_coach.models import Evaluation


def test_centipawn_evaluation_uses_a_fixed_white_perspective() -> None:
    white_to_move = summarize_evaluation(
        Evaluation(centipawns=100),
        side_to_move=chess.WHITE,
    )
    black_to_move = summarize_evaluation(
        Evaluation(centipawns=100),
        side_to_move=chess.BLACK,
    )

    assert white_to_move.display == "+1.00"
    assert white_to_move.white_percent == pytest.approx(59.104, abs=0.01)
    assert white_to_move.favored_color == "white"
    assert black_to_move.display == "-1.00"
    assert black_to_move.white_percent == pytest.approx(
        100 - white_to_move.white_percent
    )
    assert black_to_move.favored_color == "black"


def test_small_centipawn_changes_use_a_conservative_win_chance_curve() -> None:
    summary = summarize_evaluation(
        Evaluation(centipawns=20),
        side_to_move=chess.WHITE,
    )

    assert summary.white_percent == pytest.approx(51.84, abs=0.01)
    assert summary.black_percent == pytest.approx(48.16, abs=0.01)


def test_mate_evaluation_pins_bar_to_the_winning_side() -> None:
    summary = summarize_evaluation(
        Evaluation(mate_in=3),
        side_to_move=chess.BLACK,
    )

    assert summary.display == "-#3"
    assert summary.white_percent == 0
    assert summary.black_percent == 100
    assert summary.favored_color == "black"


def test_terminal_draw_is_shown_as_equal() -> None:
    summary = terminal_evaluation(None)

    assert summary.white_percent == 50
    assert summary.black_percent == 50
    assert summary.display == "0.00"
    assert summary.favored_color == "equal"
