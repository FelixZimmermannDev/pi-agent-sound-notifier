import chess

from chess_analysis_coach.models import CandidateMove, Evaluation
from chess_analysis_coach.web import create_app
from chess_analysis_coach.web_game import LocalWebGame, WebGameSettings


class WebTestEngine:
    def analyze(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        candidate_count: int,
        strength_elo: int | None = None,
    ) -> tuple[CandidateMove, ...]:
        move = chess.Move.from_uci("e2e4")
        if move not in board.legal_moves:
            move = next(iter(board.legal_moves))
        san = board.san(move)
        return (
            CandidateMove(
                san=san,
                uci=move.uci(),
                evaluation=Evaluation(centipawns=30),
                principal_variation_san=(san,),
            ),
        )

    def choose_move(
        self,
        board: chess.Board,
        *,
        time_limit_seconds: float,
        strength_elo: int,
    ) -> chess.Move:
        move = chess.Move.from_uci("e7e5")
        return move if move in board.legal_moves else next(iter(board.legal_moves))


def create_test_game() -> LocalWebGame:
    return LocalWebGame(
        WebTestEngine(),
        board=chess.Board(),
        settings=WebGameSettings(
            player_color=chess.WHITE,
            bot_elo=1500,
            coach_elo=None,
            coach_time_seconds=0.05,
            bot_time_seconds=0.05,
            candidate_count=1,
            initial_seconds=300,
        ),
    )


def test_local_web_api_serves_page_and_one_complete_turn() -> None:
    app = create_app(create_test_game())
    app.testing = True
    client = app.test_client()

    page = client.get("/")
    assert page.status_code == 200
    assert "Chess Analysis Coach" in page.get_data(as_text=True)
    assert 'id="candidate-arrows"' in page.get_data(as_text=True)
    assert 'id="evaluation-bar"' in page.get_data(as_text=True)

    stylesheet = client.get("/static/app.css")
    assert stylesheet.status_code == 200
    assert "grid-template-rows: repeat(8, minmax(0, 1fr))" in stylesheet.get_data(
        as_text=True
    )

    white_king = client.get("/pieces/K.svg")
    assert white_king.status_code == 200
    assert white_king.mimetype == "image/svg+xml"
    assert "<svg" in white_king.get_data(as_text=True)

    started = client.post("/api/game/start", json={})
    assert started.status_code == 200
    assert started.get_json()["recommendation"][0]["uci"] == "e2e4"
    assert started.get_json()["evaluation_bar"]["white_percent"] > 50

    moved = client.post("/api/game/move", json={"move": "e2e4"})
    payload = moved.get_json()
    assert moved.status_code == 200
    assert payload["moves"] == [{"black": "e5", "number": 1, "white": "e4"}]
    assert payload["is_player_turn"]

    pgn = client.get("/api/game/pgn")
    assert pgn.status_code == 200
    assert pgn.mimetype == "application/x-chess-pgn"
    assert "e4" in pgn.get_data(as_text=True)


def test_local_web_api_returns_actionable_error_for_missing_move() -> None:
    app = create_app(create_test_game())
    app.testing = True
    response = app.test_client().post("/api/game/move", json={})

    assert response.status_code == 400
    assert "move is required" in response.get_json()["error"]
