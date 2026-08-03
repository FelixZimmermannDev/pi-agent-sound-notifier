import chess
import numpy as np

from chess_overlay.chess_state import BoardOrientation
from chess_overlay.recognition import RecognitionStatus, StableBoardRecognizer


def render_board(
    board: chess.Board,
    *,
    orientation: BoardOrientation,
    square_size: int = 32,
) -> np.ndarray:
    image = np.empty((square_size * 8, square_size * 8, 3), dtype=np.uint8)
    light = np.array((203, 232, 229), dtype=np.uint8)
    dark = np.array((85, 148, 117), dtype=np.uint8)
    for row in range(8):
        for column in range(8):
            image[
                row * square_size : (row + 1) * square_size,
                column * square_size : (column + 1) * square_size,
            ] = light if (row + column) % 2 == 0 else dark

    for square, piece in board.piece_map().items():
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        if orientation == BoardOrientation.WHITE:
            row = 7 - rank_index
            column = file_index
        else:
            row = rank_index
            column = 7 - file_index
        top = row * square_size
        left = column * square_size
        inset = 8
        color = 245 if piece.color == chess.WHITE else 18
        image[
            top + inset : top + square_size - inset,
            left + inset : left + square_size - inset,
        ] = color
        stripe = 2 + piece.piece_type
        image[
            top + inset + stripe : top + inset + stripe + 2,
            left + inset - 2 : left + square_size - inset + 2,
        ] = 128
    return image


def test_recognizer_calibrates_start_and_emits_stable_move_observation() -> None:
    recognizer = StableBoardRecognizer(
        orientation=BoardOrientation.WHITE,
        stable_frame_count=2,
    )
    starting_frame = render_board(chess.Board(), orientation=BoardOrientation.WHITE)

    first = recognizer.recognize(starting_frame, captured_at=1.0)
    calibrated = recognizer.recognize(starting_frame.copy(), captured_at=1.1)

    assert first.status == RecognitionStatus.STABILIZING
    assert calibrated.status == RecognitionStatus.OBSERVATION_READY
    assert calibrated.observation is not None
    assert calibrated.observation.changed_squares == frozenset()
    recognizer.accept(calibrated.observation.observation_id)

    board_after = chess.Board()
    board_after.push_uci("e2e4")
    moved_frame = render_board(board_after, orientation=BoardOrientation.WHITE)
    changing = recognizer.recognize(moved_frame, captured_at=2.0)
    stable_move = recognizer.recognize(moved_frame.copy(), captured_at=2.1)

    assert changing.status == RecognitionStatus.STABILIZING
    assert stable_move.status == RecognitionStatus.OBSERVATION_READY
    assert stable_move.observation is not None
    assert stable_move.observation.changed_squares == frozenset(
        {chess.E2, chess.E4}
    )
    assert stable_move.observation.confidence >= 0.75


def test_recognizer_maps_black_orientation_to_same_logical_placement() -> None:
    recognizer = StableBoardRecognizer(
        orientation=BoardOrientation.BLACK,
        stable_frame_count=1,
    )

    result = recognizer.recognize(
        render_board(chess.Board(), orientation=BoardOrientation.BLACK),
        captured_at=1.0,
    )

    assert result.status == RecognitionStatus.OBSERVATION_READY
    assert result.observation is not None
    assert result.observation.piece_placement[chess.A1] is True
    assert result.observation.piece_placement[chess.E4] is False
    assert result.observation.orientation == BoardOrientation.BLACK


def test_recognizer_does_not_guess_when_board_pattern_is_lost() -> None:
    recognizer = StableBoardRecognizer(
        orientation=BoardOrientation.WHITE,
        stable_frame_count=1,
    )
    non_board_frame = np.full((256, 256, 3), 90, dtype=np.uint8)

    result = recognizer.recognize(non_board_frame, captured_at=1.0)

    assert result.status == RecognitionStatus.BOARD_LOST
    assert result.observation is None
    assert result.confidence < 0.68
