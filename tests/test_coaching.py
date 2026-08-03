import chess

from chess_analysis_coach.coaching import explain_candidate
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


def test_coaching_cue_identifies_a_check() -> None:
    board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")

    explanation = explain_candidate(board, candidate(board, "e2b5"))

    assert "unter Schach" in explanation
