"""Typed observed-position values and legal visual-move reconciliation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import chess


class BoardOrientation(str, Enum):
    WHITE = "white"
    BLACK = "black"


@dataclass(frozen=True, slots=True)
class BoardGeometry:
    left: float
    top: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Board width and height must be positive.")


@dataclass(frozen=True, slots=True)
class BoardObservation:
    """Stable visual occupancy observation; no raw pixels cross this boundary."""

    observation_id: int
    piece_placement: tuple[bool, ...]
    changed_squares: frozenset[chess.Square]
    board_bounds: BoardGeometry
    orientation: BoardOrientation
    confidence: float
    timestamp: float

    def __post_init__(self) -> None:
        if self.observation_id < 0:
            raise ValueError("Observation ID cannot be negative.")
        if len(self.piece_placement) != 64:
            raise ValueError("Piece placement must contain all 64 squares.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Observation confidence must be between 0 and 1.")

    @property
    def occupied_squares(self) -> frozenset[chess.Square]:
        return frozenset(
            square for square, occupied in enumerate(self.piece_placement) if occupied
        )


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    """Defensive logical position snapshot owned by the visual reconciler."""

    board_fen: str
    position_revision: int
    last_move_uci: str | None
    board_bounds: BoardGeometry
    orientation: BoardOrientation

    def board(self) -> chess.Board:
        return chess.Board(self.board_fen)


class ReconcileStatus(str, Enum):
    SYNCHRONIZED = "synchronized"
    MOVE_ACCEPTED = "move_accepted"
    UNCERTAIN = "uncertain"
    NO_LEGAL_TRANSITION = "no_legal_transition"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    status: ReconcileStatus
    message: str
    snapshot: PositionSnapshot
    state_changed: bool


class LegalPositionReconciler:
    """Single owner of the board reconstructed from uniquely legal visual changes."""

    def __init__(
        self,
        *,
        orientation: BoardOrientation,
        starting_board: chess.Board | None = None,
        minimum_confidence: float = 0.75,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("Minimum confidence must be between 0 and 1.")
        source_board = starting_board or chess.Board()
        self._starting_board = source_board.copy(stack=True)
        self._board = source_board.copy(stack=True)
        self._orientation = orientation
        self._minimum_confidence = minimum_confidence
        self._revision = 0
        self._last_move_uci: str | None = None
        self._board_bounds = BoardGeometry(0, 0, 1, 1)

    @property
    def revision(self) -> int:
        return self._revision

    def snapshot(self) -> PositionSnapshot:
        return PositionSnapshot(
            board_fen=self._board.fen(),
            position_revision=self._revision,
            last_move_uci=self._last_move_uci,
            board_bounds=self._board_bounds,
            orientation=self._orientation,
        )

    def reset_to_starting_position(self) -> PositionSnapshot:
        """Invalidate old analysis while preserving monotonic revision history."""

        self._board = self._starting_board.copy(stack=True)
        self._revision += 1
        self._last_move_uci = None
        return self.snapshot()

    def reconcile(self, observation: BoardObservation) -> ReconcileResult:
        current_snapshot = self.snapshot()
        if observation.orientation != self._orientation:
            return ReconcileResult(
                ReconcileStatus.UNCERTAIN,
                "Die erkannte Brettorientierung passt nicht zur Konfiguration.",
                current_snapshot,
                False,
            )
        if observation.confidence < self._minimum_confidence:
            return ReconcileResult(
                ReconcileStatus.UNCERTAIN,
                f"Erkennung unsicher ({observation.confidence:.0%}); Stellung bleibt unverändert.",
                current_snapshot,
                False,
            )

        current_placement = _occupied_placement(self._board)
        if (
            observation.piece_placement == current_placement
            and not observation.changed_squares
        ):
            self._board_bounds = observation.board_bounds
            return ReconcileResult(
                ReconcileStatus.SYNCHRONIZED,
                "Grundstellung erkannt und synchronisiert."
                if self._revision == 0
                else "Stellung stabil und synchronisiert.",
                self.snapshot(),
                False,
            )

        matching_moves: list[chess.Move] = []
        for move in self._board.legal_moves:
            candidate_board = self._board.copy(stack=True)
            changed_squares = _squares_changed_by_move(self._board, move)
            candidate_board.push(move)
            if (
                _occupied_placement(candidate_board) == observation.piece_placement
                and changed_squares == observation.changed_squares
            ):
                matching_moves.append(move)

        if not matching_moves:
            return ReconcileResult(
                ReconcileStatus.NO_LEGAL_TRANSITION,
                "Keine eindeutige legale Zugänderung erkannt; letzte gültige Stellung bleibt erhalten.",
                current_snapshot,
                False,
            )
        if len(matching_moves) > 1:
            move_list = ", ".join(move.uci() for move in matching_moves[:4])
            return ReconcileResult(
                ReconcileStatus.AMBIGUOUS,
                f"Mehrere legale Übergänge passen ({move_list}); keine Empfehlung.",
                current_snapshot,
                False,
            )

        move = matching_moves[0]
        san = self._board.san(move)
        self._board.push(move)
        self._revision += 1
        self._last_move_uci = move.uci()
        self._board_bounds = observation.board_bounds
        return ReconcileResult(
            ReconcileStatus.MOVE_ACCEPTED,
            f"Zug erkannt: {san} ({move.uci()}).",
            self.snapshot(),
            True,
        )


def occupied_placement(board: chess.Board) -> tuple[bool, ...]:
    """Public helper for deterministic recognition tests and calibration."""

    return _occupied_placement(board)


def square_center(
    square: chess.Square,
    bounds: BoardGeometry,
    orientation: BoardOrientation,
) -> tuple[float, float]:
    file_index = chess.square_file(square)
    rank_index = chess.square_rank(square)
    if orientation == BoardOrientation.WHITE:
        column = file_index
        row = 7 - rank_index
    else:
        column = 7 - file_index
        row = rank_index
    return (
        bounds.left + (column + 0.5) * bounds.width / 8,
        bounds.top + (row + 0.5) * bounds.height / 8,
    )


@dataclass(frozen=True, slots=True)
class MoveArrow:
    start: tuple[float, float]
    end: tuple[float, float]


def move_arrow(
    uci: str,
    bounds: BoardGeometry,
    orientation: BoardOrientation,
) -> MoveArrow:
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as error:
        raise ValueError(f"Invalid UCI move for overlay arrow: {uci}") from error

    start = square_center(move.from_square, bounds, orientation)
    target = square_center(move.to_square, bounds, orientation)
    delta_x = target[0] - start[0]
    delta_y = target[1] - start[1]
    distance = math.hypot(delta_x, delta_y)
    if distance == 0:
        raise ValueError("Overlay arrow move must change squares.")
    shorten_by = min(min(bounds.width, bounds.height) / 8 * 0.28, distance * 0.2)
    end = (
        target[0] - delta_x / distance * shorten_by,
        target[1] - delta_y / distance * shorten_by,
    )
    return MoveArrow(start=start, end=end)


def _occupied_placement(board: chess.Board) -> tuple[bool, ...]:
    return tuple(board.piece_at(square) is not None for square in chess.SQUARES)


def _squares_changed_by_move(
    board: chess.Board,
    move: chess.Move,
) -> frozenset[chess.Square]:
    changed = {move.from_square, move.to_square}
    if board.is_en_passant(move):
        changed.add(chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square)))
    if board.is_castling(move):
        rank = chess.square_rank(move.from_square)
        if chess.square_file(move.to_square) == 6:
            changed.update({chess.square(7, rank), chess.square(5, rank)})
        else:
            changed.update({chess.square(0, rank), chess.square(3, rank)})
    return frozenset(changed)
