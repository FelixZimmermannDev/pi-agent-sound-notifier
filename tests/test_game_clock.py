import chess

from chess_analysis_coach.game_clock import ChessClock


class FakeTime:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_clock_counts_only_active_side_and_applies_increment() -> None:
    now = FakeTime()
    clock = ChessClock(initial_seconds=60, increment_seconds=2, now=now)

    clock.start(chess.WHITE)
    now.advance(12)

    running = clock.snapshot()
    assert running.white_seconds == 48
    assert running.black_seconds == 60
    assert running.active_color == chess.WHITE

    assert clock.finish_move(chess.WHITE, next_color=chess.BLACK)
    now.advance(5)
    switched = clock.snapshot()

    assert switched.white_seconds == 50
    assert switched.black_seconds == 55
    assert switched.active_color == chess.BLACK


def test_clock_stops_and_reports_the_side_that_runs_out_of_time() -> None:
    now = FakeTime()
    clock = ChessClock(initial_seconds=10, now=now)
    clock.start(chess.BLACK)

    now.advance(10)

    assert clock.expire_if_needed() == chess.BLACK
    assert clock.expire_if_needed() is None
    assert clock.snapshot().black_seconds == 0
    assert not clock.is_running
