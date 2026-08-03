import chess

from chess_analysis_coach.background_analysis import (
    RevisionedPosition,
    analyze_revisioned_position,
)
from chess_analysis_coach.models import CandidateMove, Evaluation
from chess_overlay.chess_state import BoardGeometry, BoardOrientation, PositionSnapshot
from chess_overlay.overlay_models import build_overlay_analysis_result


class FakeCoreAnalyzer:
    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        assert time_limit_seconds == 0.05
        move = chess.Move.from_uci("e2e4")
        return (
            CandidateMove(
                san=board.san(move),
                uci=move.uci(),
                evaluation=Evaluation(centipawns=31),
                principal_variation_san=("e4", "e5"),
                principal_variation_uci=("e2e4", "e7e5"),
            ),
        )


def test_reconciled_snapshot_reaches_existing_recommendation_and_coaching_core() -> None:
    position = RevisionedPosition(4, chess.STARTING_FEN)

    core_result = analyze_revisioned_position(
        position,
        FakeCoreAnalyzer(),
        time_limit_seconds=0.05,
        candidate_count=1,
    )
    overlay_result = build_overlay_analysis_result(
        PositionSnapshot(
            board_fen=chess.STARTING_FEN,
            position_revision=4,
            last_move_uci=None,
            board_bounds=BoardGeometry(0, 0, 800, 800),
            orientation=BoardOrientation.WHITE,
        ),
        core_result,
    )

    assert overlay_result.position_revision == 4
    assert overlay_result.candidate_moves[0].uci == "e2e4"
    assert overlay_result.candidate_moves[0].evaluation == "+0.31"
    assert "Stockfish" in overlay_result.candidate_moves[0].explanation
    assert overlay_result.candidate_moves[0].plan.startswith("Ziel:")
