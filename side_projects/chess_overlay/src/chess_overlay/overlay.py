"""Transparent Windows presentation for revision-bound chess recommendations."""

from __future__ import annotations

import ctypes
import math
import sys
from ctypes import wintypes

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCloseEvent,
    QKeyEvent,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from .chess_state import BoardGeometry, move_arrow
from .geometry import Bounds, ResizeEdge, hit_test_edges, transformed_bounds
from .overlay_models import OverlayAnalysisResult


_FRAME_MARGIN = 14
_MINIMUM_WIDTH = 320
_MINIMUM_HEIGHT = 320

_HOTKEY_TOGGLE_SETUP = 0xA001
_HOTKEY_TOGGLE_VISIBILITY = 0xA002
_HOTKEY_RESYNC = 0xA003
_WM_HOTKEY = 0x0312
_MOD_NOREPEAT = 0x4000
_VK_F6 = 0x75
_VK_F8 = 0x77
_VK_F9 = 0x78

_GWL_EXSTYLE = -20
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_LAYERED = 0x00080000
_WS_EX_NOACTIVATE = 0x08000000
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020
_WDA_EXCLUDEFROMCAPTURE = 0x00000011


class OverlayPlatformError(RuntimeError):
    """Raised when Windows cannot apply required overlay behavior."""


