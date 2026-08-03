"""Frame-to-board observation recognition for a calibrated static 8x8 board."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock

import chess
import numpy as np
from numpy.typing import NDArray

from .capture import BasicFrameProcessor, CaptureError, FrameSummary
from .chess_state import (
    BoardGeometry,
    BoardObservation,
    BoardOrientation,
    occupied_placement,
)


class RecognitionStatus(str, Enum):
    CALIBRATING = "calibrating"
    STABILIZING = "stabilizing"
    SYNCHRONIZED = "synchronized"
    OBSERVATION_READY = "observation_ready"
    AWAITING_RECONCILIATION = "awaiting_reconciliation"
    BOARD_LOST = "board_lost"


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    status: RecognitionStatus
    message: str
    confidence: float
    observation: BoardObservation | None = None


@dataclass(frozen=True, slots=True)
class ChessFrameResult:
    frame_summary: FrameSummary
    recognition: RecognitionResult


@dataclass(slots=True)
class _VisualBoardSample:
    piece_placement: tuple[bool, ...]
    signatures: tuple[NDArray[np.float32], ...]
    confidence: float
    width: int
    height: int
    timestamp: float


class StableBoardRecognizer:
    """Calibrate on the starting position and emit only stable visual changes."""

    def __init__(
        self,
        *,
        orientation: BoardOrientation,
        stable_frame_count: int = 3,
        minimum_board_confidence: float = 0.68,
        occupancy_threshold: float = 0.045,
        signature_change_threshold: float = 0.035,
        stable_similarity_threshold: float = 0.012,
    ) -> None:
        if stable_frame_count <= 0:
            raise ValueError("Stable frame count must be positive.")
        self._lock = RLock()
        self._orientation = orientation
        self._stable_frame_count = stable_frame_count
        self._minimum_board_confidence = minimum_board_confidence
        self._occupancy_threshold = occupancy_threshold
        self._signature_change_threshold = signature_change_threshold
        self._stable_similarity_threshold = stable_similarity_threshold
        self._expected_start = occupied_placement(chess.Board())
        self._next_observation_id = 1
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._baseline: _VisualBoardSample | None = None
            self._candidate: _VisualBoardSample | None = None
            self._candidate_count = 0
            self._pending_samples: dict[int, _VisualBoardSample] = {}
            self._last_emitted_fingerprint: tuple[
                tuple[bool, ...], frozenset[int]
            ] | None = None

    def recognize(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> RecognitionResult:
        with self._lock:
            return self._recognize_locked(frame, captured_at=captured_at)

    def _recognize_locked(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> RecognitionResult:
        sample = self._sample_board(frame, captured_at=captured_at)
        if sample.confidence < self._minimum_board_confidence:
            self._candidate = None
            self._candidate_count = 0
            return RecognitionResult(
                RecognitionStatus.BOARD_LOST,
                f"Brett nicht sicher erkannt ({sample.confidence:.0%}).",
                sample.confidence,
            )

        if self._baseline is None:
            if sample.piece_placement != self._expected_start:
                self._candidate = None
                self._candidate_count = 0
                return RecognitionResult(
                    RecognitionStatus.CALIBRATING,
                    "Für die Kalibrierung wird die sichtbare Schachgrundstellung erwartet.",
                    sample.confidence,
                )
            if not self._is_stable_candidate(sample):
                return RecognitionResult(
                    RecognitionStatus.STABILIZING,
                    f"Grundstellung stabilisieren ({self._candidate_count}/{self._stable_frame_count}).",
                    sample.confidence,
                )
            self._baseline = sample
            observation = self._build_observation(sample, frozenset())
            self._pending_samples[observation.observation_id] = sample
            return RecognitionResult(
                RecognitionStatus.OBSERVATION_READY,
                "Grundstellung stabil erkannt.",
                sample.confidence,
                observation,
            )

        changed_squares = self._changed_squares(self._baseline, sample)
        if (
            not changed_squares
            and sample.piece_placement == self._baseline.piece_placement
        ):
            self._candidate = None
            self._candidate_count = 0
            self._last_emitted_fingerprint = None
            return RecognitionResult(
                RecognitionStatus.SYNCHRONIZED,
                "Brett stabil; keine neue Stellung.",
                sample.confidence,
            )

        if not self._is_stable_candidate(sample):
            return RecognitionResult(
                RecognitionStatus.STABILIZING,
                f"Änderung stabilisieren ({self._candidate_count}/{self._stable_frame_count}).",
                sample.confidence,
            )

        fingerprint = (sample.piece_placement, changed_squares)
        if fingerprint == self._last_emitted_fingerprint:
            return RecognitionResult(
                RecognitionStatus.AWAITING_RECONCILIATION,
                "Unveränderte Beobachtung wartet auf Resynchronisierung.",
                sample.confidence,
            )

        observation = self._build_observation(sample, changed_squares)
        self._pending_samples[observation.observation_id] = sample
        self._last_emitted_fingerprint = fingerprint
        return RecognitionResult(
            RecognitionStatus.OBSERVATION_READY,
            "Stabile Brettänderung erkannt.",
            sample.confidence,
            observation,
        )

    def accept(self, observation_id: int) -> None:
        """Advance the visual baseline only after a legal reconciler acceptance."""

        with self._lock:
            sample = self._pending_samples.get(observation_id)
            if sample is None:
                raise ValueError(f"Unknown board observation: {observation_id}")
            self._baseline = sample
            self._pending_samples.clear()
            self._candidate = None
            self._candidate_count = 0
            self._last_emitted_fingerprint = None

    def _build_observation(
        self,
        sample: _VisualBoardSample,
        changed_squares: frozenset[chess.Square],
    ) -> BoardObservation:
        observation = BoardObservation(
            observation_id=self._next_observation_id,
            piece_placement=sample.piece_placement,
            changed_squares=changed_squares,
            board_bounds=BoardGeometry(0, 0, sample.width, sample.height),
            orientation=self._orientation,
            confidence=sample.confidence,
            timestamp=sample.timestamp,
        )
        self._next_observation_id += 1
        return observation

    def _is_stable_candidate(self, sample: _VisualBoardSample) -> bool:
        if self._candidate is None or not _samples_are_similar(
            self._candidate,
            sample,
            threshold=self._stable_similarity_threshold,
        ):
            self._candidate = sample
            self._candidate_count = 1
            return self._candidate_count >= self._stable_frame_count

        self._candidate = sample
        self._candidate_count += 1
        return self._candidate_count >= self._stable_frame_count

    def _changed_squares(
        self,
        baseline: _VisualBoardSample,
        current: _VisualBoardSample,
    ) -> frozenset[chess.Square]:
        return frozenset(
            square
            for square in chess.SQUARES
            if float(
                np.mean(
                    np.abs(
                        baseline.signatures[square] - current.signatures[square]
                    )
                )
            )
            >= self._signature_change_threshold
        )

    def _sample_board(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> _VisualBoardSample:
        if frame.ndim != 3 or frame.shape[2] < 3:
            raise CaptureError("Recognition benötigt ein BGR-Bild mit drei Farbkanälen.")
        height, width = frame.shape[:2]
        if min(width, height) < 160:
            raise CaptureError("Das erkannte Brett muss mindestens 160×160 Pixel groß sein.")
        if abs(width - height) / max(width, height) > 0.04:
            raise CaptureError("Der F8-Rahmen muss ein quadratisches 8×8-Brett umschließen.")

        placement: list[bool] = [False] * 64
        signatures: list[NDArray[np.float32] | None] = [None] * 64
        background_colors: list[tuple[int, NDArray[np.float32]]] = []
        classification_confidences: list[float] = []

        for row in range(8):
            top = round(row * height / 8)
            bottom = round((row + 1) * height / 8)
            for column in range(8):
                left = round(column * width / 8)
                right = round((column + 1) * width / 8)
                patch = frame[top:bottom, left:right, :3].astype(np.float32, copy=False)
                occupied, signature, background, classification_confidence = (
                    self._square_feature(patch)
                )
                square = _screen_cell_to_square(row, column, self._orientation)
                placement[square] = occupied
                signatures[square] = signature
                background_colors.append(((row + column) % 2, background))
                classification_confidences.append(classification_confidence)

        checker_confidence = _checkerboard_confidence(background_colors)
        confidence = min(
            checker_confidence,
            float(np.mean(classification_confidences)),
        )
        return _VisualBoardSample(
            piece_placement=tuple(placement),
            signatures=tuple(signature for signature in signatures if signature is not None),
            confidence=confidence,
            width=width,
            height=height,
            timestamp=captured_at,
        )

    def _square_feature(
        self,
        patch: NDArray[np.float32],
    ) -> tuple[bool, NDArray[np.float32], NDArray[np.float32], float]:
        background = np.median(patch, axis=(0, 1)).astype(np.float32)
        margin_y = max(1, round(patch.shape[0] * 0.11))
        margin_x = max(1, round(patch.shape[1] * 0.11))
        inner = patch[margin_y:-margin_y, margin_x:-margin_x]
        color_delta = inner - background
        foreground_mask = np.linalg.norm(color_delta, axis=2) >= 28.0

        occupancy_score = float(np.mean(foreground_mask))
        occupied = occupancy_score >= self._occupancy_threshold
        classification_confidence = min(
            1.0,
            abs(occupancy_score - self._occupancy_threshold)
            / self._occupancy_threshold,
        )

        feature = np.concatenate(
            (
                foreground_mask[:, :, None].astype(np.float32),
                color_delta / 255.0,
            ),
            axis=2,
        )
        signature = _resize_feature(feature, size=16)
        return occupied, signature, background, classification_confidence


class ChessFrameProcessor:
    """Compose capture diagnostics and recognition without retaining raw frames."""

    def __init__(self, recognizer: StableBoardRecognizer) -> None:
        self._metrics = BasicFrameProcessor()
        self._recognizer = recognizer

    def process(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> ChessFrameResult:
        return ChessFrameResult(
            frame_summary=self._metrics.process(frame, captured_at=captured_at),
            recognition=self._recognizer.recognize(frame, captured_at=captured_at),
        )


def _screen_cell_to_square(
    row: int,
    column: int,
    orientation: BoardOrientation,
) -> chess.Square:
    if orientation == BoardOrientation.WHITE:
        file_index = column
        rank_index = 7 - row
    else:
        file_index = 7 - column
        rank_index = row
    return chess.square(file_index, rank_index)


def _checkerboard_confidence(
    colors: list[tuple[int, NDArray[np.float32]]],
) -> float:
    groups = [
        np.stack([color for parity, color in colors if parity == expected_parity])
        for expected_parity in (0, 1)
    ]
    group_means = [group.mean(axis=0) for group in groups]
    between = float(np.linalg.norm(group_means[0] - group_means[1]))
    within = float(
        np.mean(
            [
                np.linalg.norm(group - group_mean, axis=1).mean()
                for group, group_mean in zip(groups, group_means, strict=True)
            ]
        )
    )
    return float(np.clip((between - within * 1.5) / 70.0, 0.0, 1.0))


def _resize_feature(feature: NDArray[np.float32], *, size: int) -> NDArray[np.float32]:
    y_edges = np.linspace(0, feature.shape[0], size + 1, dtype=int)
    x_edges = np.linspace(0, feature.shape[1], size + 1, dtype=int)
    resized = np.empty((size, size, feature.shape[2]), dtype=np.float32)
    for row in range(size):
        for column in range(size):
            block = feature[
                y_edges[row] : y_edges[row + 1],
                x_edges[column] : x_edges[column + 1],
            ]
            resized[row, column] = block.mean(axis=(0, 1))
    return resized


def _samples_are_similar(
    first: _VisualBoardSample,
    second: _VisualBoardSample,
    *,
    threshold: float,
) -> bool:
    if first.piece_placement != second.piece_placement:
        return False
    difference = float(
        np.mean(
            [
                np.mean(np.abs(first.signatures[square] - second.signatures[square]))
                for square in chess.SQUARES
            ]
        )
    )
    return difference <= threshold
