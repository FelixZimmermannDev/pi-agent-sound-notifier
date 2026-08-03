"""Revision-bound background analysis shared by local presentations."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from threading import Condition, Thread

import chess

from chess_analysis_coach.application import PositionAnalyzer, recommend_moves
from chess_analysis_coach.coaching import (
    CandidateForecast,
    build_candidate_forecast,
    explain_candidate,
    explain_candidate_plan,
)
from chess_analysis_coach.models import CandidateMove, Recommendation


@dataclass(frozen=True, slots=True)
class RevisionedPosition:
    """Immutable engine input identified by its position-source revision."""

    position_revision: int
    fen: str

    def __post_init__(self) -> None:
        if self.position_revision < 0:
            raise ValueError("Position revision cannot be negative.")

    def board(self) -> chess.Board:
        return chess.Board(self.fen)


@dataclass(frozen=True, slots=True)
class CoachedCandidate:
    """An existing engine candidate paired with existing coaching information."""

    candidate: CandidateMove
    explanation: str
    plan: str
    forecast: CandidateForecast


@dataclass(frozen=True, slots=True)
class RevisionedAnalysisResult:
    """Coached recommendation that is valid only for one position revision."""

    position_revision: int
    recommendation: Recommendation
    candidates: tuple[CoachedCandidate, ...]


@dataclass(frozen=True, slots=True)
class BackgroundAnalysisFailure:
    position_revision: int | None
    message: str


AnalyzerContextFactory = Callable[[], AbstractContextManager[PositionAnalyzer]]
ResultCallback = Callable[[RevisionedAnalysisResult], None]
FailureCallback = Callable[[BackgroundAnalysisFailure], None]
StartedCallback = Callable[[int], None]


def analyze_revisioned_position(
    position: RevisionedPosition,
    analyzer: PositionAnalyzer,
    *,
    time_limit_seconds: float,
    candidate_count: int,
    strength_elo: int | None = None,
) -> RevisionedAnalysisResult:
    """Use the established recommendation and coaching core for one revision."""

    board = position.board()
    recommendation = recommend_moves(
        board,
        analyzer,
        time_limit_seconds=time_limit_seconds,
        candidate_count=candidate_count,
        strength_elo=strength_elo,
    )
    coached_candidates = tuple(
        CoachedCandidate(
            candidate=candidate,
            explanation=explain_candidate(board, candidate),
            plan=explain_candidate_plan(board, candidate),
            forecast=build_candidate_forecast(board, candidate),
        )
        for candidate in recommendation.candidates
    )
    return RevisionedAnalysisResult(
        position_revision=position.position_revision,
        recommendation=recommendation,
        candidates=coached_candidates,
    )


class LatestPositionAnalysisCoordinator:
    """Run one bounded analysis at a time and publish only the newest revision."""

    def __init__(
        self,
        analyzer_context_factory: AnalyzerContextFactory,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
        on_result: ResultCallback,
        on_failure: FailureCallback,
        on_analysis_started: StartedCallback | None = None,
    ) -> None:
        if time_limit_seconds <= 0:
            raise ValueError("Analysis time must be greater than zero.")
        if candidate_count <= 0:
            raise ValueError("Candidate count must be greater than zero.")

        self._analyzer_context_factory = analyzer_context_factory
        self._time_limit_seconds = time_limit_seconds
        self._candidate_count = candidate_count
        self._strength_elo = strength_elo
        self._on_result = on_result
        self._on_failure = on_failure
        self._on_analysis_started = on_analysis_started
        self._condition = Condition()
        self._latest_position: RevisionedPosition | None = None
        self._pending_position: RevisionedPosition | None = None
        self._thread: Thread | None = None
        self._closed = False

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError("The analysis coordinator is already closed.")
            if self._thread is not None:
                return
            self._thread = Thread(
                target=self._run,
                name="latest-position-analysis",
                daemon=False,
            )
            self._thread.start()

    def submit(self, position: RevisionedPosition) -> bool:
        """Queue a newer position, replacing any not-yet-started stale request."""

        with self._condition:
            if self._closed:
                raise RuntimeError("The analysis coordinator is already closed.")
            if self._thread is None:
                raise RuntimeError("Start the analysis coordinator before submitting.")
            if not self._thread.is_alive():
                raise RuntimeError(
                    "The analysis worker is not running; check the Stockfish startup error."
                )
            latest = self._latest_position
            if latest is not None:
                if position.position_revision < latest.position_revision:
                    return False
                if position.position_revision == latest.position_revision:
                    if position.fen != latest.fen:
                        raise ValueError(
                            "One position revision cannot identify two different FEN values."
                        )
                    return False

            self._latest_position = position
            self._pending_position = position
            self._condition.notify_all()
            return True

    def close(self, *, timeout_seconds: float = 5.0) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._pending_position = None
            self._condition.notify_all()
            thread = self._thread

        if thread is not None:
            thread.join(timeout_seconds)
            if thread.is_alive():
                raise RuntimeError(
                    "Stockfish analysis did not stop within the shutdown timeout."
                )

    def _run(self) -> None:
        try:
            with self._analyzer_context_factory() as analyzer:
                self._run_with_analyzer(analyzer)
        except Exception as error:
            with self._condition:
                latest = self._latest_position
                closed = self._closed
            if not closed:
                self._on_failure(
                    BackgroundAnalysisFailure(
                        position_revision=(
                            latest.position_revision if latest is not None else None
                        ),
                        message=str(error),
                    )
                )

    def _run_with_analyzer(self, analyzer: PositionAnalyzer) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: self._closed or self._pending_position is not None
                )
                if self._closed:
                    return
                position = self._pending_position
                self._pending_position = None

            assert position is not None
            if self._on_analysis_started is not None:
                self._on_analysis_started(position.position_revision)
            try:
                result = analyze_revisioned_position(
                    position,
                    analyzer,
                    time_limit_seconds=self._time_limit_seconds,
                    candidate_count=self._candidate_count,
                    strength_elo=self._strength_elo,
                )
            except Exception as error:
                if self._is_current(position):
                    self._on_failure(
                        BackgroundAnalysisFailure(
                            position_revision=position.position_revision,
                            message=str(error),
                        )
                    )
                continue

            if self._is_current(position):
                self._on_result(result)

    def _is_current(self, position: RevisionedPosition) -> bool:
        with self._condition:
            return not self._closed and self._latest_position == position