class OverlayWidget(QWidget):
    """Editable frame that becomes a click-through chess presentation."""

    setup_mode_changed = Signal(bool)
    presentation_visibility_changed = Signal(bool)
    resync_requested = Signal()
    closing = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chess Analysis Coach – Desktop Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self.setMinimumSize(_MINIMUM_WIDTH, _MINIMUM_HEIGHT)
        self.resize(720, 720)

        self._setup_mode = True
        self._presentation_visible = True
        self._status_message = ""
        self._capture_status = "CAPTURE PAUSIERT · F6 startet · keine Speicherung"
        self._capture_status_level = "paused"
        self._sync_status = "KALIBRIERUNG · Grundstellung im Rahmen ausrichten"
        self._sync_status_level = "waiting"
        self._analysis_status = "ANALYSE WARTET · noch keine sichere Stellung"
        self._analysis_result: OverlayAnalysisResult | None = None
        self._drag_origin: QPointF | None = None
        self._drag_bounds: Bounds | None = None
        self._drag_edges = ResizeEdge.NONE
        self._registered_hotkeys: set[int] = set()

    @property
    def setup_mode(self) -> bool:
        return self._setup_mode

    @property
    def presentation_visible(self) -> bool:
        return self._presentation_visible

    @property
    def analysis_result(self) -> OverlayAnalysisResult | None:
        return self._analysis_result

    def toggle_setup_mode(self) -> None:
        self.set_setup_mode(not self._setup_mode)

    def set_setup_mode(self, enabled: bool) -> None:
        if enabled == self._setup_mode:
            return
        try:
            self._set_windows_click_through(not enabled)
        except OverlayPlatformError as error:
            self.set_status_message(str(error))
            return

        self._setup_mode = enabled
        self._drag_origin = None
        self._drag_bounds = None
        self._drag_edges = ResizeEdge.NONE
        self.unsetCursor()
        if enabled and self._presentation_visible:
            self.raise_()
            self.activateWindow()
            self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.update()
        self.setup_mode_changed.emit(enabled)

    def toggle_presentation_visibility(self) -> None:
        self.set_presentation_visible(not self._presentation_visible)

    def set_presentation_visible(self, visible: bool) -> None:
        if visible == self._presentation_visible:
            return
        self._presentation_visible = visible
        if visible:
            self.show()
            self.raise_()
            if self._setup_mode:
                self.activateWindow()
        else:
            self.hide()
        self.presentation_visibility_changed.emit(visible)

    def request_resynchronization(self) -> None:
        self.resync_requested.emit()

    def set_status_message(self, message: str) -> None:
        self._status_message = message
        self.update()

    def set_capture_status(self, message: str, *, level: str) -> None:
        if level not in {"paused", "starting", "live", "error"}:
            raise ValueError(f"Unknown capture status level: {level}")
        self._capture_status = message
        self._capture_status_level = level
        self.update()

    def set_sync_status(self, message: str, *, level: str) -> None:
        if level not in {"waiting", "live", "error"}:
            raise ValueError(f"Unknown synchronization status level: {level}")
        self._sync_status = message
        self._sync_status_level = level
        self.update()

    def set_analysis_status(self, message: str) -> None:
        self._analysis_status = message
        self.update()

    def set_analysis_result(self, result: OverlayAnalysisResult) -> None:
        self._analysis_result = result
        self._analysis_status = f"ANALYSE AKTUELL · Revision {result.position_revision}"
        self.update()

    def clear_analysis(self, message: str) -> None:
        self._analysis_result = None
        self._analysis_status = message
        self.update()

    def exclude_from_screen_capture(self) -> None:
        """Keep overlay graphics out of the DXGI frames read behind this window."""

        if sys.platform != "win32":
            raise OverlayPlatformError(
                "Das Overlay kann nur unter Windows von der Aufnahme ausgeschlossen werden."
            )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_affinity = user32.SetWindowDisplayAffinity
        set_affinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        set_affinity.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        if not set_affinity(
            wintypes.HWND(int(self.winId())), _WDA_EXCLUDEFROMCAPTURE
        ):
            error_code = ctypes.get_last_error()
            raise OverlayPlatformError(
                "Overlay-Grafiken konnten nicht von der Aufnahme ausgeschlossen werden: "
                f"{ctypes.WinError(error_code)}"
            )

    def register_global_hotkeys(self) -> tuple[str, ...]:
        if sys.platform != "win32":
            return ("Globale Tastenkürzel sind nur unter Windows verfügbar.",)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        register_hotkey = user32.RegisterHotKey
        register_hotkey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        register_hotkey.restype = wintypes.BOOL
        hwnd = wintypes.HWND(int(self.winId()))
        failures: list[str] = []
        for identifier, virtual_key, label in (
            (_HOTKEY_TOGGLE_SETUP, _VK_F6, "F6"),
            (_HOTKEY_TOGGLE_VISIBILITY, _VK_F8, "F8"),
            (_HOTKEY_RESYNC, _VK_F9, "F9"),
        ):
            ctypes.set_last_error(0)
            if register_hotkey(hwnd, identifier, _MOD_NOREPEAT, virtual_key):
                self._registered_hotkeys.add(identifier)
            else:
                failures.append(f"{label} konnte nicht global registriert werden")
        return tuple(failures)

    def unregister_global_hotkeys(self) -> None:
        if sys.platform != "win32" or not self._registered_hotkeys:
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        unregister_hotkey = user32.UnregisterHotKey
        unregister_hotkey.argtypes = [wintypes.HWND, ctypes.c_int]
        unregister_hotkey.restype = wintypes.BOOL
        hwnd = wintypes.HWND(int(self.winId()))
        for identifier in tuple(self._registered_hotkeys):
            unregister_hotkey(hwnd, identifier)
            self._registered_hotkeys.discard(identifier)

    def nativeEvent(self, event_type: bytes, message: int) -> tuple[bool, int]:  # noqa: N802
        if sys.platform == "win32":
            native_message = wintypes.MSG.from_address(int(message))
            if native_message.message == _WM_HOTKEY:
                if native_message.wParam == _HOTKEY_TOGGLE_SETUP:
                    self.toggle_setup_mode()
                elif native_message.wParam == _HOTKEY_TOGGLE_VISIBILITY:
                    self.toggle_presentation_visibility()
                elif native_message.wParam == _HOTKEY_RESYNC:
                    self.request_resynchronization()
                return True, 0
        return super().nativeEvent(event_type, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_F6 and _HOTKEY_TOGGLE_SETUP not in self._registered_hotkeys:
            self.toggle_setup_mode()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F8 and _HOTKEY_TOGGLE_VISIBILITY not in self._registered_hotkeys:
            self.toggle_presentation_visibility()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F9 and _HOTKEY_RESYNC not in self._registered_hotkeys:
            self.request_resynchronization()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self._setup_mode:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._setup_mode or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        geometry = self.geometry()
        self._drag_origin = event.globalPosition()
        self._drag_bounds = Bounds(
            geometry.x(), geometry.y(), geometry.width(), geometry.height()
        )
        self._drag_edges = hit_test_edges(
            event.position().x(),
            event.position().y(),
            self.width(),
            self.height(),
            _FRAME_MARGIN,
        )
        self._update_cursor(self._drag_edges, dragging=True)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._setup_mode:
            super().mouseMoveEvent(event)
            return
        if (
            self._drag_origin is not None
            and self._drag_bounds is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = event.globalPosition() - self._drag_origin
            bounds = transformed_bounds(
                self._drag_bounds,
                self._drag_edges,
                round(delta.x()),
                round(delta.y()),
                minimum_width=self.minimumWidth(),
                minimum_height=self.minimumHeight(),
            )
            self.setGeometry(bounds.left, bounds.top, bounds.width, bounds.height)
            event.accept()
            return
        edges = hit_test_edges(
            event.position().x(),
            event.position().y(),
            self.width(),
            self.height(),
            _FRAME_MARGIN,
        )
        self._update_cursor(edges, dragging=False)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._setup_mode:
            self._drag_origin = None
            self._drag_bounds = None
            self._drag_edges = ResizeEdge.NONE
            self._update_cursor(
                hit_test_edges(
                    event.position().x(),
                    event.position().y(),
                    self.width(),
                    self.height(),
                    _FRAME_MARGIN,
                ),
                dragging=False,
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._setup_mode:
            painter.fillRect(self.rect(), QColor(5, 20, 31, 24))
        self._paint_frame(painter)
        if not self._setup_mode and self._analysis_result is not None:
            self._paint_best_move(painter, self._analysis_result)
        self._paint_sync_status(painter)
        if not self._setup_mode:
            self._paint_analysis_card(painter)
        self._paint_capture_status(painter)
        if self._setup_mode:
            self._paint_setup_caption(painter)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.unregister_global_hotkeys()
        self.closing.emit()
        event.accept()

    def _paint_frame(self, painter: QPainter) -> None:
        pen = QPen(
            QColor(34, 211, 238, 235 if self._setup_mode else 120),
            3 if self._setup_mode else 2,
            Qt.PenStyle.DashLine if self._setup_mode else Qt.PenStyle.SolidLine,
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(2, 2, self.width() - 4, self.height() - 4), 10, 10)
        if not self._setup_mode:
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(34, 211, 238, 235))
        handle_size = 12
        for x in (2, self.width() - handle_size - 2):
            for y in (2, self.height() - handle_size - 2):
                painter.drawRoundedRect(QRectF(x, y, handle_size, handle_size), 3, 3)

    def _paint_setup_caption(self, painter: QPainter) -> None:
        caption = "Einrichten: ziehen · Rand skalieren · F6 sperren · F8 ein/aus · F9 Resync"
        if self._status_message:
            caption = f"{caption}  |  {self._status_message}"
        self._paint_badge(
            painter,
            QRectF(18, 60, max(260, self.width() - 36), 38),
            caption,
            QColor(4, 18, 28, 225),
        )

    def _paint_sync_status(self, painter: QPainter) -> None:
        colors = {
            "waiting": QColor(202, 138, 4, 230),
            "live": QColor(22, 163, 74, 230),
            "error": QColor(220, 38, 38, 235),
        }
        self._paint_badge(
            painter,
            QRectF(18, 18, max(260, self.width() - 36), 34),
            self._sync_status,
            colors[self._sync_status_level],
        )

    def _paint_capture_status(self, painter: QPainter) -> None:
        colors = {
            "paused": QColor(71, 85, 105, 225),
            "starting": QColor(202, 138, 4, 230),
            "live": QColor(22, 163, 74, 230),
            "error": QColor(220, 38, 38, 235),
        }
        self._paint_badge(
            painter,
            QRectF(18, self.height() - 52, max(260, self.width() - 36), 34),
            self._capture_status,
            colors[self._capture_status_level],
        )

    def _paint_analysis_card(self, painter: QPainter) -> None:
        card_width = min(470.0, max(280.0, self.width() * 0.62))
        card_rect = QRectF(18, 60, card_width, 154)
        painter.setPen(QPen(QColor(148, 163, 184, 180), 1))
        painter.setBrush(QColor(4, 18, 28, 224))
        painter.drawRoundedRect(card_rect, 12, 12)
        painter.setPen(QColor(226, 232, 240))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            card_rect.adjusted(12, 8, -12, -124),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._analysis_status,
        )
        result = self._analysis_result
        if result is None or not result.candidate_moves:
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(
                card_rect.adjusted(12, 40, -12, -12),
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
                | Qt.TextFlag.TextWordWrap,
                "Sichere Stellung abwarten. Bei Fehlern F9 zur Grundstellung-Resynchronisierung drücken.",
            )
            return

        best = result.candidate_moves[0]
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(190, 242, 100))
        painter.drawText(
            card_rect.adjusted(12, 35, -12, -88),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{best.san}  ·  {best.evaluation}",
        )
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(226, 232, 240))
        detail = f"{best.explanation}\n{best.plan}"
        painter.drawText(
            card_rect.adjusted(12, 70, -12, -12),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            detail,
        )

    def _paint_best_move(
        self,
        painter: QPainter,
        result: OverlayAnalysisResult,
    ) -> None:
        if not result.candidate_moves:
            return
        bounds = BoardGeometry(4, 4, self.width() - 8, self.height() - 8)
        arrow = move_arrow(
            result.candidate_moves[0].uci,
            bounds,
            result.orientation,
        )
        start = QPointF(*arrow.start)
        end = QPointF(*arrow.end)
        radius = max(12.0, min(self.width(), self.height()) * 0.022)
        color = QColor(163, 230, 53, 225)
        painter.setPen(QPen(color, max(7.0, radius * 0.52), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)

        delta_x = end.x() - start.x()
        delta_y = end.y() - start.y()
        length = max(math.hypot(delta_x, delta_y), 1.0)
        unit_x = delta_x / length
        unit_y = delta_y / length
        base = QPointF(end.x() - unit_x * radius * 1.5, end.y() - unit_y * radius * 1.5)
        perpendicular_x = -unit_y * radius * 0.8
        perpendicular_y = unit_x * radius * 0.8
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(
            QPolygonF(
                [
                    end,
                    QPointF(base.x() + perpendicular_x, base.y() + perpendicular_y),
                    QPointF(base.x() - perpendicular_x, base.y() - perpendicular_y),
                ]
            )
        )

    def _paint_badge(
        self,
        painter: QPainter,
        rectangle: QRectF,
        text: str,
        background: QColor,
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rectangle, 9, 9)
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        visible_text = painter.fontMetrics().elidedText(
            text,
            Qt.TextElideMode.ElideRight,
            max(200, int(rectangle.width()) - 24),
        )
        painter.drawText(
            rectangle.adjusted(12, 0, -12, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            visible_text,
        )

    def _update_cursor(self, edges: ResizeEdge, *, dragging: bool) -> None:
        if edges in (
            ResizeEdge.LEFT | ResizeEdge.TOP,
            ResizeEdge.RIGHT | ResizeEdge.BOTTOM,
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in (
            ResizeEdge.RIGHT | ResizeEdge.TOP,
            ResizeEdge.LEFT | ResizeEdge.BOTTOM,
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & (ResizeEdge.LEFT | ResizeEdge.RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges & (ResizeEdge.TOP | ResizeEdge.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif dragging:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _set_windows_click_through(self, enabled: bool) -> None:
        if sys.platform != "win32":
            raise OverlayPlatformError("Klickdurchleitung wird aktuell nur unter Windows unterstützt.")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_window_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
        get_window_long.restype = ctypes.c_ssize_t
        set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_window_long.restype = ctypes.c_ssize_t
        hwnd = wintypes.HWND(int(self.winId()))
        ctypes.set_last_error(0)
        current_style = get_window_long(hwnd, _GWL_EXSTYLE)
        error_code = ctypes.get_last_error()
        if current_style == 0 and error_code:
            raise OverlayPlatformError(
                f"Windows-Fensterstil konnte nicht gelesen werden: {ctypes.WinError(error_code)}"
            )
        if enabled:
            next_style = current_style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT | _WS_EX_NOACTIVATE
        else:
            next_style = current_style & ~(_WS_EX_TRANSPARENT | _WS_EX_NOACTIVATE)
        ctypes.set_last_error(0)
        previous_style = set_window_long(hwnd, _GWL_EXSTYLE, next_style)
        error_code = ctypes.get_last_error()
        if previous_style == 0 and error_code:
            raise OverlayPlatformError(
                f"Klickdurchleitung konnte nicht gesetzt werden: {ctypes.WinError(error_code)}"
            )
        set_window_pos = user32.SetWindowPos
        set_window_pos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        set_window_pos.restype = wintypes.BOOL
        set_window_pos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE
            | _SWP_NOSIZE
            | _SWP_NOZORDER
            | _SWP_NOACTIVATE
            | _SWP_FRAMECHANGED,
        )
