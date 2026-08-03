# Guarded task contract

This instruction applies only to the active project-local `/guarded` task.

Before changing files:

1. Read the original user request.
2. Read the requirement files named below and only the directly relevant code and tests.
3. Resolve low-risk details using the project rules. If a material product, safety, or architecture conflict remains, stop and ask the user instead of inventing a decision.
4. Call `record_task_contract` exactly once before using `edit` or `write`.

The contract must be concrete and proportional. It must state:

- the goal and bounded scope;
- observable completion conditions;
- behavior and state that must remain unchanged;
- relevant requirement IDs with source paths and a short reason;
- verification commands or real-boundary checks;
- assumptions that affect the implementation.

Do not copy every project rule into every contract. Select the rules that materially constrain this task, while always retaining applicable safety invariants and Definition of Done requirements. Do not commit, amend, stash, reset, or switch branches during the guarded task.

After recording the contract, implement the complete task normally, run focused checks, and report verification accurately.
