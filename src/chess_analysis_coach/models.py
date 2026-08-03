"""Structured values returned by chess analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Evaluation:
    """An engine score from the perspective of the side to move."""

    centipawns: int | None = None
    mate_in: int | None = None

    def __post_init__(self) -> None:
        if (self.centipawns is None) == (self.mate_in is None):
            raise ValueError("An evaluation must contain either centipawns or mate distance.")


@dataclass(frozen=True)
class CandidateMove:
    """One ranked legal move and its short principal variation."""

    san: str
    uci: str
    evaluation: Evaluation
    principal_variation_san: tuple[str, ...]


@dataclass(frozen=True)
class Recommendation:
    """Candidate moves calculated for one immutable input position."""

    position_fen: str
    side_to_move: str
    time_limit_seconds: float
    candidates: tuple[CandidateMove, ...]
