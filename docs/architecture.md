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
              → player click/drag move → bounded quality comparison
              → intermediate bot-turn state → optional local premove queue
              → Elo-limited bot move → validate/apply or reject premove
              → next recommendation + incremental annotated PGN snapshot

Permitted local screen → DXCAM frame in RAM → stable 8×8 observation
                       → unique legal move reconciliation + position revision
                       → latest-only bounded Stockfish/coaching analysis
                       → click-through revision-bound desktop overlay
```

- `chess_analysis_coach.cli` owns the `analyze`, `play`, and `web` commands, Stockfish path discovery, process lifetime, terminal output, and exit codes.
- `python-chess` owns chess rules, FEN, SAN/UCI conversion, score handling, game outcomes, and UCI communication.
- `LocalGameSession` is the single owner of interactive board state. It applies legal player/bot moves, increments a monotonic revision, supports bounded undo, and exposes defensive snapshots.
- The synchronous terminal prototype requests one recommendation for each new position revision and never reanalyzes unchanged state after informational commands or rejected moves.
- `LocalWebGame` coordinates one browser game without putting chess rules into HTTP routes or JavaScript. It accepts only player-selected legal moves, invokes Stockfish for the local opponent, and publishes recommendations only on the player's turn.
- The browser supports click and native drag input through the same legal-move submission path. Dragging changes presentation only until the validated API call succeeds.
- The optional `side_projects/chess_overlay` package is a separate Windows presentation and position source for permitted local/offline boards. DXCAM reads only its configured rectangle, raw frames remain in reusable memory, and compact occupancy/signature observations—not images—cross into chess synchronization. It calibrates from the standard starting position and accepts a visual change only when stable frames match exactly one legal `python-chess` move. The reconciler is the single owner of this logical board and exposes FEN snapshots with a monotonic revision.
- The desktop overlay runs recognition and DXCAM outside the Qt UI thread and owns a latest-position analysis coordinator. Stockfish remains bounded; an in-flight stale result is discarded when a newer revision arrives, and the presentation independently verifies revision and FEN before publishing an arrow or coaching text. F8 changes presentation visibility only, while F6 controls frame editing/capture and F9 explicitly resets synchronization to the standard position.
- Player and bot phases use separate HTTP operations. During the blocking bot operation, JavaScript may queue one local premove from a server-provided bounded candidate set. After the bot response, the premove is submitted only when it is legal in the actual resulting position; otherwise it is discarded without mutating server state.
- Before game start, the browser may configure one, two, or three MultiPV candidates, local opponent Elo, and an independent limited or maximum-strength coach through the validated game boundary. One candidate, 1500 opponent Elo, and maximum coach strength are the defaults; behavioral settings are immutable during a running game. The candidates appear as selectable color-matched root arrows. Arrow selection and forecast visibility are presentation state and never apply a move. Opponent and own continuation modes independently support off, relevant-only, or all, with relevant-only as the default. The Stockfish adapter preserves up to six UCI principal-variation plies; presentation draws at most the selected candidate's expected reply and next own move as numbered dashed arrows.
- The evaluation bar uses a separate unrestricted position evaluation whenever coaching is Elo-limited, so randomized weak candidate selection cannot distort the objective reference. A transparent bounded logistic win-chance curve converts centipawns to a fixed White-perspective visual share. Presentation applies a 2-point deadband and a 650 ms transition; mate and terminal results always target the winning side. Chess.com's exact production geometry is not treated as known or copied because no official formula or frontend source is published.
- After a move, a second bounded position evaluation estimates normalized evaluation-share loss. Transparent thresholds produce a provisional category and per-color running mean. This metric is intentionally not called or treated as Chess.com's proprietary Accuracy.
- `ChessClock` is the server-side authority for both countdowns and increment. Browser countdown animation is presentation only; polling reconciles it with server time. Coach-only evaluation runs while both game clocks are stopped, so application overhead is not charged to either side.
- The Flask adapter binds only to `127.0.0.1`. It serves a packaged HTML/CSS/JavaScript board and a narrow JSON API; it is not a public web application. Its optional `--no-coach` mode skips web recommendation/evaluation work while preserving the local Stockfish opponent, allowing the independent desktop overlay to be the only coaching presentation.
- Browser games are incrementally written as PGN snapshots under the ignored `output/games` directory. Player moves include the current top live recommendation as a PGN comment, and the same PGN can be downloaded through the local UI.
- The Stockfish adapter starts the external process only when entering its context and guarantees a shutdown attempt on every exit path.
- Analysis and bot work use separate explicit time limits. Both default to 250 ms so local strength comparisons use equal move-selection budgets; the browser exposes the actual budgets for verification. The localhost game allows at most three candidates.
- Stockfish opponent and coach strength are independently selectable through the supported `UCI_Elo` target range of 1320–3190 in both CLI and pre-game browser settings. Opponent Elo applies only to the local engine opponent. A limited coach selects each displayed root through Stockfish's Elo-limited final move selection, then runs a root-constrained analysis for its evaluation and continuation; unrestricted analysis-PV ordering must not replace that selected move. Coaching is full strength by default; its selected setting controls recommendations and provisional move-quality comparisons, while the evaluation bar remains an unrestricted objective reference. UCI targets are statistical and are not treated as guaranteed single-game ratings or as directly equivalent to ratings advertised by external platforms.
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

The implemented graphical sources are the direct localhost board and the optional desktop recognizer for a user-calibrated local/offline 8×8 board. The latter is deliberately generic: it has no URL, DOM, browser-control, or platform-specific adapter and must not be used over an active chess website. A screenshot is not treated as complete FEN; starting from the standard position, compact visual changes advance state only through one uniquely matching legal move. The project does not implement active chess-site polling, chess-site screen reading, or browser automation. Completed online games remain separate and may enter post-match analysis only through documented public endpoints after the game.

### Live session

The session is the single owner of the current board and move history. It validates every transition with `python-chess`, exposes immutable snapshots to analysis, and keeps state unchanged after rejected input. Both terminal and browser presentation use this boundary without moving chess state into presentation code.

### Latest-position analysis

Live analysis must not let old results overwrite newer recommendations. The desktop overlay now uses a single-worker coordinator that attaches a monotonically increasing position revision to each request, replaces pending stale work, disregards an in-flight stale result, and publishes only when the revision still matches. The overlay presentation performs a second revision/FEN check. Engine work remains explicitly bounded. The localhost game's bot request is still synchronous and remains a separate future background-coordination slice.

### Coaching and recording

Engine scores and SAN/UCI principal variations are structured input to a separate coaching component. The browser prototype derives small deterministic cues for checks, captures, castling, promotion, visible multi-attacks, development, central control, and king safety. It heuristically labels opening, middlegame, or endgame from move number and remaining non-pawn material, then marks context tactical when the short line contains checks, captures, promotions, or attacks on valuable pieces. Relevant-only forecasts use those same visible tactical signals or a forced reply to check. Each candidate plan may name the expected counter and one next own step. These cues deliberately do not claim to be deep tactical proof, and only three plies are visualized. Provisional move categories use the fast live budget and may change under deeper analysis.

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

1. Move the remaining localhost browser engine work behind background coordination so the bot request itself is not blocked; preserve the implemented premove validation contract. The desktop overlay already uses latest-position coordination.
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
