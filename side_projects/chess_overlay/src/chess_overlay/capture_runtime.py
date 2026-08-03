"""Background runtime that keeps raw capture frames away from the UI thread."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Event

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .capture import CaptureRegion, FrameProcessor, FrameSource


class CaptureWorker(QObject):
    """Grab, process, and discard frames on one bounded background thread."""

    result_ready = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        *,
        region: CaptureRegion,
        source_factory: Callable[[], FrameSource],
        processor_factory: Callable[[], FrameProcessor],
        target_fps: float,
    ) -> None:
        super().__init__()
        if target_fps <= 0:
            raise ValueError("Target FPS must be positive.")
        self._region = region
        self._source_factory = source_factory
        self._processor_factory = processor_factory
        self._frame_interval = 1.0 / target_fps
        self._stop_requested = Event()

    @Slot()
    def run(self) -> None:
        try:
            processor = self._processor_factory()
            with self._source_factory() as source:
                next_frame_at = time.perf_counter()
                while not self._stop_requested.is_set():
                    captured_at = time.perf_counter()
                    frame = source.grab(self._region)
                    if frame is not None:
                        result = processor.process(frame, captured_at=captured_at)
                        self.result_ready.emit(result)
                    del frame

                    next_frame_at += self._frame_interval
                    now = time.perf_counter()
                    if next_frame_at < now:
                        next_frame_at = now
                    if self._stop_requested.wait(next_frame_at - now):
                        break
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    def request_stop(self) -> None:
        self._stop_requested.set()


class CaptureRuntime(QObject):
    """Own one latest-frame worker and guarantee bounded shutdown."""

    result_ready = Signal(object)
    failed = Signal(str)
    stopped = Signal()

    def __init__(
        self,
        *,
        source_factory: Callable[[], FrameSource],
        processor_factory: Callable[[], FrameProcessor],
        target_fps: float = 12.0,
    ) -> None:
        super().__init__()
        self._source_factory = source_factory
        self._processor_factory = processor_factory
        self._target_fps = target_fps
        self._thread: QThread | None = None
        self._worker: CaptureWorker | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self, region: CaptureRegion) -> None:
        self.stop()

        thread = QThread(self)
        worker = CaptureWorker(
            region=region,
            source_factory=self._source_factory,
            processor_factory=self._processor_factory,
            target_fps=self._target_fps,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result_ready.connect(self.result_ready.emit)
        worker.failed.connect(self.failed.emit)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self.stopped.emit)
        thread.finished.connect(lambda: self._clear_finished_thread(thread))
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def stop(self, *, timeout_ms: int = 2_000) -> None:
        worker = self._worker
        thread = self._thread
        if worker is None or thread is None:
            return

        worker.request_stop()
        thread.quit()
        if thread.isRunning() and not thread.wait(timeout_ms):
            self.failed.emit("Die Bildschirmaufnahme konnte nicht rechtzeitig beendet werden.")
            return

        self._worker = None
        self._thread = None

    def _clear_finished_thread(self, thread: QThread) -> None:
        if self._thread is thread:
            self._worker = None
            self._thread = None
