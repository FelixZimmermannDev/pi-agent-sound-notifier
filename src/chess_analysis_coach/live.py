"""Terminal coordination for a permitted interactive local game."""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import chess

from chess_analysis_coach.application import PositionAnalyzer, recommend_moves
from chess_analysis_coach.errors import SessionError
from chess_analysis_coach.presentation import format_recommendation
from chess_analysis_coach.session import LocalGameSession


@runtime_checkable
class LocalGameEngine(PositionAnalyzer, Protocol):
    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move: ...


InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def run_local_game(
    engine: LocalGameEngine,
    *,
    board: chess.Board,
    player_color: chess.Color,
    bot_elo: int,
    coach_elo: int | None,
    coach_time_seconds: float,
    bot_time_seconds: float,
    candidate_count: int,
    input_function: InputFunction = input,
    output_function: OutputFunction = print,
) -> None:
    """Play one synchronous local prototype game with advice at each position."""
    session = LocalGameSession(board, player_color=player_color)
    player_name = "White" if player_color == chess.WHITE else "Black"
    coach_strength = "full strength" if coach_elo is None else f"Elo {coach_elo}"

    output_function(
        f"Local prototype: you are {player_name}; opponent Elo {bot_elo}; "
        f"coach {coach_strength}."
    )
    output_function("Commands: SAN/UCI move, undo, fen, help, or quit.")
    _show_board(session.snapshot(), output_function)
    analyzed_revision: int | None = None

    while True:
        current_board = session.snapshot()
        if session.is_game_over:
            _show_game_result(current_board, output_function)
            return

        if analyzed_revision != session.revision:
            output_function("\nLive recommendation for the current position:")
            recommendation = recommend_moves(
                current_board,
                engine,
                time_limit_seconds=coach_time_seconds,
                candidate_count=candidate_count,
                strength_elo=coach_elo,
            )
            output_function(format_recommendation(recommendation))
            analyzed_revision = session.revision

        if session.is_player_turn:
            try:
                entered_value = input_function("Your move > ").strip()
            except (EOFError, KeyboardInterrupt):
                output_function("\nLocal game ended by the player.")
                return

            command = entered_value.lower()
            if command in {"quit", "exit"}:
                output_function("Local game ended by the player.")
                return
            if command == "help":
                output_function(
                    "Enter SAN such as Nf3 or UCI such as g1f3. "
                    "Other commands: undo, fen, quit."
                )
                continue
            if command == "fen":
                output_function(session.snapshot().fen())
                continue
            if command == "undo":
                try:
                    undone_moves = session.undo_last_turn()
                except SessionError as error:
                    output_function(f"Cannot undo: {error}")
                    continue
                output_function(f"Undid {undone_moves} move(s).")
                _show_board(session.snapshot(), output_function)
                continue

            try:
                played_move = session.apply_player_move(entered_value)
            except SessionError as error:
                output_function(f"Move rejected: {error}")
                continue
            output_function(f"You played {played_move.san} ({played_move.uci}).")
            _show_board(session.snapshot(), output_function)
            continue

        output_function(f"\nStockfish Elo {bot_elo} is thinking...")
        bot_move = engine.choose_move(
            current_board,
            time_limit_seconds=bot_time_seconds,
            strength_elo=bot_elo,
        )
        played_move = session.apply_bot_move(bot_move)
        output_function(f"Stockfish played {played_move.san} ({played_move.uci}).")
        _show_board(session.snapshot(), output_function)


def _show_board(board: chess.Board, output_function: OutputFunction) -> None:
    output_function("")
    output_function(str(board))
    output_function("a b c d e f g h")
    output_function(f"FEN: {board.fen()}")


def _show_game_result(board: chess.Board, output_function: OutputFunction) -> None:
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        output_function("Game ended without a determined result.")
        return
    reason = outcome.termination.name.lower().replace("_", " ")
    output_function(f"\nGame over: {outcome.result()} ({reason}).")
