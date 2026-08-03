"""Fixed-perspective values for live evaluation presentation."""

from dataclasses import dataclass
import math

import chess

from chess_analysis_coach.models import Evaluation

_CENTIPAWN_BAR_SCALE = 250
_MIN_NON_MATE_PERCENT = 2.0
_MAX_NON_MATE_PERCENT = 98.0


@dataclass(frozen=True)
class EvaluationSummary:
    """One engine score normalized to White's fixed perspective."""

    white_percent: float
    black_percent: float
    display: str
    favored_color: str


def summarize_evaluation(
    evaluation: Evaluation,
    *,
    side_to_move: chess.Color,
) -> EvaluationSummary:
    """Map an engine value to a stable White/Black evaluation bar."""
    perspective_sign = 1 if side_to_move == chess.WHITE else -1

    if evaluation.mate_in is not None:
        white_mate = evaluation.mate_in * perspective_sign
        white_percent = 100.0 if white_mate >= 0 else 0.0
        display = (
            f"#{abs(white_mate)}" if white_mate >= 0 else f"-#{abs(white_mate)}"
        )
        return EvaluationSummary(
            white_percent=white_percent,
            black_percent=100.0 - white_percent,
            display=display,
            favored_color="white" if white_mate >= 0 else "black",
        )

    assert evaluation.centipawns is not None
    white_centipawns = evaluation.centipawns * perspective_sign
    white_percent = 50.0 + (100.0 / math.pi) * math.atan(
        white_centipawns / _CENTIPAWN_BAR_SCALE
    )
    white_percent = min(
        _MAX_NON_MATE_PERCENT,
        max(_MIN_NON_MATE_PERCENT, white_percent),
    )
    if abs(white_centipawns) < 15:
        favored_color = "equal"
    else:
        favored_color = "white" if white_centipawns > 0 else "black"
    return EvaluationSummary(
        white_percent=white_percent,
        black_percent=100.0 - white_percent,
        display=f"{white_centipawns / 100:+.2f}",
        favored_color=favored_color,
    )


def terminal_evaluation(winner: chess.Color | None) -> EvaluationSummary:
    if winner is None:
        return EvaluationSummary(
            white_percent=50.0,
            black_percent=50.0,
            display="0.00",
            favored_color="equal",
        )
    white_percent = 100.0 if winner == chess.WHITE else 0.0
    return EvaluationSummary(
        white_percent=white_percent,
        black_percent=100.0 - white_percent,
        display="1-0" if winner == chess.WHITE else "0-1",
        favored_color="white" if winner == chess.WHITE else "black",
    )
