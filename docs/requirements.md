# Chess Analysis Coach Requirements Index

This is a stable traceability index for guarded tasks and audits. The linked project documents remain canonical; this index does not replace or weaken them.

## Safety and product boundaries

- **SAFE-001 — Permitted local assistance only.** Live recommendations are limited to solo analysis, local-computer play, or explicitly agreed assisted local training. Source: `AGENTS.md`, “Project purpose and boundaries”.
- **SAFE-002 — No covert active-online assistance.** Do not implement active-game polling, chess-site screen reading, browser automation, or secret competitive assistance. Source: `AGENTS.md`, “Project purpose and boundaries”.
- **SAFE-003 — Completed public data only.** Chess.com data may be retrieved only through documented public endpoints after the game has ended. Source: `AGENTS.md`, “Project purpose and boundaries”.

## Delivery and architecture

- **DONE-001 — Complete vertical slice.** Applicable workflow, understandable failures, deterministic tests, real-boundary verification, documentation, and limitation reporting form the Definition of Done. Source: `AGENTS.md`, “Definition of done”.
- **ARCH-001 — Explicit application boundaries.** Keep position input, application coordination, Stockfish integration, and presentation separate. Source: `AGENTS.md`, “Architecture and implementation standards”.
- **ARCH-002 — Use python-chess.** Do not recreate board, move, PGN, or UCI rules. Source: `AGENTS.md`, “Architecture and implementation standards”.
- **ARCH-003 — Narrow external adapters.** External processes and future network access stay behind narrow injectable boundaries with guaranteed cleanup. Source: `AGENTS.md` and `docs/architecture.md`.
- **ARCH-004 — Explicit state ownership.** Do not rely on hidden board state or unexpectedly mutate caller-owned boards. Source: `AGENTS.md` and `docs/architecture.md`, “State and dependency guidance”.
- **ARCH-005 — Bounded engine work.** Analysis limits must remain explicit and engine work bounded. Source: `AGENTS.md` and `docs/architecture.md`.
- **ARCH-006 — No speculative abstraction.** Add abstractions only for a demonstrated boundary, stable duplication, or concrete second implementation. Source: `AGENTS.md` and `docs/architecture.md`.
- **ARCH-007 — Latest live result wins.** Background live analysis must reject or cancel stale revisions so old work cannot overwrite a newer position. Source: `docs/architecture.md`, “Latest-position analysis”.

## Testing and evidence

- **TEST-001 — Test observable behavior.** Prefer public behavior and structured results over private implementation details. Source: `docs/testing.md`, “Quality standards”.
- **TEST-002 — Rejection preserves state.** Rejected operations must not mutate caller-owned boards or session state. Source: `docs/testing.md`, “Quality standards”.
- **TEST-003 — Real claims need real evidence.** Mocked tests cannot establish that Stockfish or another real external boundary works. Source: `AGENTS.md` and `docs/testing.md`, “Test levels”.
- **TEST-004 — Deterministic default suite.** The normal suite avoids real network access and isolates optional Stockfish integration. Source: `docs/testing.md`.
- **TEST-005 — Preserve valid checks.** Never weaken a valid test merely to make the suite pass. Source: `docs/testing.md`, “Quality standards”.
- **TEST-006 — Classify discrepancies.** Use `SPEC`, `CODE`, `CHECKER`, or `HARNESS` before changing requirements, production code, or checks. Source: `docs/testing.md`, “Failure classification”.

## Harness boundary

- **HARNESS-001 — Project-local operation.** The feedback loop, prompts, evals, reports, and corrections belong only to this repository.
- **HARNESS-002 — Canonical rules are protected.** The evaluator may propose an interface improvement but must not rewrite canonical requirements.
- **HARNESS-003 — Diagnose before correcting.** Change the task compiler only when evidence shows a translation failure; ordinary implementation defects remain `CODE`.
- **HARNESS-004 — Every interface correction needs an eval.** A confirmed task-translation improvement must add a generalized regression case and continue to satisfy prior cases.
