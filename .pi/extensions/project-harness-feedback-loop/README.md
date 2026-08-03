# Project Harness Feedback Loop

This repository contains a project-local Pi feedback loop for implementation tasks. It is not installed globally and does not modify the global Pi configuration or global `AGENTS.md`.

## Project/global boundary

Pi discovers this extension from the repository path `.pi/extensions/project-harness-feedback-loop/` after the project is trusted. No file is copied to or loaded from the global extension path `C:\Users\Felix\.pi\agent\extensions\`. Pi itself, configured models, credentials, and global instructions remain global infrastructure; this controller, its prompts, config, evals, and evidence are project-owned.

## Daily use

Use one command when a request should change project files:

```text
/guarded <implementation request>
```

Use normal chat prompts for explanation, investigation, or planning that should not change files.

A guarded run:

1. requires a clean Git worktree so one task has an attributable diff;
2. snapshots the original request, effective system prompt, and requirement sources;
3. requires the coding agent to call `record_task_contract` before `edit` or `write`;
4. runs the configured deterministic checks;
5. starts one isolated Pi process with read-only tools to evaluate translation and implementation separately;
6. stores evidence under ignored `output/project-harness-feedback-loop/runs/<run-id>/`;
7. posts a `PASS`, `CODE`, `CHECKER`, `HARNESS`, `SPEC`, or `MIXED` report in the Pi session.

The evaluator never edits files. In this first version, a harness improvement is proposal-only. Canonical project requirements are never changed automatically.

## Project-local components

- `.pi/extensions/project-harness-feedback-loop/index.ts` — executable project-local Pi controller and `/guarded` input interception
- `.pi/extensions/project-harness-feedback-loop/commands/guarded.md` — slash-command discovery metadata for Pi autocomplete
- `.pi/extensions/project-harness-feedback-loop/core.mjs` — deterministic parsing and report formatting
- `.pi/extensions/project-harness-feedback-loop/config.json` — project marker, requirement paths, checks, limits, and audit settings
- `.pi/extensions/project-harness-feedback-loop/prompts/task-compiler.md` — interface that makes the coding agent record an explicit task contract
- `.pi/extensions/project-harness-feedback-loop/prompts/auditor.md` — read-only evaluator instructions
- `.pi/extensions/project-harness-feedback-loop/evals/` — approved translation regression cases added after confirmed harness findings
- `docs/requirements.md` — stable requirement IDs pointing to canonical project guidance

Pi automatically loads `index.ts` from this project-local extension folder after project trust. The controller, not Pi itself, interprets the adjacent config, prompts, and evals. Merely storing prompts or evals consumes no model tokens. Tokens are used only when the controller sends selected content to an LLM.

## Verification

```powershell
node --test .pi/extensions/project-harness-feedback-loop/core.test.mjs
python -m pytest
```

After the project files are committed in a clean worktree, `/guarded` provides the real Pi boundary smoke path.
