"""Recognition check using the exact SVG piece source used by the local web board."""

import chess
import chess.svg
import numpy as np
from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from chess_overlay.chess_state import BoardOrientation
from chess_overlay.recognition import RecognitionStatus, StableBoardRecognizer


def render_local_web_board(board: chess.Board, *, square_size: int = 64) -> np.ndarray:
    application = QApplication.instance() or QApplication([])
    assert application is not None
    image = QImage(square_size * 8, square_size * 8, QImage.Format.Format_RGB888)
    painter = QPainter(image)
    for row in range(8):
        for column in range(8):
            color = QColor("#e5e8cb" if (row + column) % 2 == 0 else "#759455")
            painter.fillRect(
                column * square_size,
                row * square_size,
                square_size,
                square_size,
                color,
            )
            piece = board.piece_at(chess.square(column, 7 - row))
            if piece is None:
                continue
            svg = chess.svg.piece(piece, size=100).encode()
            renderer = QSvgRenderer(QByteArray(svg))
            margin = square_size * 0.06
            renderer.render(
                painter,
                QRectF(
                    column * square_size + margin,
                    row * square_size + margin,
                    square_size - margin * 2,
                    square_size - margin * 2,
                ),
            )
    painter.end()
    rgb = np.frombuffer(
        image.bits(),
        dtype=np.uint8,
        count=image.sizeInBytes(),
    ).reshape(image.height(), image.bytesPerLine())
    rgb = rgb[:, : image.width() * 3].reshape(image.height(), image.width(), 3)
    return rgb[:, :, ::-1].copy()


def test_recognizer_tracks_move_with_local_web_board_colors_and_piece_svgs() -> None:
    recognizer = StableBoardRecognizer(
        orientation=BoardOrientation.WHITE,
        stable_frame_count=2,
    )
    start_frame = render_local_web_board(chess.Board())
    recognizer.recognize(start_frame, captured_at=1.0)
    calibrated = recognizer.recognize(start_frame, captured_at=1.1)
    assert calibrated.observation is not None
    recognizer.accept(calibrated.observation.observation_id)

    moved_board = chess.Board()
    moved_board.push_uci("e2e4")
    moved_frame = render_local_web_board(moved_board)
    recognizer.recognize(moved_frame, captured_at=2.0)
    result = recognizer.recognize(moved_frame, captured_at=2.1)

    assert result.status == RecognitionStatus.OBSERVATION_READY
    assert result.observation is not None
    assert result.observation.changed_squares == frozenset({chess.E2, chess.E4})
    assert result.observation.confidence >= 0.75
