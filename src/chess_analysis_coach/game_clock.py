"""Server-side chess clock for local games."""

from collections.abc import Callable
from dataclasses import dataclass
import time

import chess


@dataclass(frozen=True)
class ClockSnapshot:
    """Remaining time for both players at one instant."""

    white_seconds: float
    black_seconds: float
    active_color: chess.Color | None


class ChessClock:
    """Own two countdown clocks and apply an increment after completed moves."""

    def __init__(
        self,
        *,
        initial_seconds: float,
        increment_seconds: float = 0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if initial_seconds <= 0:
            raise ValueError("Initial clock time must be greater than zero.")
        if increment_seconds < 0:
            raise ValueError("Clock increment cannot be negative.")

        self._remaining = {
            chess.WHITE: float(initial_seconds),
            chess.BLACK: float(initial_seconds),
        }
        self._increment_seconds = float(increment_seconds)
        self._now = now
        self._active_color: chess.Color | None = None
        self._active_since: float | None = None

    @property
    def is_running(self) -> bool:
        return self._active_color is not None

    def start(self, color: chess.Color) -> None:
        if self.is_running:
            raise ValueError("The chess clock is already running.")
        self._active_color = color
        self._active_since = self._now()

    def finish_move(
        self,
        moved_color: chess.Color,
        *,
        next_color: chess.Color | None,
    ) -> bool:
        """Stop one side's turn, add increment, and optionally start the next side."""
        if self._active_color != moved_color or self._active_since is None:
            raise ValueError("The moving side does not own the active clock.")

        current_time = self._now()
        elapsed = current_time - self._active_since
        self._remaining[moved_color] = max(
            0.0, self._remaining[moved_color] - elapsed
        )
        if self._remaining[moved_color] <= 0:
            self._active_color = None
            self._active_since = None
            return False

        self._remaining[moved_color] += self._increment_seconds
        self._active_color = next_color
        self._active_since = current_time if next_color is not None else None
        return True

    def expire_if_needed(self) -> chess.Color | None:
        """Stop and return the active side when its remaining time reached zero."""
        if self._active_color is None or self._active_since is None:
            return None

        color = self._active_color
        current_time = self._now()
        elapsed = current_time - self._active_since
        if elapsed < self._remaining[color]:
            return None

        self._remaining[color] = 0.0
        self._active_color = None
        self._active_since = None
        return color

    def stop(self) -> None:
        """Settle elapsed time and stop both clocks without declaring a timeout."""
        if self._active_color is None or self._active_since is None:
            return

        color = self._active_color
        elapsed = self._now() - self._active_since
        self._remaining[color] = max(0.0, self._remaining[color] - elapsed)
        self._active_color = None
        self._active_since = None

    def snapshot(self) -> ClockSnapshot:
        remaining = self._remaining.copy()
        if self._active_color is not None and self._active_since is not None:
            elapsed = self._now() - self._active_since
            remaining[self._active_color] = max(
                0.0, remaining[self._active_color] - elapsed
            )

        return ClockSnapshot(
            white_seconds=remaining[chess.WHITE],
            black_seconds=remaining[chess.BLACK],
            active_color=self._active_color,
        )
