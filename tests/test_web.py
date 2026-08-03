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
                principal_variation_uci=(move.uci(),),
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


def create_test_game(*, coach_elo: int | None = None) -> LocalWebGame:
    return LocalWebGame(
        WebTestEngine(),
        board=chess.Board(),
        settings=WebGameSettings(
            player_color=chess.WHITE,
            bot_elo=1500,
            coach_elo=coach_elo,
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
    assert 'id="future-arrowhead-response"' in page.get_data(as_text=True)
    assert 'id="evaluation-bar"' in page.get_data(as_text=True)
    assert 'data-candidate-count="1"' in page.get_data(as_text=True)
    assert 'data-forecast-side="opponent"' in page.get_data(as_text=True)
    assert 'data-forecast-mode="relevant"' in page.get_data(as_text=True)
    assert 'id="bot-elo-slider"' in page.get_data(as_text=True)
    assert 'id="coach-max-strength"' in page.get_data(as_text=True)
    assert 'id="coach-elo-slider"' in page.get_data(as_text=True)

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
    player_payload = moved.get_json()
    assert moved.status_code == 200
    assert player_payload["moves"][0]["white"] == "e4"
    assert player_payload["moves"][0]["black"] is None
    assert player_payload["moves"][0]["white_quality"] == "Bester Zug"
    assert player_payload["latest_move_quality"]["category"] == "best"
    assert player_payload["running_accuracy"]["white_percent"] == 100
    assert "g1f3" in player_payload["premove_moves"]
    assert not player_payload["is_player_turn"]

    bot_moved = client.post("/api/game/bot-move", json={})
    payload = bot_moved.get_json()
    assert bot_moved.status_code == 200
    assert payload["moves"][0]["black"] == "e5"
    assert payload["is_player_turn"]

    pgn = client.get("/api/game/pgn")
    assert pgn.status_code == 200
    assert pgn.mimetype == "application/x-chess-pgn"
    assert "e4" in pgn.get_data(as_text=True)


def test_local_web_api_accepts_pre_game_recommendation_count() -> None:
    app = create_app(create_test_game())
    app.testing = True
    response = app.test_client().post(
        "/api/game/start",
        json={"candidate_count": 3, "bot_elo": 1800, "coach_elo": 1900},
    )

    assert response.status_code == 200
    assert response.get_json()["candidate_count"] == 3
    assert response.get_json()["bot_elo"] == 1800
    assert response.get_json()["coach_elo"] == 1900


def test_local_web_api_rejects_invalid_recommendation_count_without_starting() -> None:
    app = create_app(create_test_game())
    app.testing = True
    client = app.test_client()

    response = client.post("/api/game/start", json={"candidate_count": 4})

    assert response.status_code == 400
    assert "between 1 and 3" in response.get_json()["error"]
    assert not client.get("/api/game").get_json()["started"]


def test_local_web_api_accepts_explicit_full_strength_coach() -> None:
    app = create_app(create_test_game(coach_elo=1800))
    app.testing = True

    response = app.test_client().post(
        "/api/game/start",
        json={"coach_elo": None},
    )

    assert response.status_code == 200
    assert response.get_json()["coach_elo"] is None


def test_local_web_api_rejects_invalid_bot_elo_without_starting() -> None:
    app = create_app(create_test_game())
    app.testing = True
    client = app.test_client()

    response = client.post("/api/game/start", json={"bot_elo": 1000})

    assert response.status_code == 400
    assert "Bot Elo must be between" in response.get_json()["error"]
    assert not client.get("/api/game").get_json()["started"]


def test_local_web_api_rejects_invalid_coach_elo_without_starting() -> None:
    app = create_app(create_test_game())
    app.testing = True
    client = app.test_client()

    response = client.post("/api/game/start", json={"coach_elo": 1000})

    assert response.status_code == 400
    assert "Coach Elo must be between" in response.get_json()["error"]
    assert not client.get("/api/game").get_json()["started"]


def test_local_web_api_rejects_bot_move_during_player_turn() -> None:
    app = create_app(create_test_game())
    app.testing = True
    client = app.test_client()
    client.post("/api/game/start", json={})

    response = client.post("/api/game/bot-move", json={})

    assert response.status_code == 400
    assert "cannot move on your turn" in response.get_json()["error"]
    assert client.get("/api/game").get_json()["revision"] == 0


def test_local_web_api_returns_actionable_error_for_missing_move() -> None:
    app = create_app(create_test_game())
    app.testing = True
    response = app.test_client().post("/api/game/move", json={})

    assert response.status_code == 400
    assert "move is required" in response.get_json()["error"]
