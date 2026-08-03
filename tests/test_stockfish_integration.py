"""Opt-in smoke test for the real locally installed Stockfish executable."""

import os
from pathlib import Path
import shutil

import chess
import pytest

from chess_analysis_coach.cli import resolve_engine_path
from chess_analysis_coach.stockfish import MIN_STOCKFISH_ELO, StockfishAnalyzer

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_STOCKFISH_INTEGRATION") != "1",
    reason="set RUN_STOCKFISH_INTEGRATION=1 to run the real Stockfish smoke test",
)


def test_real_stockfish_returns_legal_analysis_and_limited_strength_move() -> None:
    engine_path = resolve_engine_path(None)
    if not Path(engine_path).is_file() and shutil.which(engine_path) is None:
        pytest.fail(f"Stockfish executable was not found: {engine_path}")

    board = chess.Board()
    original_fen = board.fen()

    with StockfishAnalyzer(engine_path) as analyzer:
        candidates = analyzer.analyze(
            board,
            time_limit_seconds=0.05,
            candidate_count=2,
        )
        bot_move = analyzer.choose_move(
            board,
            time_limit_seconds=0.05,
            strength_elo=MIN_STOCKFISH_ELO,
        )

    assert 1 <= len(candidates) <= 2
    assert all(chess.Move.from_uci(candidate.uci) in board.legal_moves for candidate in candidates)
    assert bot_move in board.legal_moves
    assert board.fen() == original_fen
