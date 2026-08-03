import chess

from chess_analysis_coach.coaching import (
    build_candidate_forecast,
    explain_candidate,
    explain_candidate_plan,
)
from chess_analysis_coach.models import CandidateMove, Evaluation


def candidate(board: chess.Board, uci: str) -> CandidateMove:
    move = chess.Move.from_uci(uci)
    return CandidateMove(
        san=board.san(move),
        uci=uci,
        evaluation=Evaluation(centipawns=50),
        principal_variation_san=(board.san(move),),
    )


def test_coaching_cue_identifies_castling() -> None:
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

    explanation = explain_candidate(board, candidate(board, "e1g1"))

    assert "Rochiert" in explanation
    assert "Königssicherheit" in explanation


def test_coaching_plan_summarizes_goal_reply_and_next_step() -> None:
    board = chess.Board()
    planned_candidate = CandidateMove(
        san="e4",
        uci="e2e4",
        evaluation=Evaluation(centipawns=35),
        principal_variation_san=("e4", "e5", "Nf3"),
        principal_variation_uci=("e2e4", "e7e5", "g1f3"),
    )

    forecast = build_candidate_forecast(board, planned_candidate)
    explanation = explain_candidate_plan(board, planned_candidate)

    assert forecast.phase == "opening"
    assert forecast.context_label == "Eröffnung · positionell"
    assert not forecast.opponent_relevant
    assert not forecast.own_follow_up_relevant
    assert "Kontrolle im Zentrum" in explanation
    assert "Erwartete Antwort: e5" in explanation
    assert "Nächster eigener Schritt: Nf3" in explanation


def test_coaching_forecast_marks_tactical_opponent_capture_as_relevant() -> None:
    board = chess.Board("4k3/8/3p4/8/4P3/8/8/4K3 w - - 0 1")
    planned_candidate = CandidateMove(
        san="e5",
        uci="e4e5",
        evaluation=Evaluation(centipawns=10),
        principal_variation_san=("e5", "dxe5"),
        principal_variation_uci=("e4e5", "d6e5"),
    )

    forecast = build_candidate_forecast(board, planned_candidate)

    assert forecast.phase == "endgame"
    assert forecast.tactical
    assert forecast.opponent_reply_san == "dxe5"
    assert forecast.opponent_relevant
    assert "Material" in forecast.opponent_counter


def test_coaching_cue_identifies_a_check() -> None:
    board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")

    explanation = explain_candidate(board, candidate(board, "e2b5"))

    assert "unter Schach" in explanation
