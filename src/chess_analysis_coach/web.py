"""Localhost-only browser presentation for the chess coach."""

from dataclasses import asdict
from pathlib import Path
from threading import Timer
import webbrowser

import chess
from flask import Flask, Response, jsonify, render_template, request

from chess_analysis_coach.errors import EngineError, SessionError
from chess_analysis_coach.web_game import LocalWebGame, WebGameEngine, WebGameSettings


def create_app(game: LocalWebGame) -> Flask:
    """Create a Flask app around one explicitly owned local game."""
    app = Flask(__name__)
    app.config.update(JSON_SORT_KEYS=False)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/game")
    def game_state() -> Response:
        return jsonify(asdict(game.state()))

    @app.post("/api/game/start")
    def start_game() -> Response:
        return jsonify(asdict(game.start()))

    @app.post("/api/game/move")
    def play_move() -> Response:
        payload = request.get_json(silent=True)
        move = payload.get("move") if isinstance(payload, dict) else None
        if not isinstance(move, str) or not move.strip():
            return jsonify(error="A SAN or UCI move is required."), 400
        return jsonify(asdict(game.play_player_move(move)))

    @app.post("/api/game/reset")
    def reset_game() -> Response:
        return jsonify(asdict(game.reset()))

    @app.get("/api/game/pgn")
    def download_pgn() -> Response:
        state = game.state()
        return Response(
            game.pgn(),
            mimetype="application/x-chess-pgn",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{state.recording_filename}"'
                )
            },
        )

    @app.errorhandler(SessionError)
    def handle_session_error(error: SessionError) -> tuple[Response, int]:
        return jsonify(error=str(error)), 400

    @app.errorhandler(EngineError)
    def handle_engine_error(error: EngineError) -> tuple[Response, int]:
        return jsonify(error=str(error)), 503

    return app


def run_local_web_game(
    engine: WebGameEngine,
    *,
    board: chess.Board,
    settings: WebGameSettings,
    port: int,
    open_browser: bool,
    recording_directory: Path = Path("output/games"),
) -> None:
    """Serve one game on loopback; never expose the prototype publicly."""
    game = LocalWebGame(
        engine,
        board=board,
        settings=settings,
        recording_directory=recording_directory,
    )
    app = create_app(game)
    url = f"http://127.0.0.1:{port}"
    print(f"Local chess coach: {url}")
    print(f"PGN snapshots: {recording_directory.resolve()}")
    print("Press Ctrl+C to stop the local server.")
    if open_browser:
        Timer(0.6, lambda: webbrowser.open(url)).start()
    app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        use_reloader=False,
        threaded=False,
    )
