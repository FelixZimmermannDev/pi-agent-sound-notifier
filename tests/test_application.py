import chess
import pytest

from chess_analysis_coach.application import recommend_moves
from chess_analysis_coach.errors import EngineAnalysisError, PositionNotAnalyzableError
from chess_analysis_coach.models import CandidateMove, Evaluation


class RecordingAnalyzer:
    def __init__(self, candidates: tuple[CandidateMove, ...]) -> None:
        self.candidates = candidates
        self.received_fen: str | None = None
        self.received_time: float | None = None
        self.received_count: int | None = None
        self.received_strength: int | None = None

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        self.received_fen = board.fen()
        self.received_time = time_limit_seconds
        self.received_count = candidate_count
        self.received_strength = strength_elo
        board.push(next(iter(board.legal_moves)))
        return self.candidates


def test_recommend_moves_coordinates_bounded_analysis_without_mutating_input() -> None:
    board = chess.Board()
    original_fen = board.fen()
    candidates = (
        CandidateMove(
            san="e4",
            uci="e2e4",
            evaluation=Evaluation(centipawns=31),
            principal_variation_san=("e4", "e5"),
        ),
    )
    analyzer = RecordingAnalyzer(candidates)

    result = recommend_moves(
        board,
        analyzer,
        time_limit_seconds=0.25,
        candidate_count=3,
        strength_elo=1800,
    )

    assert result.position_fen == original_fen
    assert result.side_to_move == "White"
    assert result.candidates == candidates
    assert analyzer.received_fen == original_fen
    assert analyzer.received_time == 0.25
    assert analyzer.received_count == 3
    assert analyzer.received_strength == 1800
    assert board.fen() == original_fen


def test_recommend_moves_rejects_a_position_without_legal_moves_before_analysis() -> None:
    checkmated_board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    analyzer = RecordingAnalyzer(())

    with pytest.raises(PositionNotAnalyzableError, match="no legal moves"):
        recommend_moves(
            checkmated_board,
            analyzer,
            time_limit_seconds=0.25,
            candidate_count=3,
        )

    assert analyzer.received_fen is None


def test_recommend_moves_rejects_empty_engine_output() -> None:
    with pytest.raises(EngineAnalysisError, match="no candidate moves"):
        recommend_moves(
            chess.Board(),
            RecordingAnalyzer(()),
            time_limit_seconds=0.25,
            candidate_count=3,
        )
