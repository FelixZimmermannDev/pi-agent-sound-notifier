from __future__ import annotations

from threading import Event, Lock

import chess

from chess_analysis_coach.background_analysis import (
    BackgroundAnalysisFailure,
    LatestPositionAnalysisCoordinator,
    RevisionedAnalysisResult,
    RevisionedPosition,
)
from chess_analysis_coach.models import CandidateMove, Evaluation


class BlockingAnalyzer:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.first_started = Event()
        self.release_first = Event()
        self._lock = Lock()

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        assert time_limit_seconds == 0.05
        assert candidate_count == 1
        assert strength_elo is None
        with self._lock:
            call_number = len(self.calls)
            self.calls.append(board.fen())
        if call_number == 0:
            self.first_started.set()
            assert self.release_first.wait(2)

        move = next(iter(board.legal_moves))
        san = board.san(move)
        return (
            CandidateMove(
                san=san,
                uci=move.uci(),
                evaluation=Evaluation(centipawns=20),
                principal_variation_san=(san,),
                principal_variation_uci=(move.uci(),),
            ),
        )


class RecordingAnalyzerContext:
    def __init__(self, analyzer) -> None:
        self.analyzer = analyzer
        self.exited = False

    def __enter__(self):
        return self.analyzer

    def __exit__(self, exception_type, exception, traceback) -> bool:
        self.exited = True
        return False


def test_latest_coordinator_discards_stale_result_and_analyzes_newest_position() -> None:
    analyzer = BlockingAnalyzer()
    context = RecordingAnalyzerContext(analyzer)
    results: list[RevisionedAnalysisResult] = []
    failures: list[BackgroundAnalysisFailure] = []
    result_ready = Event()
    coordinator = LatestPositionAnalysisCoordinator(
        lambda: context,
        time_limit_seconds=0.05,
        candidate_count=1,
        on_result=lambda result: (results.append(result), result_ready.set()),
        on_failure=failures.append,
    )
    board_after_e4 = chess.Board()
    board_after_e4.push_uci("e2e4")

    coordinator.start()
    assert coordinator.submit(RevisionedPosition(0, chess.STARTING_FEN)) is True
    assert analyzer.first_started.wait(2)
    assert coordinator.submit(RevisionedPosition(1, board_after_e4.fen())) is True
    analyzer.release_first.set()
    assert result_ready.wait(2)
    coordinator.close()

    assert failures == []
    assert [result.position_revision for result in results] == [1]
    assert len(analyzer.calls) == 2
    assert context.exited is True
    assert coordinator.is_running is False


def test_latest_coordinator_does_not_repeat_same_revision() -> None:
    analyzer = BlockingAnalyzer()
    analyzer.release_first.set()
    context = RecordingAnalyzerContext(analyzer)
    result_ready = Event()
    results: list[RevisionedAnalysisResult] = []
    coordinator = LatestPositionAnalysisCoordinator(
        lambda: context,
        time_limit_seconds=0.05,
        candidate_count=1,
        on_result=lambda result: (results.append(result), result_ready.set()),
        on_failure=lambda failure: None,
    )
    position = RevisionedPosition(4, chess.STARTING_FEN)

    coordinator.start()
    assert coordinator.submit(position) is True
    assert result_ready.wait(2)
    assert coordinator.submit(position) is False
    coordinator.close()

    assert len(analyzer.calls) == 1
    assert len(results) == 1
    assert context.exited is True


def test_latest_coordinator_reports_failure_and_cleans_up_context() -> None:
    class FailingAnalyzer:
        def analyze(self, board, **kwargs):
            raise RuntimeError("controlled analysis failure")

    context = RecordingAnalyzerContext(FailingAnalyzer())
    failures: list[BackgroundAnalysisFailure] = []
    failure_ready = Event()
    coordinator = LatestPositionAnalysisCoordinator(
        lambda: context,
        time_limit_seconds=0.05,
        candidate_count=1,
        on_result=lambda result: None,
        on_failure=lambda failure: (failures.append(failure), failure_ready.set()),
    )

    coordinator.start()
    coordinator.submit(RevisionedPosition(7, chess.STARTING_FEN))
    assert failure_ready.wait(2)
    coordinator.close()

    assert failures == [
        BackgroundAnalysisFailure(7, "controlled analysis failure")
    ]
    assert context.exited is True
