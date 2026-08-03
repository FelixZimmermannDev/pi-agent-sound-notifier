from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import pytest

from chess_analysis_coach.errors import InvalidMoveError
from chess_analysis_coach.models import CandidateMove, Evaluation
from chess_analysis_coach.web_game import LocalWebGame, WebGameSettings


class DeterministicWebEngine:
    def __init__(self) -> None:
        self.analysis_calls: list[str] = []
        self.bot_calls: list[str] = []

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        self.analysis_calls.append(board.fen())
        preferred_moves = ("e2e4", "g1f3", "e7e5", "g8f6")
        moves: list[chess.Move] = []
        for uci in preferred_moves:
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves and move not in moves:
                moves.append(move)
        for move in board.legal_moves:
            if move not in moves:
                moves.append(move)
            if len(moves) >= candidate_count:
                break

        candidates: list[CandidateMove] = []
        for rank, move in enumerate(moves[:candidate_count], start=1):
            san = board.san(move)
            candidates.append(
                CandidateMove(
                    san=san,
                    uci=move.uci(),
                    evaluation=Evaluation(centipawns=30 - rank * 5),
                    principal_variation_san=(san,),
                    principal_variation_uci=(move.uci(),),
                )
            )
        return tuple(candidates)

    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move:
        self.bot_calls.append(board.fen())
        for uci in ("e7e5", "e2e4"):
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                return move
        return next(iter(board.legal_moves))


def settings(*, player_color: chess.Color = chess.WHITE) -> WebGameSettings:
    return WebGameSettings(
        player_color=player_color,
        bot_elo=1500,
        coach_elo=None,
        coach_time_seconds=0.05,
        bot_time_seconds=0.05,
        candidate_count=2,
        initial_seconds=600,
    )


def test_web_game_tracks_manual_player_move_bot_reply_and_live_advice(
    tmp_path: Path,
) -> None:
    engine = DeterministicWebEngine()
    game = LocalWebGame(
        engine,
        board=chess.Board(),
        settings=settings(),
        recording_directory=tmp_path,
    )

    ready = game.state()
    assert not ready.started
    assert ready.legal_moves == ()

    started = game.start()
    assert started.is_player_turn
    assert started.recommendation[0].uci == "e2e4"
    assert [candidate.uci for candidate in started.recommendation] == ["e2e4", "g1f3"]
    assert started.recommendation[0].variation_uci == ("e2e4",)
    assert started.recommendation[0].plan.startswith("Ziel:")
    assert started.evaluation_bar is not None
    assert started.evaluation_bar.white_percent > 50

    after_player_move = game.play_player_move("e2e4")
    assert not after_player_move.is_player_turn
    assert after_player_move.moves[0].white == "e4"
    assert after_player_move.moves[0].black is None
    assert "g1f3" in after_player_move.premove_moves

    after_turn = game.play_bot_turn()

    board = chess.Board(after_turn.fen)
    assert board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.piece_at(chess.E5) == chess.Piece(chess.PAWN, chess.BLACK)
    assert after_turn.moves[0].white == "e4"
    assert after_turn.moves[0].black == "e5"
    assert after_turn.recommendation[0].uci == "g1f3"
    assert after_turn.moves[0].white_quality == "Bester Zug"
    assert after_turn.moves[0].black_quality == "Bester Zug"
    assert after_turn.latest_move_quality is not None
    assert after_turn.latest_move_quality.color == "white"
    assert after_turn.latest_move_quality.category == "best"
    assert after_turn.running_accuracy.white_percent == 100
    assert after_turn.running_accuracy.black_percent == 100
    assert len(engine.bot_calls) == 1
    assert len(engine.analysis_calls) == 3

    recording_path = tmp_path / after_turn.recording_filename
    assert recording_path.is_file()
    recorded_game = chess.pgn.read_game(StringIO(recording_path.read_text(encoding="utf-8")))
    assert recorded_game is not None
    assert [move.uci() for move in recorded_game.mainline_moves()] == ["e2e4", "e7e5"]
    assert recorded_game.headers["White"] == "Player"
    assert "Live coach: e4" in recorded_game.next().comment
    assert "Provisional live quality: Bester Zug" in recorded_game.next().comment


def test_web_game_classifies_a_non_candidate_player_move_provisionally() -> None:
    engine = DeterministicWebEngine()
    game = LocalWebGame(engine, board=chess.Board(), settings=settings())
    game.start()

    state = game.play_player_move("a3")

    assert not state.is_player_turn
    assert state.latest_move_quality is not None
    assert state.latest_move_quality.san == "a3"
    assert state.latest_move_quality.category == "inaccuracy"
    assert state.latest_move_quality.best_move_san == "e4"
    assert state.latest_move_quality.loss_percentage_points > 0
    assert state.running_accuracy.white_percent is not None
    assert state.running_accuracy.white_percent < 100


def test_web_game_rejects_illegal_player_move_without_bot_reply() -> None:
    engine = DeterministicWebEngine()
    game = LocalWebGame(engine, board=chess.Board(), settings=settings())
    game.start()
    original_fen = game.state().fen

    with pytest.raises(InvalidMoveError):
        game.play_player_move("e2e5")

    state = game.state()
    assert state.fen == original_fen
    assert state.revision == 0
    assert engine.bot_calls == []


def test_web_game_reports_an_already_finished_position_without_engine_work() -> None:
    engine = DeterministicWebEngine()
    game = LocalWebGame(
        engine,
        board=chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"),
        settings=settings(),
    )

    state = game.start()

    assert state.game_over
    assert state.result == "1-0"
    assert state.termination == "checkmate"
    assert state.clocks.active_color is None
    assert engine.analysis_calls == []
    assert engine.bot_calls == []


def test_web_game_plays_the_opening_bot_move_when_player_is_black() -> None:
    engine = DeterministicWebEngine()
    game = LocalWebGame(
        engine,
        board=chess.Board(),
        settings=settings(player_color=chess.BLACK),
    )

    waiting_for_bot = game.start()

    assert waiting_for_bot.player_color == "black"
    assert not waiting_for_bot.is_player_turn
    assert waiting_for_bot.premove_moves
    assert waiting_for_bot.moves == ()

    state = game.play_bot_turn()

    assert state.is_player_turn
    assert state.evaluation_bar is not None
    assert state.evaluation_bar.white_percent < 50
    assert state.moves[0].white == "e4"
    assert len(engine.bot_calls) == 1
    assert state.recommendation
