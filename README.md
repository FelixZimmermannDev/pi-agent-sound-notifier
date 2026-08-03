# Chess Analysis Coach

A local Python application for **live move recommendations during permitted local chess practice** and deeper post-game review. Suitable examples include playing against a local engine, using your own analysis board, or an assisted local training game where every participant has explicitly agreed to engine assistance.

## Current status

Three local workflows are implemented:

```text
FEN → validation → bounded Stockfish MultiPV → ranked recommendations

terminal game → recommendation → player SAN/UCI move → local Stockfish reply

localhost browser game → click or drag moves + two chess clocks
                       → live evaluation bar + selectable MultiPV arrows
                       → queued legal premove while Stockfish thinks
                       → provisional quality + short tactical plan overlay
                       → local Stockfish reply + move list + PGN snapshot
```

The browser prototype is served only on `127.0.0.1`. It never plays the player's recommended move: the player clicks or drags every own move, while Stockfish controls only the local opponent. During the bot phase, one player move can be queued as a blue premove and is automatically submitted only if it remains legal after the bot response. A fixed White-perspective evaluation bar updates after every completed turn.

Candidate cards include evaluations, principal variations, deterministic tactical cues, and selectable color-matched root arrows. The default is one green best-move recommendation. Before starting, the local UI can switch to two or three candidates; that choice is locked during the game. The selected candidate may additionally show the expected reply and one next own move as numbered dashed arrows.

Opponent counters and own continuations each have live display modes **Aus**, **Wichtig**, and **Alle**; both default to **Wichtig**. Relevance is a transparent heuristic based on checks, captures, promotions, attacks on valuable pieces, or a forced reply to check. Candidate context is labeled as opening, middlegame, or endgame and as positional or tactical. The phase boundary is intentionally heuristic rather than a chess rule. A concise plan identifies development, central control, king safety, checks, captures, counters, and the next own step without displaying a cluttered full search tree.

After each move, a second bounded evaluation—or the terminal result—estimates normalized evaluation-share loss. This produces a clearly labeled **provisional** move category and running accuracy for both colors. It is an original transparent prototype metric, not Chess.com's proprietary Accuracy. Every played move, clock value, live recommendation, provisional quality, and current result is recorded as PGN under `output/games` and can also be downloaded in the browser.

Stockfish 18 was discovered from the local winget installation and verified with real bounded analysis and local play. Deterministic tests cover position and move errors, state ownership, clock behavior, PGN recording, browser API coordination, analysis, Elo configuration, Stockfish-output transformation, cleanup, presentation, and CLI behavior. A separate opt-in test exercises the real executable.

## Fair-play boundary

Live recommendations are supported only for local solo/computer practice or explicitly agreed assisted training. This project does not inspect active chess websites, read chess-site screens, automate browsers, or secretly assist in competitive games against another person. Completed online games may later be retrieved through documented public endpoints for post-game review.

An online game being “unranked” does not by itself permit engine assistance. A future online integration would require an explicit platform-supported assisted/bot mode and documented interface; it will not be implemented through scraping or hidden automation. An external platform's advertised bot rating will be recorded as platform-specific metadata, not assumed to equal Stockfish's UCI target without empirical calibration.

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

Stockfish 18 accepts UCI Elo target values from **1320 through 3190**. These are statistical strength targets rather than guarantees for one game, and effective play also depends on engine version, hardware, and thinking time. The coach and opponent strengths are separate: the opponent uses `--bot-elo`; the coach is full strength unless `--coach-elo` is supplied. For a fair local comparison, give both the same target and the same `--time-ms`/`--bot-time-ms` budget. Both default to 250 ms.

A limited coach now obtains its displayed root move through the same Elo-limited Stockfish `bestmove` selection used by the opponent. It then analyzes only that selected move to provide an evaluation and short continuation; this explanatory pass cannot replace the chosen move with a full-strength principal variation.

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

The application binds to `http://127.0.0.1:8765`. Use `--no-browser` to suppress automatic browser opening or `--port 9000` to select another local port. Before clicking **Partie starten**, choose one, two, or three recommendations, set the local opponent from 1320 to 3190 UCI Elo, and choose either maximum coach strength or a separately limited coach from 1320 to 3190 Elo. The page labels limited values as UCI targets and displays the actual coach/opponent calculation budgets. One candidate, a 1500-Elo opponent, maximum coach strength, and equal 250 ms budgets are the defaults. These settings lock during the game. Then click a piece and destination or drag the piece directly. The evaluation bar always treats positive values as a White advantage, independent of whose turn it is. Selecting a recommendation card emphasizes its matching arrow. The **Gegner-Counter** and **Eigene Fortsetzung** controls remain available during play and determine whether no, only relevant, or all short forecast arrows and details are visible.

After submitting a normal move, the browser receives the intermediate bot-turn position. While the bounded bot request runs, click or drag one blue premove; press `Escape` to cancel it. The move is checked against the actual resulting position and is discarded with a message if it became illegal.

PGN snapshots are written after every move to `output/games`; this generated directory is ignored by Git. Coach-only analysis is performed while both game clocks are paused, so application overhead is not charged to either side. Bot calculation remains a synchronous HTTP request, but local premove selection stays interactive during that request. Deep post-game reclassification is not implemented yet.

### Provisional live quality

The live metric converts centipawn evaluation to a bounded evaluation share and compares that share before and after a move. Playing the first Stockfish candidate is marked **Bester Zug**. Other moves are classified by share loss: up to 1 point **Sehr gut**, 3 **Gut**, 7 **Ungenauigkeit**, 15 **Fehler**, and above 15 **Patzer**. Per-move accuracy is `max(0, 100 - 2.5 × loss)` and the displayed running value is the arithmetic mean for that color. Deeper post-game analysis will later recompute these values with a larger budget.

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
3. **Clocked localhost browser game** — implemented with click and drag input, validated premoves, pre-game recommendation-count plus independent opponent/coach strength controls, live evaluation bar, selectable MultiPV, independently filtered opponent/own forecast arrows, phase-aware tactical plan summaries, provisional move quality and accuracy, local opponent moves, two countdown clocks, move history, and incremental PGN recording.
4. **Low-latency live pipeline** — move analysis into the background, cancel stale work, and publish only the newest position's result.
5. **Deep post-game analysis** — recompute each played move with a larger Stockfish budget and identify stable inaccuracies, mistakes, blunders, and critical moments.
6. **Richer coaching explanations** — expand the first tactical cues into concise tactical and positional learning notes.
7. **External bot companion mode** — accept manually entered moves from an explicitly permitted external bot game without reading or controlling a website. Local `bot_elo` configuration will not apply when the opponent is external.
8. **Bachelor-thesis evaluation** — measure latency, recommendation stability, explanation usefulness, and agreement with deeper post-match analysis.
