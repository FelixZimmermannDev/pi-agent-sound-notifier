# Chess Analysis Coach

A local Python application for **live move recommendations during permitted local chess practice** and deeper post-game review. Suitable examples include playing against a local engine, using your own analysis board, or an assisted local training game where every participant has explicitly agreed to engine assistance.

## Current status

Two working terminal workflows are implemented:

```text
FEN → validation → bounded Stockfish MultiPV → ranked recommendations

interactive local game → recommendation for every current position
                       → player SAN/UCI move or Elo-limited Stockfish move
                       → explicit session state until game end or quit
```

Stockfish 18 was discovered from the local winget installation and verified with real bounded analysis and local play. Deterministic tests cover position and move errors, state ownership, analysis coordination, Elo configuration, Stockfish-output transformation, cleanup, presentation, and CLI behavior. A separate opt-in test exercises the real executable.

## Fair-play boundary

Live recommendations are supported only for local solo/computer practice or explicitly agreed assisted training. This project does not inspect active chess websites, read chess-site screens, automate browsers, or secretly assist in competitive games against another person. Completed online games may later be retrieved through documented public endpoints for post-game review.

An online game being “unranked” does not by itself permit engine assistance. A future online integration would require an explicit platform-supported assisted/bot mode and documented interface; it will not be implemented through scraping or hidden automation.

## Setup with PyCharm on Windows

Pi and the project are editor-independent. PyCharm can use the existing project environment directly:

1. Open this repository folder in PyCharm.
2. Open **Settings → Project → Python Interpreter**.
3. Select `.venv\Scripts\python.exe`.
4. Use `pytest` as the test runner.

PyCharm's machine-specific `.idea` configuration is intentionally ignored by Git.

From the PyCharm terminal or PowerShell:

```powershell
cd C:\Users\Felix\Code\Projects\PythonProject\chess-analysis-coach
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m chess_analysis_coach
```

## Stockfish

Stockfish is an external UCI engine and is not bundled with the repository. Install it with:

```powershell
winget install --id Stockfish.Stockfish -e
```

The application discovers Stockfish in this order:

1. `--engine PATH`
2. `STOCKFISH_PATH`
3. a `stockfish` executable on `PATH`
4. the standard local winget package directory

## Analyze one position

```powershell
python -m chess_analysis_coach analyze `
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" `
  --time-ms 250 `
  --candidates 3
```

Use `--coach-elo 1800` to restrict the recommendation engine, or omit it for full-strength bounded coaching. Scores are shown from the perspective of the side to move. For example, `+0.34` means a small advantage for the player whose turn it is; `-#2` means that side is being mated in two moves with best play.

## Play the local live prototype

Start as White against a 1600-Elo local opponent:

```powershell
python -m chess_analysis_coach play --player-color white --bot-elo 1600
```

Choose Black and use a restricted 1800-Elo coach:

```powershell
python -m chess_analysis_coach play `
  --player-color black `
  --bot-elo 2000 `
  --coach-elo 1800 `
  --time-ms 250 `
  --bot-time-ms 250 `
  --candidates 3
```

Stockfish 18 exposes accurate UCI Elo selection from **1320 through 3190**. The coach and opponent strengths are separate: the opponent uses `--bot-elo`; the coach is full strength unless `--coach-elo` is supplied.

During play, enter:

- SAN, such as `e4`, `Nf3`, or `O-O`;
- UCI, such as `e2e4` or `g1f3`;
- `undo`, `fen`, `help`, or `quit`.

The synchronous prototype deliberately displays a recommendation for every new position, including the position after the player's move and before the bot response.

## Verification

Deterministic suite:

```powershell
python -m pytest
```

Real Stockfish smoke test:

```powershell
$env:RUN_STOCKFISH_INTEGRATION = "1"
python -m pytest tests/test_stockfish_integration.py
```

## Development sequence

1. **Bounded position analysis** — implemented and real-engine verified.
2. **Synchronous interactive local game** — implemented with legal move input, undo, game termination, live recommendations, and selectable bot/coach Elo.
3. **Low-latency live pipeline** — move analysis into the background, cancel stale work, and publish only the newest position's result.
4. **Local board interface** — provide a usable local graphical board and direct move events; keep position-source adapters separate.
5. **Coaching explanations** — translate engine lines into concise tactical and positional learning notes.
6. **Session recording and post-match analysis** — compare fast live recommendations with deeper analysis and identify critical moments.
7. **Optional local recognition adapters** — local PGN stream, local application integration, or physical-board camera recognition.
8. **Bachelor-thesis evaluation** — measure latency, recommendation stability, recognition accuracy, and usefulness compared with deeper post-match analysis.
