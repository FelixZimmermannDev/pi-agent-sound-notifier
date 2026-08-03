from __future__ import annotations

import numpy as np
import pytest

from chess_overlay.capture import (
    BasicFrameProcessor,
    CaptureError,
    DxcamFrameSource,
    capture_region_for_overlay,
    primary_dxcam_output,
)
from chess_overlay.geometry import Bounds


def test_overlay_bounds_are_mapped_to_physical_display_pixels() -> None:
    region = capture_region_for_overlay(
        Bounds(left=100, top=50, width=600, height=500),
        Bounds(left=0, top=0, width=1920, height=1080),
        device_pixel_ratio=2.0,
        inset=4,
    )

    assert region.as_dxcam_tuple() == (208, 108, 1392, 1092)
    assert region.width == 1184
    assert region.height == 984


def test_capture_region_rejects_overlay_crossing_display_boundary() -> None:
    with pytest.raises(CaptureError, match="vollständig auf dem Hauptmonitor"):
        capture_region_for_overlay(
            Bounds(left=1700, top=50, width=400, height=400),
            Bounds(left=0, top=0, width=1920, height=1080),
            device_pixel_ratio=1.0,
        )


def test_primary_dxcam_output_reads_device_and_output_indices() -> None:
    info = (
        "Device[0] Output[0]: Res:(1920, 1080) Rot:0 Primary:False\n"
        "Device[1] Output[2]: Res:(2560, 1440) Rot:0 Primary:True"
    )

    assert primary_dxcam_output(info) == (1, 2)


def test_frame_processor_reduces_bgr_frame_without_mutating_it() -> None:
    frame = np.empty((16, 24, 3), dtype=np.uint8)
    frame[:] = (10, 20, 30)
    original = frame.copy()
    processor = BasicFrameProcessor(sample_step=2)

    summary = processor.process(frame, captured_at=10.0)

    assert summary.sequence == 1
    assert (summary.width, summary.height) == (24, 16)
    assert summary.mean_rgb == (30, 20, 10)
    assert summary.changed_fraction == 0.0
    assert summary.frames_per_second == 0.0
    np.testing.assert_array_equal(frame, original)


def test_frame_processor_reports_change_and_smoothed_capture_rate() -> None:
    processor = BasicFrameProcessor(sample_step=2, change_threshold=18)
    dark_frame = np.zeros((16, 24, 3), dtype=np.uint8)
    bright_frame = np.full((16, 24, 3), 255, dtype=np.uint8)
    processor.process(dark_frame, captured_at=20.0)

    summary = processor.process(bright_frame, captured_at=20.1)

    assert summary.sequence == 2
    assert summary.changed_fraction == 1.0
    assert summary.frames_per_second == pytest.approx(10.0)


def test_dxcam_source_releases_camera_and_requests_reusable_memory() -> None:
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    factory_arguments: dict[str, object] = {}

    class FakeCamera:
        released = False

        def grab(self, **kwargs):
            assert kwargs["copy"] is False
            return frame

        def release(self) -> None:
            self.released = True

    camera = FakeCamera()

    def camera_factory(**kwargs):
        factory_arguments.update(kwargs)
        return camera

    with DxcamFrameSource(
        device_index=1,
        output_index=2,
        camera_factory=camera_factory,
    ) as source:
        captured = source.grab(
            capture_region_for_overlay(
                Bounds(0, 0, 16, 16),
                Bounds(0, 0, 100, 100),
                device_pixel_ratio=1.0,
                inset=0,
            )
        )
        assert captured is frame

    assert camera.released is True
    assert factory_arguments["device_idx"] == 1
    assert factory_arguments["output_idx"] == 2
    assert factory_arguments["max_buffer_len"] == 2
