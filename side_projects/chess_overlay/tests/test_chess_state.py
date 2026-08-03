import chess

from chess_overlay.chess_state import (
    BoardGeometry,
    BoardObservation,
    BoardOrientation,
    LegalPositionReconciler,
    ReconcileStatus,
    move_arrow,
    occupied_placement,
    square_center,
)


def observation_for(
    board: chess.Board,
    *,
    changed_squares: frozenset[chess.Square],
    confidence: float = 0.95,
    orientation: BoardOrientation = BoardOrientation.WHITE,
) -> BoardObservation:
    return BoardObservation(
        observation_id=1,
        piece_placement=occupied_placement(board),
        changed_squares=changed_squares,
        board_bounds=BoardGeometry(0, 0, 800, 800),
        orientation=orientation,
        confidence=confidence,
        timestamp=10.0,
    )


def test_reconciler_accepts_one_stable_legal_transition_and_increments_revision() -> None:
    reconciler = LegalPositionReconciler(orientation=BoardOrientation.WHITE)
    board_after = chess.Board()
    board_after.push_uci("e2e4")

    result = reconciler.reconcile(
        observation_for(board_after, changed_squares=frozenset({chess.E2, chess.E4}))
    )

    assert result.status == ReconcileStatus.MOVE_ACCEPTED
    assert result.state_changed is True
    assert result.snapshot.position_revision == 1
    assert result.snapshot.last_move_uci == "e2e4"
    assert result.snapshot.board_fen == board_after.fen()


def test_uncertain_observation_keeps_last_valid_position_unchanged() -> None:
    reconciler = LegalPositionReconciler(orientation=BoardOrientation.WHITE)
    before = reconciler.snapshot()
    board_after = chess.Board()
    board_after.push_uci("e2e4")

    result = reconciler.reconcile(
        observation_for(
            board_after,
            changed_squares=frozenset({chess.E2, chess.E4}),
            confidence=0.4,
        )
    )

    assert result.status == ReconcileStatus.UNCERTAIN
    assert result.state_changed is False
    assert result.snapshot == before
    assert reconciler.snapshot() == before


def test_ambiguous_promotion_observation_is_rejected_without_mutation() -> None:
    starting_board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1")
    reconciler = LegalPositionReconciler(
        orientation=BoardOrientation.WHITE,
        starting_board=starting_board,
    )
    visually_identical_promotion = starting_board.copy()
    visually_identical_promotion.push_uci("a7a8q")
    before = reconciler.snapshot()

    result = reconciler.reconcile(
        observation_for(
            visually_identical_promotion,
            changed_squares=frozenset({chess.A7, chess.A8}),
        )
    )

    assert result.status == ReconcileStatus.AMBIGUOUS
    assert "a7a8" in result.message
    assert result.state_changed is False
    assert reconciler.snapshot() == before


def test_invalid_visual_transition_preserves_board_and_revision() -> None:
    reconciler = LegalPositionReconciler(orientation=BoardOrientation.WHITE)
    impossible_board = chess.Board()
    impossible_board.remove_piece_at(chess.A2)
    before = reconciler.snapshot()

    result = reconciler.reconcile(
        observation_for(
            impossible_board,
            changed_squares=frozenset({chess.A2}),
        )
    )

    assert result.status == ReconcileStatus.NO_LEGAL_TRANSITION
    assert reconciler.snapshot() == before


def test_resynchronization_invalidates_analysis_with_monotonic_revision() -> None:
    reconciler = LegalPositionReconciler(orientation=BoardOrientation.WHITE)
    board_after = chess.Board()
    board_after.push_uci("e2e4")
    reconciler.reconcile(
        observation_for(board_after, changed_squares=frozenset({chess.E2, chess.E4}))
    )

    reset_snapshot = reconciler.reset_to_starting_position()

    assert reset_snapshot.position_revision == 2
    assert reset_snapshot.board_fen == chess.STARTING_FEN
    assert reset_snapshot.last_move_uci is None


def test_square_and_move_mapping_supports_both_board_orientations() -> None:
    bounds = BoardGeometry(0, 0, 800, 800)

    assert square_center(chess.G1, bounds, BoardOrientation.WHITE) == (650, 750)
    assert square_center(chess.F3, bounds, BoardOrientation.WHITE) == (550, 550)
    assert square_center(chess.G1, bounds, BoardOrientation.BLACK) == (150, 50)
    assert square_center(chess.F3, bounds, BoardOrientation.BLACK) == (250, 250)

    white_arrow = move_arrow("g1f3", bounds, BoardOrientation.WHITE)
    black_arrow = move_arrow("g1f3", bounds, BoardOrientation.BLACK)
    assert white_arrow.start == (650, 750)
    assert white_arrow.end[0] < white_arrow.start[0]
    assert white_arrow.end[1] < white_arrow.start[1]
    assert black_arrow.start == (150, 50)
    assert black_arrow.end[0] > black_arrow.start[0]
    assert black_arrow.end[1] > black_arrow.start[1]
