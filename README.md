# Chess Analysis Coach

A local Python application for **live move recommendations during permitted local chess practice** and deeper post-game review. Suitable examples include playing against a local engine, using your own analysis board, or an assisted local training game where every participant has explicitly agreed to engine assistance.

## Current status

Three local workflows are implemented:

```text
FEN → validation → bounded Stockfish MultiPV → ranked recommendations

terminal game → recommendation → player SAN/UCI move → local Stockfish reply

localhost browser game → clickable board + two chess clocks
                       → recommendations only for the player's turn
                       → local Stockfish reply + move list + PGN snapshot
```

The browser prototype is served only on `127.0.0.1`. It never plays the player's recommended move: the player selects and submits every own move, while Stockfish controls only the local opponent. Candidate cards include evaluations, principal variations, and small deterministic tactical cues. Every played move, clock value, and current result is recorded as PGN under `output/games` and can also be downloaded in the browser.

Stockfish 18 was discovered from the local winget installation and verified with real bounded analysis and local play. Deterministic tests cover position and move errors, state ownership, clock behavior, PGN recording, browser API coordination, analysis, Elo configuration, Stockfish-output transformation, cleanup, presentation, and CLI behavior. A separate opt-in test exercises the real executable.

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

If `python` is not globally available or the environment is not activated, invoke the project interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m chess_analysis_coach --help
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

The synchronous terminal prototype deliberately displays a recommendation for every new position, including the position after the player's move and before the bot response.

## Play in the local browser prototype

Start a ten-minute game as White. The default browser opens automatically:

```powershell
.\.venv\Scripts\python.exe -m chess_analysis_coach web `
  --player-color white `
  --bot-elo 1500 `
  --minutes 10
```

Example with a five-minute clock and three-second increment:

```powershell
.\.venv\Scripts\python.exe -m chess_analysis_coach web `
  --player-color black `
  --bot-elo 1800 `
  --minutes 5 `
  --increment-seconds 3
```

The application binds to `http://127.0.0.1:8765`. Use `--no-browser` to suppress automatic browser opening or `--port 9000` to select another local port. Click **Partie starten**, then select a piece and its destination square. PGN snapshots are written after every move to `output/games`; this generated directory is ignored by Git.

This first graphical slice remains synchronous: a move request waits briefly for the bounded bot move and new coaching analysis. Deep post-game mistake classification is not implemented yet.

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
2. **Synchronous interactive terminal game** — implemented with legal move input, undo, game termination, live recommendations, and selectable bot/coach Elo.
3. **Clocked localhost browser game** — implemented with a clickable board, recommendations for the player's side, local opponent moves, two countdown clocks, move history, and incremental PGN recording.
4. **Deep post-game analysis** — compare each played move with deeper Stockfish analysis and identify inaccuracies, mistakes, blunders, and critical moments.
5. **Low-latency live pipeline** — move analysis into the background, cancel stale work, and publish only the newest position's result.
6. **Richer coaching explanations** — expand the first tactical cues into concise tactical and positional learning notes.
7. **External bot companion mode** — accept manually entered moves from an explicitly permitted external bot game without reading or controlling a website.
8. **Bachelor-thesis evaluation** — measure latency, recommendation stability, explanation usefulness, and agreement with deeper post-match analysis.
