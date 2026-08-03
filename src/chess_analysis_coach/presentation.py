"""Plain-text presentation for recommendation results."""

from chess_analysis_coach.models import Evaluation, Recommendation


def format_evaluation(evaluation: Evaluation) -> str:
    if evaluation.mate_in is not None:
        prefix = "#" if evaluation.mate_in >= 0 else "-#"
        return f"{prefix}{abs(evaluation.mate_in)}"

    assert evaluation.centipawns is not None
    return f"{evaluation.centipawns / 100:+.2f}"


def format_recommendation(recommendation: Recommendation) -> str:
    lines = [
        f"{recommendation.side_to_move} to move",
        "Evaluation perspective: side to move",
    ]

    for rank, candidate in enumerate(recommendation.candidates, start=1):
        variation = " ".join(candidate.principal_variation_san)
        lines.append(
            f"{rank}. {candidate.san} ({candidate.uci})  "
            f"{format_evaluation(candidate.evaluation)}  line: {variation}"
        )

    return "\n".join(lines)
