import chess
import chess.engine
import pytest

from chess_analysis_coach.errors import EngineUnavailableError
from chess_analysis_coach.models import Evaluation
from chess_analysis_coach.stockfish import StockfishAnalyzer


class FakeUciEngine:
    def __init__(self, analysis: list[chess.engine.InfoDict]) -> None:
        self.analysis = analysis
        self.received_fen: str | None = None
        self.received_limit: chess.engine.Limit | None = None
        self.received_multipv: int | None = None
        self.received_analysis_root_moves: list[chess.Move] | None = None
        self.received_play_root_moves: list[chess.Move] | None = None
        self.configurations: list[dict[str, object]] = []
        self.move_to_play: chess.Move | None = None
        self.quit_called = False

    def configure(self, options: dict[str, object]) -> None:
        self.configurations.append(options)

    def analyse(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        *,
        multipv: int,
        root_moves: list[chess.Move] | None = None,
    ) -> list[chess.engine.InfoDict]:
        self.received_fen = board.fen()
        self.received_limit = limit
        self.received_multipv = multipv
        self.received_analysis_root_moves = root_moves
        return self.analysis

    def play(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        *,
        root_moves: list[chess.Move] | None = None,
    ) -> chess.engine.PlayResult:
        self.received_fen = board.fen()
        self.received_limit = limit
        self.received_play_root_moves = root_moves
        return chess.engine.PlayResult(self.move_to_play, None)

    def quit(self) -> None:
        self.quit_called = True


def test_stockfish_adapter_transforms_ranked_uci_analysis_and_closes_engine() -> None:
    board = chess.Board()
    e4 = chess.Move.from_uci("e2e4")
    e5 = chess.Move.from_uci("e7e5")
    d4 = chess.Move.from_uci("d2d4")
    d5 = chess.Move.from_uci("d7d5")
    fake_engine = FakeUciEngine(
        [
            {
                "multipv": 2,
                "score": chess.engine.PovScore(chess.engine.Cp(18), chess.WHITE),
                "pv": [d4, d5],
            },
            {
                "multipv": 1,
                "score": chess.engine.PovScore(chess.engine.Cp(31), chess.WHITE),
                "pv": [e4, e5],
            },
        ]
    )

    with StockfishAnalyzer("stockfish-test", engine_factory=lambda _: fake_engine) as analyzer:
        candidates = analyzer.analyze(
            board,
            time_limit_seconds=0.25,
            candidate_count=3,
        )

    assert [candidate.uci for candidate in candidates] == ["e2e4", "d2d4"]
    assert candidates[0].san == "e4"
    assert candidates[0].evaluation == Evaluation(centipawns=31)
    assert candidates[0].principal_variation_san == ("e4", "e5")
    assert candidates[0].principal_variation_uci == ("e2e4", "e7e5")
    assert fake_engine.received_fen == board.fen()
    assert fake_engine.received_limit == chess.engine.Limit(time=0.25)
    assert fake_engine.received_multipv == 3
    assert fake_engine.configurations == [{"UCI_LimitStrength": False}]
    assert fake_engine.quit_called


def test_limited_coach_analyzes_stockfishs_elo_selected_move() -> None:
    board = chess.Board()
    d4 = chess.Move.from_uci("d2d4")
    d5 = chess.Move.from_uci("d7d5")
    fake_engine = FakeUciEngine(
        [
            {
                "multipv": 1,
                "score": chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE),
                "pv": [d4, d5],
            }
        ]
    )
    fake_engine.move_to_play = d4

    with StockfishAnalyzer("stockfish-test", engine_factory=lambda _: fake_engine) as analyzer:
        candidates = analyzer.analyze(
            board,
            time_limit_seconds=0.1,
            candidate_count=1,
            strength_elo=1400,
        )

    assert [candidate.uci for candidate in candidates] == ["d2d4"]
    assert fake_engine.received_play_root_moves is not None
    assert set(fake_engine.received_play_root_moves) == set(board.legal_moves)
    assert fake_engine.received_analysis_root_moves == [d4]
    assert fake_engine.configurations == [
        {"UCI_LimitStrength": True, "UCI_Elo": 1400}
    ]


def test_stockfish_adapter_chooses_a_move_at_selected_elo_without_mutating_board() -> None:
    board = chess.Board()
    fake_engine = FakeUciEngine([])
    fake_engine.move_to_play = chess.Move.from_uci("e2e4")

    with StockfishAnalyzer("stockfish-test", engine_factory=lambda _: fake_engine) as analyzer:
        move = analyzer.choose_move(
            board,
            time_limit_seconds=0.1,
            strength_elo=1600,
        )

    assert move == chess.Move.from_uci("e2e4")
    assert board == chess.Board()
    assert fake_engine.received_limit == chess.engine.Limit(time=0.1)
    assert fake_engine.configurations == [
        {"UCI_LimitStrength": True, "UCI_Elo": 1600}
    ]
    assert fake_engine.quit_called


def test_stockfish_adapter_reports_an_actionable_startup_error() -> None:
    def unavailable_engine(_: str) -> FakeUciEngine:
        raise FileNotFoundError("missing")

    with pytest.raises(EngineUnavailableError, match="STOCKFISH_PATH"):
        with StockfishAnalyzer("missing-stockfish", engine_factory=unavailable_engine):
            pass
