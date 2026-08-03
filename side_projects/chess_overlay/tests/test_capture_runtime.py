from __future__ import annotations

import numpy as np
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from chess_overlay.capture import BasicFrameProcessor, CaptureRegion
from chess_overlay.capture_runtime import CaptureRuntime


def test_runtime_processes_latest_frame_and_stops_with_resource_cleanup() -> None:
    application = QApplication.instance() or QApplication([])
    assert application is not None
    frame = np.zeros((12, 12, 3), dtype=np.uint8)
    summaries = []
    errors: list[str] = []
    timed_out = False

    class FakeSource:
        released = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            self.released = True

        def grab(self, region):
            assert region == CaptureRegion(0, 0, 12, 12)
            return frame

    source = FakeSource()
    runtime = CaptureRuntime(
        source_factory=lambda: source,
        processor_factory=BasicFrameProcessor,
        target_fps=30,
    )
    runtime.result_ready.connect(summaries.append)
    runtime.failed.connect(errors.append)
    event_loop = QEventLoop()

    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)

    def stop_after_first_summary(summary) -> None:
        del summary
        timeout_timer.stop()
        runtime.stop(timeout_ms=1_000)
        event_loop.quit()

    def fail_on_timeout() -> None:
        nonlocal timed_out
        timed_out = True
        runtime.stop(timeout_ms=1_000)
        event_loop.quit()

    runtime.result_ready.connect(stop_after_first_summary)
    timeout_timer.timeout.connect(fail_on_timeout)
    timeout_timer.start(2_000)
    runtime.start(CaptureRegion(0, 0, 12, 12))
    event_loop.exec()

    assert timed_out is False
    assert errors == []
    assert len(summaries) == 1
    assert source.released is True
    assert runtime.is_running is False
