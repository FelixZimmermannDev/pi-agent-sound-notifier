"""Desktop overlay bootstrap and end-to-end local chess coordination."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from chess_analysis_coach.background_analysis import (
    BackgroundAnalysisFailure,
    LatestPositionAnalysisCoordinator,
    RevisionedAnalysisResult,
    RevisionedPosition,
)
from chess_analysis_coach.engine_discovery import resolve_engine_path
from chess_analysis_coach.stockfish import (
    MAX_STOCKFISH_ELO,
    MIN_STOCKFISH_ELO,
    StockfishAnalyzer,
)

from .capture import (
    CaptureError,
    CaptureRegion,
    DxcamFrameSource,
    capture_region_for_overlay,
    discover_primary_dxcam_output,
)
from .capture_runtime import CaptureRuntime
from .chess_state import (
    BoardOrientation,
    LegalPositionReconciler,
    PositionSnapshot,
    ReconcileStatus,
)
from .geometry import Bounds
from .overlay import OverlayPlatformError, OverlayWidget
from .overlay_models import build_overlay_analysis_result
from .recognition import (
    ChessFrameProcessor,
    ChessFrameResult,
    RecognitionStatus,
    StableBoardRecognizer,
)


_ORGANIZATION = "ChessAnalysisCoach"
_APPLICATION = "ChessDesktopOverlay"
_DEFAULT_TIME_MS = 250
_DEFAULT_CANDIDATES = 1
_DEFAULT_STABLE_FRAMES = 3


class _AnalysisSignalBridge(QObject):
    result_ready = Signal(object)
    failure = Signal(object)
    analysis_started = Signal(int)


class OverlayController:
    """Coordinate capture, legal synchronization, background analysis, and UI."""

    def __init__(
        self,
        application: QApplication,
        *,
        orientation: BoardOrientation,
        engine_path: str,
        time_limit_seconds: float,
        candidate_count: int,
        coach_elo: int | None,
        stable_frame_count: int,
        reset_geometry: bool,
    ) -> None:
        self.application = application
        self.settings = QSettings(_ORGANIZATION, _APPLICATION)
        self.overlay = OverlayWidget()
        self.recognizer = StableBoardRecognizer(
            orientation=orientation,
            stable_frame_count=stable_frame_count,
        )
        self.reconciler = LegalPositionReconciler(orientation=orientation)
        self._current_snapshot = self.reconciler.snapshot()
        self._capture_exclusion_ready = False
        self.capture_runtime: CaptureRuntime | None = None
        self.tray_icon: QSystemTrayIcon | None = None
        self.mode_action: QAction | None = None
        self.visibility_action: QAction | None = None
        self._shutting_down = False

        self.analysis_bridge = _AnalysisSignalBridge()
        self.analysis_bridge.result_ready.connect(self._show_analysis_result)
        self.analysis_bridge.failure.connect(self._show_analysis_failure)
        self.analysis_bridge.analysis_started.connect(self._show_analysis_started)
        self.analysis_coordinator = LatestPositionAnalysisCoordinator(
            lambda: StockfishAnalyzer(engine_path),
            time_limit_seconds=time_limit_seconds,
            candidate_count=candidate_count,
            strength_elo=coach_elo,
            on_result=self.analysis_bridge.result_ready.emit,
            on_failure=self.analysis_bridge.failure.emit,
            on_analysis_started=self.analysis_bridge.analysis_started.emit,
        )

        self.overlay.setup_mode_changed.connect(self._sync_mode_action)
        self.overlay.setup_mode_changed.connect(self._handle_setup_mode_changed)
        self.overlay.presentation_visibility_changed.connect(
            self._sync_visibility_action
        )
        self.overlay.resync_requested.connect(self.resynchronize)
        self.overlay.closing.connect(self.application.quit)
        self.application.aboutToQuit.connect(self._shutdown)

        saved_geometry = self.settings.value("overlay_geometry")
        if (
            reset_geometry
            or saved_geometry is None
            or not self.overlay.restoreGeometry(saved_geometry)
        ):
            self.center_overlay()
        elif QApplication.screenAt(self.overlay.frameGeometry().center()) is None:
            self.center_overlay()

        self._create_tray_icon()
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

        try:
            self.overlay.exclude_from_screen_capture()
            self._capture_exclusion_ready = True
        except OverlayPlatformError as error:
            self.overlay.set_capture_status(
                f"CAPTURE GESPERRT · {error}", level="error"
            )

        self._initialize_capture()
        hotkey_failures = self.overlay.register_global_hotkeys()
        if hotkey_failures:
            self.overlay.set_status_message(
                "; ".join(hotkey_failures) + ". Das Tray-Menü bleibt verfügbar."
            )
        self.analysis_coordinator.start()

    def _initialize_capture(self) -> None:
        try:
            device_index, output_index = discover_primary_dxcam_output()
        except CaptureError as error:
            self.overlay.set_capture_status(
                f"CAPTURE NICHT VERFÜGBAR · {error}", level="error"
            )
            return

        self.capture_runtime = CaptureRuntime(
            source_factory=lambda: DxcamFrameSource(
                device_index=device_index,
                output_index=output_index,
            ),
            processor_factory=lambda: ChessFrameProcessor(self.recognizer),
            target_fps=12.0,
        )
        self.capture_runtime.result_ready.connect(self._handle_frame_result)
        self.capture_runtime.failed.connect(self._show_capture_error)

    def _handle_setup_mode_changed(self, setup_mode: bool) -> None:
        if setup_mode:
            if self.capture_runtime is not None:
                self.capture_runtime.stop()
            self.overlay.set_capture_status(
                "CAPTURE PAUSIERT · F6 startet · keine Speicherung",
                level="paused",
            )
            return

        if not self._capture_exclusion_ready:
            self.overlay.set_capture_status(
                "CAPTURE GESPERRT · Overlay konnte nicht sicher ausgeblendet werden",
                level="error",
            )
            return
        if self.capture_runtime is None:
            self.overlay.set_capture_status(
                "CAPTURE NICHT VERFÜGBAR · F6 zum Bearbeiten",
                level="error",
            )
            return

        try:
            region = self._current_capture_region()
        except CaptureError as error:
            self.overlay.set_capture_status(f"CAPTUREFEHLER · {error}", level="error")
            return

        self.overlay.set_capture_status(
            f"CAPTURE STARTET · {region.width}×{region.height} · nur RAM",
            level="starting",
        )
        self.capture_runtime.start(region)

    def _current_capture_region(self) -> CaptureRegion:
        primary_screen = self.application.primaryScreen()
        if primary_screen is None:
            raise CaptureError("Windows meldet keinen Hauptmonitor.")
        display_geometry = primary_screen.geometry()
        overlay_geometry = self.overlay.frameGeometry()
        return capture_region_for_overlay(
            Bounds(
                overlay_geometry.x(),
                overlay_geometry.y(),
                overlay_geometry.width(),
                overlay_geometry.height(),
            ),
            Bounds(
                display_geometry.x(),
                display_geometry.y(),
                display_geometry.width(),
                display_geometry.height(),
            ),
            device_pixel_ratio=primary_screen.devicePixelRatio(),
            inset=0,
        )

    def _handle_frame_result(self, result: ChessFrameResult) -> None:
        summary = result.frame_summary
        self.overlay.set_capture_status(
            "CAPTURE LIVE · "
            f"{summary.frames_per_second:.1f} FPS · "
            f"{summary.width}×{summary.height} · nur RAM",
            level="live",
        )
        recognition = result.recognition
        if recognition.status == RecognitionStatus.SYNCHRONIZED:
            self.overlay.set_sync_status(recognition.message, level="live")
            return
        if recognition.status == RecognitionStatus.AWAITING_RECONCILIATION:
            return
        if recognition.status in {
            RecognitionStatus.CALIBRATING,
            RecognitionStatus.STABILIZING,
        }:
            self.overlay.set_sync_status(recognition.message, level="waiting")
            self.overlay.clear_analysis("ANALYSE PAUSIERT · Stellung noch nicht stabil")
            return
        if recognition.status == RecognitionStatus.BOARD_LOST:
            self.overlay.set_sync_status(recognition.message, level="error")
            self.overlay.clear_analysis("ANALYSE AUSGEBLENDET · Brett nicht sicher")
            return

        observation = recognition.observation
        if observation is None:
            return
        reconciled = self.reconciler.reconcile(observation)
        if reconciled.status in {
            ReconcileStatus.SYNCHRONIZED,
            ReconcileStatus.MOVE_ACCEPTED,
        }:
            self.recognizer.accept(observation.observation_id)
            self._current_snapshot = reconciled.snapshot
            self.overlay.set_sync_status(reconciled.message, level="live")
            self._submit_current_position()
            return

        self.overlay.set_sync_status(reconciled.message, level="error")
        self.overlay.clear_analysis(
            "ANALYSE AUSGEBLENDET · keine sichere legale Synchronisierung"
        )

    def _submit_current_position(self) -> None:
        board = self._current_snapshot.board()
        if board.is_game_over(claim_draw=True):
            self.overlay.clear_analysis("PARTIE BEENDET · keine legalen Züge")
            return
        self.overlay.clear_analysis(
            f"ANALYSE EINGEREIHT · Revision {self._current_snapshot.position_revision}"
        )
        try:
            self.analysis_coordinator.submit(
                RevisionedPosition(
                    self._current_snapshot.position_revision,
                    self._current_snapshot.board_fen,
                )
            )
        except RuntimeError as error:
            self.overlay.clear_analysis(f"ANALYSEFEHLER · {error}")

    def _show_analysis_started(self, position_revision: int) -> None:
        if position_revision != self._current_snapshot.position_revision:
            return
        self.overlay.set_analysis_status(
            f"ANALYSE LÄUFT · Revision {position_revision} · bounded"
        )

    def _show_analysis_result(self, result: RevisionedAnalysisResult) -> None:
        if result.position_revision != self._current_snapshot.position_revision:
            return
        if result.recommendation.position_fen != self._current_snapshot.board_fen:
            return
        self.overlay.set_analysis_result(
            build_overlay_analysis_result(self._current_snapshot, result)
        )

    def _show_analysis_failure(self, failure: BackgroundAnalysisFailure) -> None:
        if (
            failure.position_revision is not None
            and failure.position_revision != self._current_snapshot.position_revision
        ):
            return
        self.overlay.clear_analysis(f"ANALYSEFEHLER · {failure.message}")

    def _show_capture_error(self, message: str) -> None:
        self.overlay.set_capture_status(f"CAPTUREFEHLER · {message}", level="error")
        self.overlay.clear_analysis("ANALYSE AUSGEBLENDET · Capturefehler")

    def resynchronize(self) -> None:
        self.recognizer.reset()
        self._current_snapshot = self.reconciler.reset_to_starting_position()
        self.overlay.set_sync_status(
            "RESYNC · Grundstellung anzeigen und stabil halten",
            level="waiting",
        )
        self.overlay.clear_analysis(
            f"ANALYSE PAUSIERT · Resync Revision {self._current_snapshot.position_revision}"
        )

    def center_overlay(self) -> None:
        screen = self.application.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        size = max(320, min(720, available.width() - 80, available.height() - 80))
        left = available.x() + (available.width() - size) // 2
        top = available.y() + (available.height() - size) // 2
        self.overlay.setGeometry(left, top, size, size)

    def _create_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self._build_icon(), self.application)
        tray.setToolTip("Chess Analysis Coach – Desktop Overlay")
        menu = QMenu()
        self.mode_action = menu.addAction("Rahmen sperren / Capture starten (F6)")
        self.mode_action.triggered.connect(self.overlay.toggle_setup_mode)
        self.visibility_action = menu.addAction("Overlay ausblenden (F8)")
        self.visibility_action.triggered.connect(
            self.overlay.toggle_presentation_visibility
        )
        menu.addAction("Auf Grundstellung resynchronisieren (F9)", self.resynchronize)
        menu.addAction("Auf Hauptbildschirm zentrieren", self.center_overlay)
        menu.addSeparator()
        menu.addAction("Beenden", self.application.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._handle_tray_activation)
        tray.show()
        self.tray_icon = tray

    def _sync_mode_action(self, setup_mode: bool) -> None:
        if self.mode_action is None:
            return
        self.mode_action.setText(
            "Rahmen sperren / Capture starten (F6)"
            if setup_mode
            else "Capture stoppen / Rahmen bearbeiten (F6)"
        )

    def _sync_visibility_action(self, visible: bool) -> None:
        if self.visibility_action is not None:
            self.visibility_action.setText(
                "Overlay ausblenden (F8)" if visible else "Overlay einblenden (F8)"
            )

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.overlay.toggle_presentation_visibility()

    def _shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        if self.capture_runtime is not None:
            self.capture_runtime.stop()
        try:
            self.analysis_coordinator.close(timeout_seconds=5.0)
        except RuntimeError as error:
            self.overlay.set_status_message(str(error))
        self.overlay.unregister_global_hotkeys()
        self.settings.setValue("overlay_geometry", self.overlay.saveGeometry())
        self.settings.sync()

    @staticmethod
    def _build_icon() -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(4, 18, 28))
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        painter.setBrush(QColor(163, 230, 53))
        painter.drawEllipse(13, 35, 16, 16)
        painter.drawEllipse(36, 13, 16, 16)
        painter.setPen(QColor(163, 230, 53))
        pen = painter.pen()
        pen.setWidth(6)
        painter.setPen(pen)
        painter.drawLine(24, 40, 42, 22)
        painter.end()
        return QIcon(pixmap)


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("muss eine ganze Zahl sein") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("muss größer als null sein")
    return parsed


def _candidate_count(value: str) -> int:
    parsed = _positive_integer(value)
    if parsed > 3:
        raise argparse.ArgumentTypeError("muss zwischen 1 und 3 liegen")
    return parsed


def _stockfish_elo(value: str) -> int:
    parsed = _positive_integer(value)
    if not MIN_STOCKFISH_ELO <= parsed <= MAX_STOCKFISH_ELO:
        raise argparse.ArgumentTypeError(
            f"muss zwischen {MIN_STOCKFISH_ELO} und {MAX_STOCKFISH_ELO} liegen"
        )
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-overlay",
        description="Lokales DXCAM-Schachoverlay für erlaubtes Offline-Training.",
    )
    parser.add_argument(
        "--orientation",
        choices=("white", "black"),
        default="white",
        help="Farbe am unteren Brettrand (Standard: white)",
    )
    parser.add_argument("--engine", metavar="PATH", help="Stockfish executable")
    parser.add_argument(
        "--time-ms",
        type=_positive_integer,
        default=_DEFAULT_TIME_MS,
        help=f"begrenzte Analysezeit pro Stellung (Standard: {_DEFAULT_TIME_MS} ms)",
    )
    parser.add_argument(
        "--candidates",
        type=_candidate_count,
        default=_DEFAULT_CANDIDATES,
        help=f"Anzahl der Kandidaten 1-3 (Standard: {_DEFAULT_CANDIDATES})",
    )
    parser.add_argument(
        "--coach-elo",
        type=_stockfish_elo,
        help="optionale begrenzte Stockfish-Coach-Stärke",
    )
    parser.add_argument(
        "--stable-frames",
        type=_positive_integer,
        default=_DEFAULT_STABLE_FRAMES,
        help=f"übereinstimmende Frames vor Annahme (Standard: {_DEFAULT_STABLE_FRAMES})",
    )
    parser.add_argument(
        "--reset-geometry",
        action="store_true",
        help="gespeicherte Position verwerfen und Overlay zentrieren",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if sys.platform != "win32":
        print("Das Desktop-Overlay unterstützt aktuell nur Windows.", file=sys.stderr)
        return 2

    application = QApplication([sys.argv[0]])
    application.setApplicationName("Chess Desktop Overlay")
    application.setOrganizationName(_ORGANIZATION)
    application.setQuitOnLastWindowClosed(False)
    controller = OverlayController(
        application,
        orientation=BoardOrientation(args.orientation),
        engine_path=resolve_engine_path(args.engine),
        time_limit_seconds=args.time_ms / 1000,
        candidate_count=args.candidates,
        coach_elo=args.coach_elo,
        stable_frame_count=args.stable_frames,
        reset_geometry=args.reset_geometry,
    )
    exit_code = application.exec()
    controller._shutdown()
    return exit_code
