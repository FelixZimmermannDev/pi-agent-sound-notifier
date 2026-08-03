# Chess Analysis Coach Project Instructions

## Delivery mode

- Treat this repository as a practical tool to be completed and used, not as a guided-learning project.
- Default to direct, autonomous implementation. Felix does not need to write code, review test syntax, answer teaching questions, or participate in incremental implementation steps.
- Convert broad requests into sensible technical requirements and proceed without approval when assumptions are low-risk and reversible.
- Ask only when unresolved ambiguity would materially change user-visible behavior, safety, cost, or the long-term architecture.
- Prefer completing a coherent vertical slice in one pass: implementation, errors, tests, configuration, documentation, and verification.
- Do not turn work into a quiz or require an active learning check. Explain only important decisions, trade-offs, and usage in the final report.
- Optimize for the shortest reliable path to a usable application, not for maximum abstraction or ceremonial process.

## Project purpose and boundaries

- Build a dependable local chess assistant that recommends and explains moves during permitted offline practice.
- Support live recommendations only for solo analysis, play against a local computer, or assisted training where every participant explicitly agrees.
- Never implement active-online-game polling, chess-site screen reading, browser automation, or secret assistance in competitive human games.
- Chess.com data may be retrieved only through documented public endpoints and analyzed after the online game has ended.
- Keep the global `C:\Users\Felix\.pi\agent\AGENTS.md` unchanged unless Felix explicitly requests a global change.

## Definition of done

A requested feature is complete only when, as applicable:

- the user-visible workflow is implemented end to end;
- common invalid input and external-tool failures produce understandable messages;
- focused automated tests cover deterministic behavior;
- relevant integration or smoke checks use the real boundary when available;
- the practical full test suite passes;
- installation and execution commands are documented and verified;
- remaining limitations and unverified external assumptions are reported clearly.

Never claim that the application works solely because its architecture looks correct or mocked tests pass.

## Context loading

- Before changing or evaluating architecture, responsibilities, dependencies, engine boundaries, or significant refactorings, read `docs/architecture.md`.
- Before deciding whether tests add value or designing, writing, reviewing, running, or changing tests, read `docs/testing.md`.
- For Clean Code reviews or behavior-preserving refactoring, load the global `clean-code-coach` skill and apply `docs/architecture.md`.
- Do not load detailed architecture or testing documents for unrelated questions or narrow mechanical work.

## Architecture and implementation standards

- Use a small, professional layered design with explicit boundaries between position input, application coordination, Stockfish integration, and presentation.
- Keep chess rules and recommendation logic independent of terminal formatting and future interfaces.
- Use `python-chess` for board, move, PGN, and UCI engine integration; do not recreate chess rules.
- Keep external processes and future network access behind narrow adapters so deterministic behavior remains testable.
- Prefer dependency injection at external boundaries, explicit typed result values, actionable domain-specific errors, and guaranteed resource cleanup.
- Keep state ownership and mutation explicit. Do not mutate caller-owned boards unexpectedly or rely on hidden global state.
- Keep analysis limits explicit so engine work is bounded.
- Keep the Stockfish executable path configurable and do not commit binaries, credentials, generated output, or machine-specific paths.
- Add abstractions only when they enforce a real boundary, remove demonstrated duplication, or support a concrete second implementation.
- Preserve unrelated user changes and make the smallest coherent change that completes the requested workflow.

## Product sequence

- First deliver a stable terminal workflow: FEN input → bounded Stockfish analysis → legal candidate moves and understandable output.
- Then add an interactive local move session if useful.
- Defer camera/screenshot recognition, GUI, persistence, and completed-game chess.com import until the core workflow works end to end.
- Do not create placeholders for deferred features.

## Verification and reporting

- Run the narrowest relevant checks during development and the full practical suite before finishing.
- Test deterministic application behavior without a real engine and maintain a small real-Stockfish smoke path once Stockfish is configured.
- Distinguish clearly between unit-tested behavior, real integration verification, failures, and checks that could not be run.
- Final reports should be concise: result, important decisions, commands/results, and remaining limitations.

## Context maintenance

- Keep `docs/architecture.md` and `docs/testing.md` as current durable guidance, not task logs.
- Update them only after an implemented architectural change or explicitly confirmed durable decision makes them inaccurate.
- Keep temporary plans, session handovers, and speculative designs out of `AGENTS.md` and the context documents.
