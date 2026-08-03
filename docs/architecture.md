# Chess Analysis Coach Architecture

This document records durable architecture direction and project-specific code-quality guidance. Implemented behavior, intended direction, and open decisions are deliberately separated.

## Project purpose

Chess Analysis Coach is a dependable local Python application that explains and recommends moves during permitted live chess practice. It is intended for local solo play, play against a local computer, or explicitly agreed assisted local training. It also records sessions for deeper post-match review and research comparison. It must not assist active online or unapproved competitive games.

## Currently implemented

Two terminal workflows are implemented:

```text
Quoted FEN → validation → defensive board copy → bounded Stockfish MultiPV
           → typed recommendation → terminal presentation

Local session → recommendation for current revision → player SAN/UCI move
              → recommendation for new revision → Elo-limited bot move → repeat
```

- `chess_analysis_coach.cli` owns the `analyze` and `play` commands, Stockfish path discovery, terminal output, and exit codes.
- `python-chess` owns chess rules, FEN, SAN/UCI conversion, score handling, game outcomes, and UCI communication.
- `LocalGameSession` is the single owner of interactive board state. It applies legal player/bot moves, increments a monotonic revision, supports bounded undo, and exposes defensive snapshots.
- The synchronous terminal prototype requests one recommendation for each new position revision and never reanalyzes unchanged state after informational commands or rejected moves.
- The Stockfish adapter starts the external process only when entering its context and guarantees a shutdown attempt on every exit path.
- Analysis and bot work use separate explicit time limits. Current CLI defaults are 250 ms and three candidates.
- Stockfish opponent strength is selectable through its supported `UCI_Elo` range of 1320–3190. Coaching is full strength by default and can be limited independently.
- Candidate scores are normalized to the side-to-move perspective and include a short principal variation.
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

A position source emits a complete position or a proposed move. It does not invoke Stockfish or format recommendations. The first live source is the implemented interactive terminal session with direct legal move input, because it is deterministic and gives exact board state. Additional local sources should adapt into the same session boundary.

The project does not implement active chess-site polling, chess-site screen reading, or browser automation. Completed online games remain separate and may enter only the post-match workflow through documented public endpoints.

### Live session

The session is the single owner of the current board and move history. It validates every transition with `python-chess`, exposes immutable snapshots to analysis, and keeps state unchanged after rejected input. This boundary supports a future terminal session and local graphical board without moving chess state into presentation code.

### Latest-position analysis

Live analysis must not let old results overwrite newer recommendations. The coordinator will attach a monotonically increasing position revision to each request, cancel or disregard stale work, and publish a result only when its revision still matches the current session. Engine work remains explicitly bounded.

### Coaching and recording

Engine scores and principal variations remain structured input to a separate coaching component. Live explanations should be concise and latency-aware; deeper post-match work may use larger limits. Recording should preserve moves, timing, live recommendations, and later comparison results without making persistence a requirement of basic analysis.

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

1. Move engine work behind a latest-position background coordinator so input and presentation are not blocked and stale results cannot be published.
2. Add a local graphical board that emits direct move events into `LocalGameSession`.
3. Add concise coaching explanations based on score changes, legal threats, and principal variations.
4. Record local sessions and compare fast live results with deeper post-match analysis.
5. Add optional local position-source adapters only when the core live workflow is stable.

Do not create empty adapters or interfaces for later sources before the current vertical slice needs them.

## Open decisions

Ask only when implementation evidence makes one of these choices material:

- Which local user interface should follow the terminal session (desktop, browser served only on localhost, or another local UI)
- Whether the first recognition experiment targets a local application, a PGN stream, or a physical board
- Which live and deep-analysis budgets should be used in thesis experiments
- Which objective and subjective metrics define coaching usefulness
- Whether session recording should use PGN annotations, JSON, or a small local database

## Maintenance

Update this document only when implemented architecture or an explicitly confirmed durable decision makes it incomplete or incorrect. Detailed feature behavior belongs in code and tests; temporary progress belongs in the Pi session.
