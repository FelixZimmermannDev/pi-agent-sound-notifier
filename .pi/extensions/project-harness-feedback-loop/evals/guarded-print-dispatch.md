# Guarded print-mode dispatch regression

- **Original gap:** An extension command called `pi.sendUserMessage()` and returned. Interactive Pi remained alive, but one-shot print/JSON mode exited before the queued coding turn, leaving only the initial harness snapshot.
- **Representative input:** `/guarded Add one focused regression test without refactoring.`
- **Required behavior:** The input hook starts the guarded run, transforms the slash input into the original implementation request, and lets Pi's normal prompt lifecycle await the coding turn and subsequent evaluator.
- **Regression evidence:** A one-shot `pi --mode json -p` smoke run must contain assistant/tool events and produce `task-contract.json`, `changes.patch`, `checks.json`, and `audit.json`.
- **Protected interface rule:** A user-facing harness entrypoint must work in interactive and non-interactive Pi modes; do not enqueue its primary task from a command handler that the one-shot runner can finish before delivery.
