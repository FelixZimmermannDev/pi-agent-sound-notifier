from PySide6.QtWidgets import QApplication

from chess_overlay.chess_state import BoardGeometry, BoardOrientation
from chess_overlay.overlay import OverlayWidget
from chess_overlay.overlay_models import OverlayAnalysisResult, OverlayCandidate


def test_f8_visibility_toggle_preserves_current_analysis_state() -> None:
    application = QApplication.instance() or QApplication([])
    assert application is not None
    overlay = OverlayWidget()
    analysis = OverlayAnalysisResult(
        position_revision=3,
        candidate_moves=(
            OverlayCandidate(
                rank=1,
                san="Nf3",
                uci="g1f3",
                evaluation="+0.25",
                principal_variation_san=("Nf3", "Nf6"),
                explanation="Entwickelt den Springer.",
                plan="Ziel: Figuren entwickeln.",
            ),
        ),
        board_bounds=BoardGeometry(0, 0, 800, 800),
        orientation=BoardOrientation.WHITE,
    )
    visibility_changes: list[bool] = []
    overlay.presentation_visibility_changed.connect(visibility_changes.append)
    overlay.set_analysis_result(analysis)
    overlay.show()

    overlay.toggle_presentation_visibility()
    assert overlay.presentation_visible is False
    assert overlay.isVisible() is False
    assert overlay.analysis_result == analysis

    overlay.toggle_presentation_visibility()
    assert overlay.presentation_visible is True
    assert overlay.isVisible() is True
    assert overlay.analysis_result == analysis
    assert visibility_changes == [False, True]
    overlay.close()
