"""Desktop-presentation values derived from revision-bound core analysis."""

from dataclasses import dataclass

from chess_analysis_coach.background_analysis import RevisionedAnalysisResult
from chess_analysis_coach.presentation import format_evaluation

from .chess_state import BoardGeometry, BoardOrientation, PositionSnapshot


@dataclass(frozen=True, slots=True)
class OverlayCandidate:
    rank: int
    san: str
    uci: str
    evaluation: str
    principal_variation_san: tuple[str, ...]
    explanation: str
    plan: str


@dataclass(frozen=True, slots=True)
class OverlayAnalysisResult:
    position_revision: int
    candidate_moves: tuple[OverlayCandidate, ...]
    board_bounds: BoardGeometry
    orientation: BoardOrientation


def build_overlay_analysis_result(
    snapshot: PositionSnapshot,
    analysis: RevisionedAnalysisResult,
) -> OverlayAnalysisResult:
    if snapshot.position_revision != analysis.position_revision:
        raise ValueError("Analysis revision does not match the position snapshot.")
    return OverlayAnalysisResult(
        position_revision=analysis.position_revision,
        candidate_moves=tuple(
            OverlayCandidate(
                rank=rank,
                san=coached.candidate.san,
                uci=coached.candidate.uci,
                evaluation=format_evaluation(coached.candidate.evaluation),
                principal_variation_san=coached.candidate.principal_variation_san,
                explanation=coached.explanation,
                plan=coached.plan,
            )
            for rank, coached in enumerate(analysis.candidates, start=1)
        ),
        board_bounds=snapshot.board_bounds,
        orientation=snapshot.orientation,
    )
