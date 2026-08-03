from chess_analysis_coach.models import CandidateMove, Evaluation, Recommendation
from chess_analysis_coach.presentation import format_evaluation, format_recommendation


def test_format_evaluation_handles_centipawns_and_mate() -> None:
    assert format_evaluation(Evaluation(centipawns=34)) == "+0.34"
    assert format_evaluation(Evaluation(centipawns=-125)) == "-1.25"
    assert format_evaluation(Evaluation(mate_in=3)) == "#3"
    assert format_evaluation(Evaluation(mate_in=-2)) == "-#2"


def test_format_recommendation_explains_perspective_and_variation() -> None:
    recommendation = Recommendation(
        position_fen="test-fen",
        side_to_move="White",
        time_limit_seconds=0.25,
        candidates=(
            CandidateMove(
                san="e4",
                uci="e2e4",
                evaluation=Evaluation(centipawns=34),
                principal_variation_san=("e4", "e5", "Nf3"),
            ),
        ),
    )

    output = format_recommendation(recommendation)

    assert "White to move" in output
    assert "Evaluation perspective: side to move" in output
    assert "1. e4 (e2e4)  +0.34  line: e4 e5 Nf3" in output
