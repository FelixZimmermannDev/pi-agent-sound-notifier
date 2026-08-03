"""Stockfish UCI process adapter."""

from collections.abc import Callable
from types import TracebackType
from typing import Any, Protocol, Self

import chess
import chess.engine

from chess_analysis_coach.errors import EngineAnalysisError, EngineUnavailableError
from chess_analysis_coach.models import CandidateMove, Evaluation

_MAX_VARIATION_PLIES = 6
MIN_STOCKFISH_ELO = 1320
MAX_STOCKFISH_ELO = 3190


class _UciEngine(Protocol):
    def configure(self, options: dict[str, object]) -> None: ...

    def analyse(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        *,
        multipv: int,
        root_moves: list[chess.Move] | None = None,
    ) -> chess.engine.InfoDict | list[chess.engine.InfoDict]: ...

    def play(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        *,
        root_moves: list[chess.Move] | None = None,
    ) -> chess.engine.PlayResult: ...

    def quit(self) -> None: ...


EngineFactory = Callable[[str], _UciEngine]


class StockfishAnalyzer:
    """Own one Stockfish process and transform UCI output into domain values."""

    def __init__(
        self,
        executable_path: str,
        *,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self._executable_path = executable_path
        self._engine_factory = engine_factory or chess.engine.SimpleEngine.popen_uci
        self._engine: _UciEngine | None = None

    def __enter__(self) -> Self:
        try:
            self._engine = self._engine_factory(self._executable_path)
        except (OSError, TimeoutError, chess.engine.EngineError) as error:
            raise EngineUnavailableError(
                f"Could not start Stockfish at '{self._executable_path}'. "
                "Install Stockfish and pass --engine PATH or set STOCKFISH_PATH."
            ) from error
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        engine = self._engine
        self._engine = None
        if engine is not None:
            try:
                engine.quit()
            except (OSError, TimeoutError, chess.engine.EngineError) as error:
                if exception_type is None:
                    raise EngineAnalysisError(
                        "Stockfish analysis finished, but the engine did not shut down cleanly."
                    ) from error
        return False

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        engine = self._require_running_engine()
        multipv = min(candidate_count, board.legal_moves.count())
        try:
            self._configure_strength(engine, strength_elo)
            limited_root_moves = (
                self._choose_limited_root_moves(
                    engine,
                    board,
                    time_limit_seconds=time_limit_seconds,
                    candidate_count=multipv,
                )
                if strength_elo is not None
                else None
            )
            raw_analysis = engine.analyse(
                board,
                chess.engine.Limit(time=time_limit_seconds),
                multipv=multipv,
                root_moves=limited_root_moves,
            )
        except (OSError, TimeoutError, chess.engine.EngineError) as error:
            raise EngineAnalysisError(f"Stockfish analysis failed: {error}") from error

        analysis_lines = raw_analysis if isinstance(raw_analysis, list) else [raw_analysis]
        if limited_root_moves is None:
            analysis_lines.sort(key=lambda info: int(info.get("multipv", 1)))
        else:
            analysis_lines = _order_lines_by_selected_moves(
                analysis_lines,
                limited_root_moves,
            )
        return tuple(
            _candidate_from_info(board, info, line_number=index)
            for index, info in enumerate(analysis_lines, start=1)
        )

    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move:
        """Choose one legal opponent move at Stockfish's limited UCI Elo."""
        engine = self._require_running_engine()
        try:
            self._configure_strength(engine, strength_elo)
            play_result = engine.play(
                board.copy(stack=True),
                chess.engine.Limit(time=time_limit_seconds),
            )
        except (OSError, TimeoutError, chess.engine.EngineError) as error:
            raise EngineAnalysisError(f"Stockfish could not choose a move: {error}") from error

        if play_result.move is None or play_result.move not in board.legal_moves:
            raise EngineAnalysisError("Stockfish did not return a legal opponent move.")
        return play_result.move

    @staticmethod
    def _choose_limited_root_moves(
        engine: _UciEngine,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
    ) -> list[chess.Move]:
        """Ask Stockfish's Elo limiter to select each displayed root move."""
        remaining_moves = list(board.legal_moves)
        selected_moves: list[chess.Move] = []
        limit = chess.engine.Limit(time=time_limit_seconds)
        for _ in range(candidate_count):
            play_result = engine.play(
                board.copy(stack=True),
                limit,
                root_moves=remaining_moves.copy(),
            )
            move = play_result.move
            if move is None or move not in remaining_moves:
                raise EngineAnalysisError(
                    "Stockfish did not return a legal limited-strength candidate."
                )
            selected_moves.append(move)
            remaining_moves.remove(move)
        return selected_moves

    def _require_running_engine(self) -> _UciEngine:
        if self._engine is None:
            raise EngineAnalysisError("Stockfish must be started before requesting analysis.")
        return self._engine

    @staticmethod
    def _configure_strength(engine: _UciEngine, strength_elo: int | None) -> None:
        if strength_elo is None:
            engine.configure({"UCI_LimitStrength": False})
            return
        if not MIN_STOCKFISH_ELO <= strength_elo <= MAX_STOCKFISH_ELO:
            raise ValueError(
                f"Stockfish Elo must be between {MIN_STOCKFISH_ELO} and {MAX_STOCKFISH_ELO}."
            )
        engine.configure(
            {
                "UCI_LimitStrength": True,
                "UCI_Elo": strength_elo,
            }
        )


def _order_lines_by_selected_moves(
    analysis_lines: list[chess.engine.InfoDict],
    selected_moves: list[chess.Move],
) -> list[chess.engine.InfoDict]:
    lines_by_root = {
        variation[0]: info
        for info in analysis_lines
        if (variation := info.get("pv"))
    }
    try:
        return [lines_by_root[move] for move in selected_moves]
    except KeyError as error:
        raise EngineAnalysisError(
            "Stockfish did not analyze every limited-strength candidate."
        ) from error


def _candidate_from_info(
    board: chess.Board,
    info: dict[str, Any],
    *,
    line_number: int,
) -> CandidateMove:
    variation = info.get("pv")
    score = info.get("score")
    if not variation or score is None:
        raise EngineAnalysisError(
            f"Stockfish returned incomplete data for candidate {line_number}."
        )

    root_move = variation[0]
    if root_move not in board.legal_moves:
        raise EngineAnalysisError(
            f"Stockfish returned an illegal move for candidate {line_number}."
        )

    try:
        point_of_view_score = score.pov(board.turn)
        mate_in = point_of_view_score.mate()
        centipawns = point_of_view_score.score()
    except AttributeError as error:
        raise EngineAnalysisError(
            f"Stockfish returned an invalid score for candidate {line_number}."
        ) from error

    if mate_in is not None:
        evaluation = Evaluation(mate_in=mate_in)
    elif centipawns is not None:
        evaluation = Evaluation(centipawns=centipawns)
    else:
        raise EngineAnalysisError(
            f"Stockfish returned no usable score for candidate {line_number}."
        )

    return CandidateMove(
        san=board.san(root_move),
        uci=root_move.uci(),
        evaluation=evaluation,
        principal_variation_san=_variation_to_san(board, variation, line_number=line_number),
        principal_variation_uci=tuple(
            move.uci() for move in variation[:_MAX_VARIATION_PLIES]
        ),
    )


def _variation_to_san(
    board: chess.Board,
    variation: list[chess.Move],
    *,
    line_number: int,
) -> tuple[str, ...]:
    variation_board = board.copy(stack=False)
    san_moves: list[str] = []
    for move in variation[:_MAX_VARIATION_PLIES]:
        if move not in variation_board.legal_moves:
            raise EngineAnalysisError(
                f"Stockfish returned an illegal variation for candidate {line_number}."
            )
        san_moves.append(variation_board.san(move))
        variation_board.push(move)
    return tuple(san_moves)
