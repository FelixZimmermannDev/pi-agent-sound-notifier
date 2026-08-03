"""PGN recording for local browser games."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import chess
import chess.pgn


@dataclass(frozen=True)
class RecordedMove:
    """One played move with clock and optional live-coach context."""

    move: chess.Move
    remaining_seconds: float
    coach_comment: str | None = None


def build_pgn(
    *,
    starting_board: chess.Board,
    moves: tuple[RecordedMove, ...],
    player_color: chess.Color,
    bot_elo: int,
    result: str,
    termination: str | None,
) -> str:
    """Build a portable PGN snapshot of the current local game."""
    game = chess.pgn.Game()
    game.headers["Event"] = "Chess Analysis Coach local game"
    game.headers["Site"] = "localhost"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = "-"
    game.headers["White"] = "Player" if player_color == chess.WHITE else f"Stockfish {bot_elo}"
    game.headers["Black"] = f"Stockfish {bot_elo}" if player_color == chess.WHITE else "Player"
    game.headers["Result"] = result
    if termination is not None:
        game.headers["Termination"] = termination
    if starting_board.fen() != chess.STARTING_FEN:
        game.setup(starting_board)

    board = starting_board.copy(stack=False)
    node: chess.pgn.GameNode = game
    for recorded_move in moves:
        if recorded_move.move not in board.legal_moves:
            raise ValueError("Cannot record an illegal move in PGN.")
        node = node.add_variation(recorded_move.move)
        node.set_clock(recorded_move.remaining_seconds)
        if recorded_move.coach_comment:
            node.comment = recorded_move.coach_comment
        board.push(recorded_move.move)

    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
    return game.accept(exporter) + "\n"


def create_recording_path(directory: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid4().hex[:8]
    return directory / f"local-game-{timestamp}-{suffix}.pgn"


def save_pgn(path: Path, pgn: str) -> None:
    """Atomically replace the on-disk snapshot for one game."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(pgn, encoding="utf-8")
    temporary_path.replace(path)
