import chess

from chess_analysis_coach.live import run_local_game
from chess_analysis_coach.models import CandidateMove, Evaluation


class RecordingLiveEngine:
    def __init__(self) -> None:
        self.analysis_calls: list[tuple[str, float, int, int | None]] = []
        self.bot_calls: list[tuple[str, float, int]] = []

    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        self.analysis_calls.append(
            (board.fen(), time_limit_seconds, candidate_count, strength_elo)
        )
        move = next(iter(board.legal_moves))
        return (
            CandidateMove(
                san=board.san(move),
                uci=move.uci(),
                evaluation=Evaluation(centipawns=20),
                principal_variation_san=(board.san(move),),
            ),
        )

    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move:
        self.bot_calls.append((board.fen(), time_limit_seconds, strength_elo))
        return chess.Move.from_uci("e7e5")


def test_local_game_recommends_after_each_move_and_uses_selected_bot_elo() -> None:
    engine = RecordingLiveEngine()
    entered_values = iter(["e4", "quit"])
    output: list[str] = []

    run_local_game(
        engine,
        board=chess.Board(),
        player_color=chess.WHITE,
        bot_elo=1600,
        coach_elo=None,
        coach_time_seconds=0.1,
        bot_time_seconds=0.2,
        candidate_count=1,
        input_function=lambda _: next(entered_values),
        output_function=output.append,
    )

    assert len(engine.analysis_calls) == 3
    assert [call[3] for call in engine.analysis_calls] == [None, None, None]
    assert engine.bot_calls[0][1:] == (0.2, 1600)
    assert any("You played e4 (e2e4)" in line for line in output)
    assert any("Stockfish played e5 (e7e5)" in line for line in output)
    assert output.count("\nLive recommendation for the current position:") == 3
    assert output[-1] == "Local game ended by the player."


def test_local_game_reports_an_already_finished_position_without_analysis() -> None:
    engine = RecordingLiveEngine()
    output: list[str] = []

    run_local_game(
        engine,
        board=chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"),
        player_color=chess.WHITE,
        bot_elo=1500,
        coach_elo=1800,
        coach_time_seconds=0.1,
        bot_time_seconds=0.1,
        candidate_count=1,
        input_function=lambda _: "quit",
        output_function=output.append,
    )

    assert engine.analysis_calls == []
    assert engine.bot_calls == []
    assert output[-1] == "\nGame over: 1-0 (checkmate)."
