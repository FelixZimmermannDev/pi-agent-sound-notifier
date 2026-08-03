"""Application state for one local browser game."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import chess

from chess_analysis_coach.application import PositionAnalyzer, recommend_moves
from chess_analysis_coach.coaching import explain_candidate
from chess_analysis_coach.errors import InvalidMoveError, SessionStateError
from chess_analysis_coach.evaluation import (
    EvaluationSummary,
    summarize_evaluation,
    terminal_evaluation,
)
from chess_analysis_coach.game_clock import ChessClock
from chess_analysis_coach.models import Recommendation
from chess_analysis_coach.move_quality import MoveQuality, assess_move
from chess_analysis_coach.presentation import format_evaluation
from chess_analysis_coach.recording import (
    RecordedMove,
    build_pgn,
    create_recording_path,
    save_pgn,
)
from chess_analysis_coach.session import LocalGameSession


class WebGameEngine(PositionAnalyzer, Protocol):
    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move: ...


@dataclass(frozen=True)
class WebGameSettings:
    player_color: chess.Color
    bot_elo: int
    coach_elo: int | None
    coach_time_seconds: float
    bot_time_seconds: float
    candidate_count: int
    initial_seconds: float
    increment_seconds: float = 0

    def __post_init__(self) -> None:
        if self.coach_time_seconds <= 0 or self.bot_time_seconds <= 0:
            raise ValueError("Engine time limits must be greater than zero.")
        if self.candidate_count <= 0:
            raise ValueError("Candidate count must be greater than zero.")
        if self.initial_seconds <= 0:
            raise ValueError("Initial clock time must be greater than zero.")
        if self.increment_seconds < 0:
            raise ValueError("Clock increment cannot be negative.")


@dataclass(frozen=True)
class CandidateView:
    rank: int
    san: str
    uci: str
    evaluation: str
    variation: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class AssessedMoveView:
    color: str
    san: str
    uci: str
    category: str
    label: str
    accuracy_percent: float
    loss_percentage_points: float
    best_move_san: str
    best_move_uci: str


@dataclass(frozen=True)
class RunningAccuracyView:
    white_percent: float | None
    black_percent: float | None
    provisional: bool = True


@dataclass(frozen=True)
class MoveRow:
    number: int
    white: str | None
    black: str | None
    white_quality: str | None
    black_quality: str | None


@dataclass(frozen=True)
class ClockView:
    white_seconds: float
    black_seconds: float
    active_color: str | None


@dataclass(frozen=True)
class WebGameView:
    fen: str
    player_color: str
    turn: str
    started: bool
    game_over: bool
    is_player_turn: bool
    result: str | None
    termination: str | None
    revision: int
    legal_moves: tuple[str, ...]
    premove_moves: tuple[str, ...]
    clocks: ClockView
    evaluation_bar: EvaluationSummary | None
    recommendation: tuple[CandidateView, ...]
    latest_move_quality: AssessedMoveView | None
    running_accuracy: RunningAccuracyView
    moves: tuple[MoveRow, ...]
    recording_filename: str


class LocalWebGame:
    """Coordinate a clocked local game, live coaching, and PGN snapshots."""

    def __init__(
        self,
        engine: WebGameEngine,
        *,
        board: chess.Board,
        settings: WebGameSettings,
        recording_directory: Path | None = None,
    ) -> None:
        self._engine = engine
        self._starting_board = board.copy(stack=True)
        self._settings = settings
        self._recording_directory = recording_directory
        self._initialize_game()

    def _initialize_game(self) -> None:
        self._session = LocalGameSession(
            self._starting_board,
            player_color=self._settings.player_color,
        )
        self._clock = ChessClock(
            initial_seconds=self._settings.initial_seconds,
            increment_seconds=self._settings.increment_seconds,
        )
        self._started = False
        self._timeout_color: chess.Color | None = None
        self._recommendation: Recommendation | None = None
        self._pending_bot_recommendation: Recommendation | None = None
        self._moves: list[RecordedMove] = []
        self._move_assessments: list[AssessedMoveView | None] = []
        self._recording_path = (
            create_recording_path(self._recording_directory)
            if self._recording_directory is not None
            else None
        )

    def start(self) -> WebGameView:
        if self._started:
            raise SessionStateError("The local game has already started.")

        self._started = True
        if self._session.is_game_over:
            self._persist()
            return self.state()

        if self._session.is_player_turn:
            self._recommendation = self._analyze_current_position()
            self._clock.start(self._settings.player_color)
        else:
            self._pending_bot_recommendation = self._analyze_current_position()
            self._clock.start(self._session.snapshot().turn)
        self._persist()
        return self.state()

    def play_player_move(self, notation: str) -> WebGameView:
        self._ensure_active_game()
        move = self._session.parse_player_move(notation)
        if self._sync_timeout():
            raise SessionStateError("Your clock reached zero before the move was played.")

        board_before = self._session.snapshot()
        recommendation_before = self._recommendation
        if not self._clock.finish_move(
            self._settings.player_color,
            next_color=None,
        ):
            self._set_timeout(self._settings.player_color)
            raise SessionStateError("Your clock reached zero before the move was played.")

        coach_comment = self._coach_comment()
        played_move = self._session.apply_player_move(move.uci())
        self._recommendation = None

        if self._session.is_game_over:
            board_after = self._session.snapshot()
            assessment = self._assess_played_move(
                recommendation_before=recommendation_before,
                board_before=board_before,
                recommendation_after=None,
                board_after=board_after,
                played_san=played_move.san,
                played_uci=played_move.uci,
            )
            self._record_move(
                played_move.uci,
                self._settings.player_color,
                coach_comment,
                assessment,
            )
            self._persist()
            return self.state()

        board_after = self._session.snapshot()
        bot_recommendation = self._analyze_current_position()
        assessment = self._assess_played_move(
            recommendation_before=recommendation_before,
            board_before=board_before,
            recommendation_after=bot_recommendation,
            board_after=board_after,
            played_san=played_move.san,
            played_uci=played_move.uci,
        )
        self._record_move(
            played_move.uci,
            self._settings.player_color,
            coach_comment,
            assessment,
        )

        self._pending_bot_recommendation = bot_recommendation
        self._clock.start(board_after.turn)
        self._persist()
        return self.state()

    def play_bot_turn(self) -> WebGameView:
        if not self._started:
            raise SessionStateError("Start the local game before requesting a bot move.")
        self._sync_timeout()
        if self._is_game_over():
            raise SessionStateError("The local game is already over.")
        if self._session.is_player_turn:
            raise SessionStateError("The local Stockfish opponent cannot move on your turn.")

        self._play_bot_turn(self._pending_bot_recommendation)
        self._pending_bot_recommendation = None
        self._persist()
        return self.state()

    def reset(self) -> WebGameView:
        self._initialize_game()
        return self.state()

    def state(self) -> WebGameView:
        self._sync_timeout()
        board = self._session.snapshot()
        game_over = self._is_game_over()
        clock = self._clock.snapshot()
        legal_moves = (
            tuple(move.uci() for move in board.legal_moves)
            if self._started and not game_over and self._session.is_player_turn
            else ()
        )
        premove_moves = (
            self._possible_premoves(board)
            if self._started and not game_over and not self._session.is_player_turn
            else ()
        )
        recommendation = (
            self._candidate_views(board)
            if self._started and not game_over and self._session.is_player_turn
            else ()
        )
        result, termination = self._result_and_termination()

        return WebGameView(
            fen=board.fen(),
            player_color=_color_name(self._settings.player_color),
            turn=_color_name(board.turn),
            started=self._started,
            game_over=game_over,
            is_player_turn=(
                self._started and not game_over and self._session.is_player_turn
            ),
            result=result,
            termination=termination,
            revision=self._session.revision,
            legal_moves=legal_moves,
            premove_moves=premove_moves,
            clocks=ClockView(
                white_seconds=clock.white_seconds,
                black_seconds=clock.black_seconds,
                active_color=(
                    _color_name(clock.active_color)
                    if clock.active_color is not None
                    else None
                ),
            ),
            evaluation_bar=self._evaluation_summary(board),
            recommendation=recommendation,
            latest_move_quality=self._latest_move_quality(),
            running_accuracy=self._running_accuracy(),
            moves=self._move_rows(),
            recording_filename=(
                self._recording_path.name
                if self._recording_path is not None
                else "local-game.pgn"
            ),
        )

    def pgn(self) -> str:
        result, termination = self._result_and_termination()
        return build_pgn(
            starting_board=self._starting_board,
            moves=tuple(self._moves),
            player_color=self._settings.player_color,
            bot_elo=self._settings.bot_elo,
            result=result or "*",
            termination=termination,
        )

    def _play_bot_turn(
        self,
        recommendation_before: Recommendation | None,
    ) -> None:
        if self._is_game_over() or self._session.is_player_turn:
            return

        board_before = self._session.snapshot()
        bot_move = self._engine.choose_move(
            board_before,
            time_limit_seconds=self._settings.bot_time_seconds,
            strength_elo=self._settings.bot_elo,
        )
        if bot_move not in board_before.legal_moves:
            raise InvalidMoveError(
                f"The engine selected an illegal move: {bot_move.uci()}."
            )
        if self._sync_timeout():
            return

        bot_color = not self._settings.player_color
        if not self._clock.finish_move(bot_color, next_color=None):
            self._set_timeout(bot_color)
            return

        played_move = self._session.apply_bot_move(bot_move)
        if self._session.is_game_over:
            board_after = self._session.snapshot()
            assessment = self._assess_played_move(
                recommendation_before=recommendation_before,
                board_before=board_before,
                recommendation_after=None,
                board_after=board_after,
                played_san=played_move.san,
                played_uci=played_move.uci,
            )
            self._record_move(played_move.uci, bot_color, assessment=assessment)
            self._persist()
            return

        board_after = self._session.snapshot()
        player_recommendation = self._analyze_current_position()
        assessment = self._assess_played_move(
            recommendation_before=recommendation_before,
            board_before=board_before,
            recommendation_after=player_recommendation,
            board_after=board_after,
            played_san=played_move.san,
            played_uci=played_move.uci,
        )
        self._record_move(played_move.uci, bot_color, assessment=assessment)
        self._recommendation = player_recommendation
        self._clock.start(board_after.turn)

    def _analyze_current_position(self) -> Recommendation:
        return recommend_moves(
            self._session.snapshot(),
            self._engine,
            time_limit_seconds=self._settings.coach_time_seconds,
            candidate_count=self._settings.candidate_count,
            strength_elo=self._settings.coach_elo,
        )

    def _possible_premoves(self, board: chess.Board) -> tuple[str, ...]:
        premove_board = board.copy(stack=False)
        premove_board.turn = self._settings.player_color
        premove_board.ep_square = None
        return tuple(move.uci() for move in premove_board.legal_moves)

    def _evaluation_summary(
        self,
        board: chess.Board,
    ) -> EvaluationSummary | None:
        if self._timeout_color is not None:
            return terminal_evaluation(not self._timeout_color)
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            return terminal_evaluation(outcome.winner)
        recommendation = self._recommendation or self._pending_bot_recommendation
        if recommendation is None or not recommendation.candidates:
            return None
        return summarize_evaluation(
            recommendation.candidates[0].evaluation,
            side_to_move=board.turn,
        )

    def _candidate_views(self, board: chess.Board) -> tuple[CandidateView, ...]:
        if self._recommendation is None:
            return ()
        return tuple(
            CandidateView(
                rank=rank,
                san=candidate.san,
                uci=candidate.uci,
                evaluation=format_evaluation(candidate.evaluation),
                variation=candidate.principal_variation_san,
                explanation=explain_candidate(board, candidate),
            )
            for rank, candidate in enumerate(self._recommendation.candidates, start=1)
        )

    def _assess_played_move(
        self,
        *,
        recommendation_before: Recommendation | None,
        board_before: chess.Board,
        recommendation_after: Recommendation | None,
        board_after: chess.Board,
        played_san: str,
        played_uci: str,
    ) -> AssessedMoveView | None:
        if recommendation_before is None or not recommendation_before.candidates:
            return None

        if recommendation_after is not None and recommendation_after.candidates:
            after_summary = summarize_evaluation(
                recommendation_after.candidates[0].evaluation,
                side_to_move=board_after.turn,
            )
        else:
            outcome = board_after.outcome(claim_draw=True)
            if outcome is None:
                return None
            after_summary = terminal_evaluation(outcome.winner)

        best = recommendation_before.candidates[0]
        quality: MoveQuality = assess_move(
            before=summarize_evaluation(
                best.evaluation,
                side_to_move=board_before.turn,
            ),
            after=after_summary,
            moving_color=board_before.turn,
            played_move_uci=played_uci,
            best_move_san=best.san,
            best_move_uci=best.uci,
        )
        return AssessedMoveView(
            color=_color_name(board_before.turn),
            san=played_san,
            uci=played_uci,
            category=quality.category,
            label=quality.label,
            accuracy_percent=quality.accuracy_percent,
            loss_percentage_points=quality.loss_percentage_points,
            best_move_san=quality.best_move_san,
            best_move_uci=quality.best_move_uci,
        )

    def _coach_comment(self) -> str | None:
        if self._recommendation is None or not self._recommendation.candidates:
            return None
        best = self._recommendation.candidates[0]
        return (
            f"Live coach: {best.san} ({best.uci}), "
            f"evaluation {format_evaluation(best.evaluation)}."
        )

    def _record_move(
        self,
        uci: str,
        color: chess.Color,
        coach_comment: str | None = None,
        assessment: AssessedMoveView | None = None,
    ) -> None:
        clock = self._clock.snapshot()
        remaining = clock.white_seconds if color == chess.WHITE else clock.black_seconds
        comments = [coach_comment] if coach_comment else []
        if assessment is not None:
            comments.append(
                f"Provisional live quality: {assessment.label}; "
                f"accuracy {assessment.accuracy_percent:.1f}; "
                f"evaluation-share loss {assessment.loss_percentage_points:.1f} points."
            )
        self._moves.append(
            RecordedMove(
                move=chess.Move.from_uci(uci),
                remaining_seconds=remaining,
                coach_comment=" ".join(comments) or None,
            )
        )
        self._move_assessments.append(assessment)

    def _latest_move_quality(self) -> AssessedMoveView | None:
        return next(
            (
                assessment
                for assessment in reversed(self._move_assessments)
                if (
                    assessment is not None
                    and assessment.color == _color_name(self._settings.player_color)
                )
            ),
            None,
        )

    def _running_accuracy(self) -> RunningAccuracyView:
        def average_for(color: str) -> float | None:
            values = [
                assessment.accuracy_percent
                for assessment in self._move_assessments
                if assessment is not None and assessment.color == color
            ]
            return sum(values) / len(values) if values else None

        return RunningAccuracyView(
            white_percent=average_for("white"),
            black_percent=average_for("black"),
        )

    def _move_rows(self) -> tuple[MoveRow, ...]:
        board = self._starting_board.copy(stack=False)
        rows: list[MoveRow] = []
        pending_white: str | None = None
        pending_white_quality: str | None = None
        move_number = board.fullmove_number

        for index, recorded_move in enumerate(self._moves):
            san = board.san(recorded_move.move)
            assessment = self._move_assessments[index]
            quality_label = assessment.label if assessment is not None else None
            if board.turn == chess.WHITE:
                pending_white = san
                pending_white_quality = quality_label
            else:
                rows.append(
                    MoveRow(
                        move_number,
                        pending_white,
                        san,
                        pending_white_quality,
                        quality_label,
                    )
                )
                pending_white = None
                pending_white_quality = None
                move_number += 1
            board.push(recorded_move.move)

        if pending_white is not None:
            rows.append(
                MoveRow(
                    move_number,
                    pending_white,
                    None,
                    pending_white_quality,
                    None,
                )
            )
        return tuple(rows)

    def _ensure_active_game(self) -> None:
        if not self._started:
            raise SessionStateError("Start the local game before playing a move.")
        self._sync_timeout()
        if self._is_game_over():
            raise SessionStateError("The local game is already over.")
        if not self._session.is_player_turn:
            raise SessionStateError("Wait for the local Stockfish opponent to move.")

    def _sync_timeout(self) -> bool:
        if self._timeout_color is not None or not self._started:
            return self._timeout_color is not None
        expired_color = self._clock.expire_if_needed()
        if expired_color is None:
            return False
        self._set_timeout(expired_color)
        return True

    def _set_timeout(self, color: chess.Color) -> None:
        if self._timeout_color is None:
            self._timeout_color = color
            self._recommendation = None
            self._pending_bot_recommendation = None
            self._persist()

    def _is_game_over(self) -> bool:
        return self._timeout_color is not None or self._session.is_game_over

    def _result_and_termination(self) -> tuple[str | None, str | None]:
        if self._timeout_color is not None:
            result = "0-1" if self._timeout_color == chess.WHITE else "1-0"
            return result, "time forfeit"
        outcome = self._session.snapshot().outcome(claim_draw=True)
        if outcome is None:
            return None, None
        termination = outcome.termination.name.lower().replace("_", " ")
        return outcome.result(), termination

    def _persist(self) -> None:
        if self._recording_path is not None and self._started:
            save_pgn(self._recording_path, self.pgn())


def _color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"
