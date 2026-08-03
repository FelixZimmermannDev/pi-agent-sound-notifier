import chess
import pytest

from chess_analysis_coach.evaluation import EvaluationSummary
from chess_analysis_coach.move_quality import assess_move


def summary(white_percent: float) -> EvaluationSummary:
    return EvaluationSummary(
        white_percent=white_percent,
        black_percent=100 - white_percent,
        display="0.00",
        favored_color="equal",
    )


def test_playing_the_recommended_move_is_always_classified_as_best() -> None:
    quality = assess_move(
        before=summary(60),
        after=summary(55),
        moving_color=chess.WHITE,
        played_move_uci="e2e4",
        best_move_san="e4",
        best_move_uci="e2e4",
    )

    assert quality.category == "best"
    assert quality.label == "Bester Zug"
    assert quality.accuracy_percent == 100
    assert quality.loss_percentage_points == 0


@pytest.mark.parametrize(
    ("loss", "category", "label"),
    [
        (0.5, "excellent", "Sehr gut"),
        (2, "good", "Gut"),
        (5, "inaccuracy", "Ungenauigkeit"),
        (10, "mistake", "Fehler"),
        (20, "blunder", "Patzer"),
    ],
)
def test_quality_thresholds_use_expected_score_loss(
    loss: float,
    category: str,
    label: str,
) -> None:
    quality = assess_move(
        before=summary(70),
        after=summary(70 - loss),
        moving_color=chess.WHITE,
        played_move_uci="a2a3",
        best_move_san="e4",
        best_move_uci="e2e4",
    )

    assert quality.category == category
    assert quality.label == label
    assert quality.loss_percentage_points == pytest.approx(loss)
    assert quality.accuracy_percent == pytest.approx(max(0, 100 - 2.5 * loss))


def test_black_quality_uses_blacks_expected_score() -> None:
    quality = assess_move(
        before=summary(40),
        after=summary(50),
        moving_color=chess.BLACK,
        played_move_uci="a7a6",
        best_move_san="e5",
        best_move_uci="e7e5",
    )

    assert quality.loss_percentage_points == pytest.approx(10)
    assert quality.category == "mistake"
