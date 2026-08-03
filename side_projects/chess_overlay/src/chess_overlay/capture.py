"""In-memory screen acquisition and frame-processing boundary.

Raw frames are never written to disk or sent over the network. A frame is handed
directly to a processor, reduced to structured measurements, and then discarded.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import dxcam
import numpy as np
from numpy.typing import NDArray

from .geometry import Bounds


class CaptureError(RuntimeError):
    """An actionable failure at the screen-capture boundary."""


@dataclass(frozen=True, slots=True)
class CaptureRegion:
    """Physical-pixel region relative to one DXGI display output."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.left < 0 or self.top < 0:
            raise ValueError("Capture region must start inside the display.")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("Capture region must have a positive size.")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_dxcam_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True, slots=True)
class FrameSummary:
    """Small non-image result retained after one raw frame is discarded."""

    sequence: int
    width: int
    height: int
    frames_per_second: float
    changed_fraction: float
    mean_rgb: tuple[int, int, int]


class FrameProcessor(Protocol):
    """Replaceable boundary that reduces one raw frame to structured data."""

    def process(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> object: ...


class FrameSource(Protocol):
    """Minimal in-memory frame source owned by the capture worker."""

    def __enter__(self) -> FrameSource: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...

    def grab(self, region: CaptureRegion) -> NDArray[np.uint8] | None: ...


class BasicFrameProcessor:
    """Prove live processing with FPS, color, and coarse change measurements."""

    def __init__(self, *, sample_step: int = 8, change_threshold: int = 18) -> None:
        if sample_step <= 0:
            raise ValueError("Sample step must be positive.")
        if not 0 <= change_threshold <= 255:
            raise ValueError("Change threshold must be between 0 and 255.")

        self._sample_step = sample_step
        self._change_threshold = change_threshold
        self._previous_gray: NDArray[np.float32] | None = None
        self._previous_time: float | None = None
        self._smoothed_fps = 0.0
        self._sequence = 0

    def process(
        self,
        frame: NDArray[np.uint8],
        *,
        captured_at: float,
    ) -> FrameSummary:
        if frame.ndim != 3 or frame.shape[2] < 3 or frame.size == 0:
            raise CaptureError("dxcam lieferte kein gültiges BGR-Bild.")

        sampled_bgr = frame[:: self._sample_step, :: self._sample_step, :3].astype(
            np.float32,
            copy=True,
        )
        mean_bgr = sampled_bgr.mean(axis=(0, 1))
        current_gray = (
            sampled_bgr[:, :, 0] * 0.114
            + sampled_bgr[:, :, 1] * 0.587
            + sampled_bgr[:, :, 2] * 0.299
        )

        changed_fraction = 0.0
        if self._previous_gray is not None:
            if self._previous_gray.shape == current_gray.shape:
                changed_fraction = float(
                    np.mean(
                        np.abs(current_gray - self._previous_gray)
                        >= self._change_threshold
                    )
                )
            else:
                changed_fraction = 1.0

        if self._previous_time is not None and captured_at > self._previous_time:
            instantaneous_fps = 1.0 / (captured_at - self._previous_time)
            if self._smoothed_fps == 0.0:
                self._smoothed_fps = instantaneous_fps
            else:
                self._smoothed_fps = self._smoothed_fps * 0.8 + instantaneous_fps * 0.2

        self._previous_gray = current_gray
        self._previous_time = captured_at
        self._sequence += 1
        height, width = frame.shape[:2]

        return FrameSummary(
            sequence=self._sequence,
            width=width,
            height=height,
            frames_per_second=self._smoothed_fps,
            changed_fraction=changed_fraction,
            mean_rgb=(
                int(round(float(mean_bgr[2]))),
                int(round(float(mean_bgr[1]))),
                int(round(float(mean_bgr[0]))),
            ),
        )


class DxcamFrameSource:
    """Acquire caller-owned access to one DXGI output without persistence."""

    def __init__(
        self,
        *,
        device_index: int,
        output_index: int,
        camera_factory: Callable[..., Any] = dxcam.create,
    ) -> None:
        self._device_index = device_index
        self._output_index = output_index
        self._camera_factory = camera_factory
        self._camera: Any | None = None

    def __enter__(self) -> DxcamFrameSource:
        try:
            self._camera = self._camera_factory(
                device_idx=self._device_index,
                output_idx=self._output_index,
                output_color="BGR",
                max_buffer_len=2,
                processor_backend="numpy",
            )
        except Exception as error:
            raise CaptureError(f"dxcam konnte nicht gestartet werden: {error}") from error
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self._camera is not None:
            try:
                self._camera.release()
            finally:
                self._camera = None

    def grab(self, region: CaptureRegion) -> NDArray[np.uint8] | None:
        if self._camera is None:
            raise CaptureError("dxcam wurde vor der Aufnahme nicht gestartet.")
        try:
            return self._camera.grab(
                region=region.as_dxcam_tuple(),
                copy=False,
                new_frame_only=False,
            )
        except Exception as error:
            raise CaptureError(f"Bildschirmbereich konnte nicht gelesen werden: {error}") from error


def capture_region_for_overlay(
    overlay: Bounds,
    display: Bounds,
    *,
    device_pixel_ratio: float,
    inset: int = 4,
) -> CaptureRegion:
    """Map logical Qt window bounds to physical pixels on one display."""

    if device_pixel_ratio <= 0:
        raise ValueError("Device pixel ratio must be positive.")
    if inset < 0:
        raise ValueError("Capture inset cannot be negative.")
    if overlay.width <= inset * 2 or overlay.height <= inset * 2:
        raise CaptureError("Der Overlay-Rahmen ist zu klein für eine Aufnahme.")
    if (
        overlay.left < display.left
        or overlay.top < display.top
        or overlay.right > display.right
        or overlay.bottom > display.bottom
    ):
        raise CaptureError(
            "Der Overlay-Rahmen muss vollständig auf dem Hauptmonitor liegen."
        )

    left = math.floor((overlay.left + inset - display.left) * device_pixel_ratio)
    top = math.floor((overlay.top + inset - display.top) * device_pixel_ratio)
    right = math.ceil((overlay.right - inset - display.left) * device_pixel_ratio)
    bottom = math.ceil((overlay.bottom - inset - display.top) * device_pixel_ratio)
    return CaptureRegion(left, top, right, bottom)


def discover_primary_dxcam_output() -> tuple[int, int]:
    """Ask dxcam for the primary DXGI device/output pair."""

    try:
        output_info = dxcam.output_info()
    except Exception as error:
        raise CaptureError(f"dxcam konnte die Monitore nicht abfragen: {error}") from error
    return primary_dxcam_output(output_info)


def primary_dxcam_output(output_info: str) -> tuple[int, int]:
    """Extract the DXGI device/output indices marked as the primary display."""

    match = re.search(
        r"Device\[(?P<device>\d+)]\s+Output\[(?P<output>\d+)]:[^\n]*Primary:True",
        output_info,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise CaptureError("dxcam konnte den Hauptmonitor nicht bestimmen.")
    return int(match.group("device")), int(match.group("output"))
