# Chess Analysis Coach Architecture

This document records durable architecture direction and project-specific code-quality guidance. Implemented behavior, intended direction, and open decisions are deliberately separated.

## Project purpose

Chess Analysis Coach is a dependable local Python application that explains and recommends moves during permitted live chess practice. It is intended for local solo play, play against a local computer, or explicitly agreed assisted local training. It also records sessions for deeper post-match review and research comparison. It must not assist active online or unapproved competitive games.

## Currently implemented

Three local workflows are implemented:

```text
Quoted FEN → validation → defensive board copy → bounded Stockfish MultiPV
           → typed recommendation → terminal presentation

Terminal session → recommendation → player SAN/UCI move
                 → Elo-limited local bot move → repeat

Local browser → player-only MultiPV recommendation + fixed evaluation bar
              → player click move → provisional bounded quality comparison
              → Elo-limited local bot move → next recommendation
              → browser state + incremental annotated PGN snapshot
```

- `chess_analysis_coach.cli` owns the `analyze`, `play`, and `web` commands, Stockfish path discovery, process lifetime, terminal output, and exit codes.
- `python-chess` owns chess rules, FEN, SAN/UCI conversion, score handling, game outcomes, and UCI communication.
- `LocalGameSession` is the single owner of interactive board state. It applies legal player/bot moves, increments a monotonic revision, supports bounded undo, and exposes defensive snapshots.
- The synchronous terminal prototype requests one recommendation for each new position revision and never reanalyzes unchanged state after informational commands or rejected moves.
- `LocalWebGame` coordinates one browser game without putting chess rules into HTTP routes or JavaScript. It accepts only player-selected legal moves, invokes Stockfish for the local opponent, and publishes recommendations only on the player's turn.
- The browser presents the top MultiPV candidates as selectable color-matched root arrows. Arrow selection is presentation state and never applies a move.
- The evaluation bar normalizes the top candidate to a fixed White perspective. A bounded arctangent mapping converts centipawns to a visual share; mate and terminal results pin the bar to the winning side.
- After a move, a second bounded position evaluation estimates normalized evaluation-share loss. Transparent thresholds produce a provisional category and per-color running mean. This metric is intentionally not called or treated as Chess.com's proprietary Accuracy.
- `ChessClock` is the server-side authority for both countdowns and increment. Browser countdown animation is presentation only; polling reconciles it with server time. Coach-only evaluation runs while both game clocks are stopped, so application overhead is not charged to either side.
- The Flask adapter binds only to `127.0.0.1`. It serves a packaged HTML/CSS/JavaScript board and a narrow JSON API; it is not a public web application.
- Browser games are incrementally written as PGN snapshots under the ignored `output/games` directory. Player moves include the current top live recommendation as a PGN comment, and the same PGN can be downloaded through the local UI.
- The Stockfish adapter starts the external process only when entering its context and guarantees a shutdown attempt on every exit path.
- Analysis and bot work use separate explicit time limits. Current CLI defaults are 250 ms and three candidates.
- Stockfish opponent strength is selectable through its supported `UCI_Elo` range of 1320–3190. Coaching is full strength by default and can be limited independently.
- Candidate cards use the side-to-move perspective and include a short principal variation; the live bar separately uses a fixed White perspective so it does not reverse meaning after every move.
- Application coordination analyzes a defensive board copy, including move history, and does not mutate caller-owned state.
- Expected position, move, session, and engine failures produce actionable user-facing messages.
- Deterministic automated tests cover the implemented boundaries. Stockfish 18 installed through winget has also passed bounded analysis and local-play smoke verification.

## Intended live architecture

Extend the working vertical slice without coupling acquisition, engine work, or presentation:

```text
Position source
  ├── local board move events
  ├── local PGN/move stream
  └── optional physical-board recognition
             ↓
Live session (single owner of current board and move history)
             ↓
Latest-position analysis coordinator
             ↓
Stockfish worker (bounded and cancellable)
             ↓
Structured recommendation + coaching explanation
             ├── live presentation
             └── session recorder → deeper post-match report
```

### Position sources

