"""Application coordination for bounded move recommendations."""

from typing import Protocol

import chess

from chess_analysis_coach.errors import EngineAnalysisError, PositionNotAnalyzableError
from chess_analysis_coach.models import CandidateMove, Recommendation


class PositionAnalyzer(Protocol):
    """Boundary implemented by an engine that analyzes one position."""

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]: ...


def validate_analysis_request(
    board: chess.Board,
    *,
    time_limit_seconds: float,
    candidate_count: int,
) -> None:
    if time_limit_seconds <= 0:
        raise ValueError("Analysis time must be greater than zero.")
    if candidate_count <= 0:
        raise ValueError("Candidate count must be greater than zero.")
    if board.legal_moves.count() == 0:
        raise PositionNotAnalyzableError(
            "The position has no legal moves; the game is already checkmate or stalemate."
        )


def recommend_moves(
    board: chess.Board,
    analyzer: PositionAnalyzer,
    *,
    time_limit_seconds: float,
    candidate_count: int,
    strength_elo: int | None = None,
) -> Recommendation:
    """Analyze a defensive copy of a board under an explicit time limit."""
    validate_analysis_request(
        board,
        time_limit_seconds=time_limit_seconds,
        candidate_count=candidate_count,
    )

    position_fen = board.fen()
    side_to_move = "White" if board.turn == chess.WHITE else "Black"
    analysis_board = board.copy(stack=True)
    candidates = analyzer.analyze(
        analysis_board,
        time_limit_seconds=time_limit_seconds,
        candidate_count=candidate_count,
        strength_elo=strength_elo,
    )

    if not candidates:
        raise EngineAnalysisError("Stockfish returned no candidate moves for this position.")

    return Recommendation(
        position_fen=position_fen,
        side_to_move=side_to_move,
        time_limit_seconds=time_limit_seconds,
        candidates=candidates,
    )
