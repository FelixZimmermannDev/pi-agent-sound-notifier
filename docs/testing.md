# Chess Analysis Coach Testing

This document defines the project's durable testing responsibilities and strategy. Detailed feature examples belong in tests rather than this file.

## Responsibilities

The agent owns test planning, implementation, execution, and accurate reporting. Derive expected behavior from the request, documented product direction, and established professional conventions without requiring Felix to review test syntax or approve routine cases.

Choose a sensible, documented default for low-risk and reversible details. Ask Felix only when a product choice—such as a materially different scoring perspective or operating mode—would significantly affect user-visible behavior and cannot be inferred safely.

## Behavior review format

For each test-worthy behavior, review:

1. Main task of the function
2. Normal case + expected result
3. Edge case + expected result
4. What must remain unchanged

Use deterministic examples. Resolve routine details autonomously; clarify only material unresolved product decisions before encoding them as expected results.

## Default workflow

```text
derive the behavior contract
→ implement one complete vertical slice
→ write focused deterministic tests
→ run focused checks
→ run the full practical suite
→ verify the real external boundary when available
→ report results and limitations
```

Do not pause for routine test-plan approval. For bug fixes, first add a reproducing regression test when practical. Use whichever test-first or test-after sequence is most efficient while preserving evidence that the requested behavior works.

## Test levels

### Level 1: Pure chess and application behavior

Default level. Test position parsing, result transformation, state handling, calculations, and errors without launching Stockfish or using the network.

### Level 2: Coordination with controlled collaborators

Use a small fake or injected collaborator when testing that analysis coordination passes the correct board and limit to an engine boundary. Assert structured application results rather than private calls unless the collaboration itself is the behavior.

### Level 3: Stockfish integration

Use a real local Stockfish executable selectively to verify UCI startup, one small bounded analysis, and clean shutdown. Mark or isolate these tests so the normal suite can still run when Stockfish is unavailable. Never claim engine integration works when only fake-engine tests ran.

### Level 4: Terminal workflow

Once stable, test a small number of complete CLI paths: valid FEN, invalid FEN, missing engine, and successful recommendation output. Prefer invoking the Python entry point without spawning a subprocess unless process behavior matters.

### Level 5: External data

If completed-game chess.com import is added, keep live API checks separate from the deterministic default suite. Test parsing with saved minimal fixtures and test HTTP behavior at the adapter boundary.

## What tests should protect

Tests normally add value for:

- FEN and move validation behavior;
- legal-move and recommendation transformation;
- evaluation and mate-score presentation rules;
- explicit state changes in an interactive local session;
- engine startup, failure handling, limits, and shutdown;
- bug fixes and regressions.

Tests normally do not add value for documentation-only changes, formatting, empty scaffolding, or direct behavior-free configuration.

## Quality standards

- Test externally visible behavior through public APIs.
- Give each test one clear purpose and a descriptive name.
- Do not assert an exact Stockfish best move or centipawn score in ordinary tests; engine versions and settings can change them.
- For deterministic recommendation tests, use controlled engine results.
- With a real engine, assert stable invariants such as successful startup, legal returned moves, bounded result count, and clean shutdown.
- Verify that rejected operations do not mutate a caller-owned board or session state.
- Avoid real network access in the default test suite.
- Keep tests independent and use temporary paths for files.
- Never weaken a valid test merely to make the suite pass.

## Commands

From the repository root with the virtual environment activated:

```powershell
# Deterministic default suite; real engine test is skipped.
python -m pytest

# Explicit real Stockfish boundary check.
$env:RUN_STOCKFISH_INTEGRATION = "1"
python -m pytest tests/test_stockfish_integration.py
```

Run a focused file first when changing behavior, then the full suite when practical. Keep the real executable check opt-in so the default suite remains portable when Stockfish is unavailable.

## Failure classification

Before changing code or checks, classify discrepancies:

- `SPEC`: intended behavior is missing or ambiguous
- `CODE`: production code violates valid behavior
- `CHECKER`: a test or static check encodes the wrong expectation
- `HARNESS`: discovery, dependencies, configuration, or environment failed

## Result reporting

Report:

```text
Behavior reviewed:
- ...

Tests added or changed:
- contract item → test case

Verification:
- command → result

Not covered or still open:
- ...
```

Never claim functionality works without identifying the command that verified it.

## Maintenance

Update this document only when the durable test workflow, levels, or responsibilities change. Do not record temporary test results or individual feature cases here.
