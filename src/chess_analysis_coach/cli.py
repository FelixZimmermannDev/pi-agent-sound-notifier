"""Command-line entry point for the chess analysis coach."""

import argparse
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
import os
from pathlib import Path
import shutil
import sys

import chess

from chess_analysis_coach import __version__
from chess_analysis_coach.application import PositionAnalyzer, recommend_moves
from chess_analysis_coach.errors import EngineError, PositionError, SessionError
from chess_analysis_coach.live import InputFunction, LocalGameEngine, run_local_game
from chess_analysis_coach.positions import parse_fen
from chess_analysis_coach.presentation import format_recommendation
from chess_analysis_coach.stockfish import (
    MAX_STOCKFISH_ELO,
    MIN_STOCKFISH_ELO,
    StockfishAnalyzer,
)

_DEFAULT_TIME_MS = 250
_DEFAULT_CANDIDATES = 3
_DEFAULT_BOT_ELO = 1500
AnalyzerFactory = Callable[[str], AbstractContextManager[PositionAnalyzer]]


def _positive_integer(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a whole number") from error
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed_value


def _stockfish_elo(value: str) -> int:
    parsed_value = _positive_integer(value)
    if not MIN_STOCKFISH_ELO <= parsed_value <= MAX_STOCKFISH_ELO:
        raise argparse.ArgumentTypeError(
            f"must be between {MIN_STOCKFISH_ELO} and {MAX_STOCKFISH_ELO}"
        )
    return parsed_value


def _add_engine_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--engine",
        metavar="PATH",
        help=(
            "Stockfish executable; otherwise use STOCKFISH_PATH, the system PATH, "
            "or an installed winget package"
        ),
    )


def _add_coach_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--time-ms",
        type=_positive_integer,
        default=_DEFAULT_TIME_MS,
        help=f"coach analysis time per position (default: {_DEFAULT_TIME_MS} ms)",
    )
    parser.add_argument(
        "--candidates",
        type=_positive_integer,
        default=_DEFAULT_CANDIDATES,
        help=f"maximum candidate moves to show (default: {_DEFAULT_CANDIDATES})",
    )
    parser.add_argument(
        "--coach-elo",
        type=_stockfish_elo,
        help=(
            f"optionally limit coach strength from {MIN_STOCKFISH_ELO} to "
            f"{MAX_STOCKFISH_ELO}; default is full strength"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-coach",
        description="Analyze and play permitted local practice games with Stockfish.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command")

    analyze_parser = commands.add_parser("analyze", help="analyze one FEN position")
    analyze_parser.add_argument(
        "fen",
        help="FEN position to analyze (quote it because FEN contains spaces)",
    )
    _add_engine_argument(analyze_parser)
    _add_coach_arguments(analyze_parser)

    play_parser = commands.add_parser(
        "play",
        help="play an interactive local game against limited-strength Stockfish",
    )
    play_parser.add_argument(
        "--player-color",
        choices=("white", "black"),
        default="white",
        help="your color in the local game (default: white)",
    )
    play_parser.add_argument(
        "--bot-elo",
        type=_stockfish_elo,
        default=_DEFAULT_BOT_ELO,
        help=(
            f"local opponent strength from {MIN_STOCKFISH_ELO} to "
            f"{MAX_STOCKFISH_ELO} (default: {_DEFAULT_BOT_ELO})"
        ),
    )
    play_parser.add_argument(
        "--bot-time-ms",
        type=_positive_integer,
        default=_DEFAULT_TIME_MS,
        help=f"opponent thinking time per move (default: {_DEFAULT_TIME_MS} ms)",
    )
    play_parser.add_argument(
        "--fen",
        default=chess.STARTING_FEN,
        help="optional starting FEN; default is the standard starting position",
    )
    _add_engine_argument(play_parser)
    _add_coach_arguments(play_parser)
    return parser


def resolve_engine_path(command_line_path: str | None) -> str:
    explicit_path = command_line_path or os.environ.get("STOCKFISH_PATH")
    if explicit_path:
        return explicit_path

    path_executable = shutil.which("stockfish")
    if path_executable:
        return path_executable

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        candidates = sorted(
            package_root.glob("Stockfish.Stockfish_*/stockfish/stockfish*.exe")
        )
        if candidates:
            return str(candidates[-1])

    return "stockfish"


def main(
    arguments: Sequence[str] | None = None,
    *,
    analyzer_factory: AnalyzerFactory = StockfishAnalyzer,
    input_function: InputFunction = input,
) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    if options.command is None:
        print("Chess Analysis Coach is ready for permitted local live analysis.")
        parser.print_help()
        return 0

    try:
        board = parse_fen(options.fen)
        engine_path = resolve_engine_path(options.engine)
        with analyzer_factory(engine_path) as analyzer:
            if options.command == "analyze":
                recommendation = recommend_moves(
                    board,
                    analyzer,
                    time_limit_seconds=options.time_ms / 1000,
                    candidate_count=options.candidates,
                    strength_elo=options.coach_elo,
                )
                print(format_recommendation(recommendation))
            else:
                live_engine = analyzer
                if not isinstance(live_engine, LocalGameEngine):
                    raise TypeError("The configured engine does not support local play.")
                run_local_game(
                    live_engine,
                    board=board,
                    player_color=(
                        chess.WHITE if options.player_color == "white" else chess.BLACK
                    ),
                    bot_elo=options.bot_elo,
                    coach_elo=options.coach_elo,
                    coach_time_seconds=options.time_ms / 1000,
                    bot_time_seconds=options.bot_time_ms / 1000,
                    candidate_count=options.candidates,
                    input_function=input_function,
                )
    except PositionError as error:
        print(f"Position error: {error}", file=sys.stderr)
        return 2
    except EngineError as error:
        print(f"Engine error: {error}", file=sys.stderr)
        return 3
    except SessionError as error:
        print(f"Session error: {error}", file=sys.stderr)
        return 4

    return 0
