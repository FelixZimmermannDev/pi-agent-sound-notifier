from types import TracebackType

import chess

from chess_analysis_coach.application import PositionAnalyzer
from chess_analysis_coach.cli import build_parser, main
from chess_analysis_coach.errors import EngineUnavailableError
from chess_analysis_coach.models import CandidateMove, Evaluation

STARTING_FEN = chess.STARTING_FEN


class FakeAnalyzer:
    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        assert board.fen() == STARTING_FEN
        assert time_limit_seconds == 0.1
        assert candidate_count == 1
        assert strength_elo == 1800
        return (
            CandidateMove(
                san="e4",
                uci="e2e4",
                evaluation=Evaluation(centipawns=31),
                principal_variation_san=("e4", "e5"),
            ),
        )

    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move:
        return next(iter(board.legal_moves))


class FakeAnalyzerContext:
    def __enter__(self) -> PositionAnalyzer:
        return FakeAnalyzer()

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False


class UnavailableAnalyzerContext(FakeAnalyzerContext):
    def __enter__(self) -> PositionAnalyzer:
        raise EngineUnavailableError("Stockfish is missing")


def test_cli_accepts_local_web_game_settings() -> None:
    options = build_parser().parse_args(
        [
            "web",
            "--player-color",
            "black",
            "--minutes",
            "5",
            "--increment-seconds",
            "3",
            "--port",
            "9000",
            "--no-browser",
            "--no-coach",
        ]
    )

    assert options.command == "web"
    assert options.player_color == "black"
    assert options.minutes == 5
    assert options.increment_seconds == 3
    assert options.candidates == 1
    assert options.port == 9000
    assert options.no_browser
    assert options.no_coach


def test_cli_without_command_lists_available_workflows(capsys) -> None:
    exit_code = main([])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ready for permitted local live analysis" in output
    assert "analyze" in output
    assert "play" in output


def test_cli_analyzes_a_fen_with_explicit_limits(capsys) -> None:
    received_path: list[str] = []

    def analyzer_factory(path: str) -> FakeAnalyzerContext:
        received_path.append(path)
        return FakeAnalyzerContext()

    exit_code = main(
        [
            "analyze",
            STARTING_FEN,
            "--engine",
            "stockfish-test",
            "--time-ms",
            "100",
            "--candidates",
            "1",
            "--coach-elo",
            "1800",
        ],
        analyzer_factory=analyzer_factory,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert received_path == ["stockfish-test"]
    assert "1. e4 (e2e4)  +0.31" in captured.out


def test_cli_starts_local_play_with_selected_strengths(capsys) -> None:
    exit_code = main(
        [
            "play",
            "--engine",
            "stockfish-test",
            "--bot-elo",
            "1600",
            "--coach-elo",
            "1800",
            "--time-ms",
            "100",
            "--candidates",
            "1",
        ],
        analyzer_factory=lambda _: FakeAnalyzerContext(),
        input_function=lambda _: "quit",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "opponent Elo 1600; coach Elo 1800" in captured.out
    assert "Live recommendation for the current position" in captured.out
    assert "Local game ended by the player" in captured.out


def test_cli_rejects_invalid_fen_without_starting_engine(capsys) -> None:
    engine_started = False

    def analyzer_factory(_: str) -> FakeAnalyzerContext:
        nonlocal engine_started
        engine_started = True
        return FakeAnalyzerContext()

    exit_code = main(
        ["analyze", "not-a-fen"],
        analyzer_factory=analyzer_factory,
    )

    assert exit_code == 2
    assert "Position error: Invalid FEN" in capsys.readouterr().err
    assert not engine_started


def test_cli_reports_engine_startup_failure(capsys) -> None:
    exit_code = main(
        ["analyze", STARTING_FEN],
        analyzer_factory=lambda _: UnavailableAnalyzerContext(),
    )

    assert exit_code == 3
    assert "Engine error: Stockfish is missing" in capsys.readouterr().err