A position source emits a complete position or a proposed move. It does not invoke Stockfish or format recommendations. The implemented terminal and localhost-board sources both submit direct legal move input, which is deterministic and gives exact board state. Additional local sources should adapt into the same session boundary.

The implemented graphical source is the localhost board. The project does not implement active chess-site polling, chess-site screen reading, or browser automation. A future manual companion may accept moves that the user explicitly enters from a permitted bot game; completed online games remain separate and may enter post-match analysis through documented public endpoints.

### Live session

The session is the single owner of the current board and move history. It validates every transition with `python-chess`, exposes immutable snapshots to analysis, and keeps state unchanged after rejected input. Both terminal and browser presentation use this boundary without moving chess state into presentation code.

### Latest-position analysis

Live analysis must not let old results overwrite newer recommendations. The coordinator will attach a monotonically increasing position revision to each request, cancel or disregard stale work, and publish a result only when its revision still matches the current session. Engine work remains explicitly bounded.

### Coaching and recording

Engine scores and principal variations are structured input to a separate coaching component. The browser prototype derives small deterministic cues for checks, captures, castling, promotion, and visible multi-attacks. These cues deliberately do not claim to be deep tactical proof. Its provisional move categories use the fast live budget and may change under deeper analysis.

Basic PGN recording now preserves moves, clock values, results, the top live recommendation attached to player moves, and provisional live quality comments. A future post-match report will add deeper comparison results without changing game-state ownership.

## State and dependency guidance

- Pass current positions explicitly; do not use hidden global board state.
- Treat recommendations as results for a specific immutable input position.
- Give the live session one clear owner and return copies or snapshots at boundaries.
- Make analysis limits explicit. Do not hide expensive unlimited engine work behind a simple call.
- Keep the Stockfish executable path in command input or local configuration, never as a committed machine-specific absolute path.
- Ensure engine processes are closed even when analysis fails.
- Keep acquisition and future external data adapters outside chess rules and recommendation logic.
- Prefer a native Stockfish process for the initial Windows workflow; containerization is optional future experiment infrastructure, not a runtime requirement.

## Professional quality principles

- Use standard chess terms such as FEN, legal move, side to move, candidate move, evaluation, centipawn, and mate score precisely.
- Prefer small typed recommendation values over passing raw engine dictionaries throughout the application.
- Validate data at the boundary that first understands it, and preserve useful details in user-facing error messages.
- Keep I/O visible. Avoid constructors that unexpectedly start Stockfish, access the network, or write files.
- Depend inward: terminal, engine, recognition, and persistence adapters may depend on application contracts; application behavior must not depend on presentation formatting.
- Guarantee cleanup of engine processes with explicit ownership and context management, including exceptional paths.
- Keep configuration external to domain behavior and provide useful defaults only when they are portable and safe.
- Accept small duplication until the shared concept is stable; do not create abstractions solely to satisfy DRY.
- Prefer a complete, tested vertical slice over speculative framework code for future features.
- Make the smallest coherent change that fully satisfies the requested workflow and avoid unrelated cleanup.

## Next implementation slices

1. Move engine work behind a latest-position background coordinator so browser requests are not blocked and stale results cannot be published.
2. Add deep post-game analysis that recomputes played moves with a larger Stockfish budget and reports stable evaluation loss and critical moments.
3. Expand deterministic coaching from basic tactical cues to score-change, threat, and positional explanations, including optional principal-variation overlays.
4. Add a manual external-bot companion only for an explicitly permitted mode; keep it independent from website acquisition or control.
5. Add thesis-oriented exports and metrics once live and deep-analysis outputs are stable.

Do not create empty adapters or interfaces for later sources before the current vertical slice needs them.

## Open decisions

Ask only when implementation evidence makes one of these choices material:

- Whether the first optional external position-source experiment should be manual move relay, a permitted local PGN stream, or a physical board
- Which live and deep-analysis budgets should be used in thesis experiments
- Which objective and subjective metrics define coaching usefulness
- Whether session recording should use PGN annotations, JSON, or a small local database

## Maintenance

Update this document only when implemented architecture or an explicitly confirmed durable decision makes it incomplete or incorrect. Detailed feature behavior belongs in code and tests; temporary progress belongs in the Pi session.
