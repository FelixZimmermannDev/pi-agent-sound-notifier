"""Transparent provisional move-quality scoring for bounded live analysis."""

from dataclasses import dataclass

import chess

from chess_analysis_coach.evaluation import EvaluationSummary


@dataclass(frozen=True)
class MoveQuality:
    """Quality based on normalized evaluation-share loss, not a proprietary metric."""

    category: str
    label: str
    accuracy_percent: float
    loss_percentage_points: float
    best_move_san: str
    best_move_uci: str


def assess_move(
    *,
    before: EvaluationSummary,
    after: EvaluationSummary,
    moving_color: chess.Color,
    played_move_uci: str,
    best_move_san: str,
    best_move_uci: str,
) -> MoveQuality:
    """Compare normalized evaluation share before and after a played move."""
    before_percent = _share_percent(before, moving_color)
    after_percent = _share_percent(after, moving_color)
    loss = max(0.0, before_percent - after_percent)

    if played_move_uci == best_move_uci:
        category = "best"
        label = "Bester Zug"
        loss = 0.0
    elif loss <= 1:
        category = "excellent"
        label = "Sehr gut"
    elif loss <= 3:
        category = "good"
        label = "Gut"
    elif loss <= 7:
        category = "inaccuracy"
        label = "Ungenauigkeit"
    elif loss <= 15:
        category = "mistake"
        label = "Fehler"
    else:
        category = "blunder"
        label = "Patzer"

    accuracy = max(0.0, 100.0 - 2.5 * loss)
    return MoveQuality(
        category=category,
        label=label,
        accuracy_percent=accuracy,
        loss_percentage_points=loss,
        best_move_san=best_move_san,
        best_move_uci=best_move_uci,
    )


def _share_percent(summary: EvaluationSummary, color: chess.Color) -> float:
    return summary.white_percent if color == chess.WHITE else summary.black_percent
