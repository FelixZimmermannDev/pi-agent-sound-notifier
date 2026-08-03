# Project Harness Feedback Loop

A minimal project-local Pi feedback loop for implementation tasks. It is not installed globally and never modifies global Pi instructions, extensions, models, credentials, or settings.

## Use

```text
/guarded <implementation request>
```

Use normal chat for explanation, investigation, or planning without requested file changes. A guarded task requires a clean Git worktree so its output diff is attributable to one request.

The loop performs only two responsibilities:

1. snapshot the original user request and original loaded requirements, then compare them with the resulting code and tests through an isolated read-only evaluator;
2. when evidence shows an interface failure, suggest one optional project-local improvement to `prompts/interface.md` without applying it or changing canonical requirements.

The normal coding agent remains responsible for implementation and applicable project tests. The controller does not run those tests a second time.

## Files

- `index.ts` — intercepts `/guarded`, records evidence, starts the read-only evaluator, and displays its report
- `commands/guarded.md` — slash-command autocomplete metadata
- `config.json` — project marker, canonical requirement paths, evaluator settings, and size limits
- `prompts/interface.md` — small operational interface supplied only to the guarded coding task
- `prompts/auditor.md` — instructions supplied only to the isolated evaluator

Canonical project guidance remains in the project-specific `AGENTS.md`, `docs/architecture.md`, and `docs/testing.md`.

## Project/global boundary

Pi discovers this extension only from this trusted repository:

```text
chess-analysis-coach/.pi/extensions/project-harness-feedback-loop/
```

Nothing is copied to the global extension location:

```text
C:\Users\Felix\.pi\agent\extensions\
```

Raw run evidence is ignored under `output/project-harness-feedback-loop/runs/<run-id>/`. Stored files consume no model tokens unless a guarded coding task or evaluator actually reads them.
