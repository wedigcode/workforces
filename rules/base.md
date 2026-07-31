---
trigger: always_on
---

# Workforces Base Rules

These rules apply to all workforces and projects. They are enforced by the AI agents at all times.

---

## GitHub Rules

- **All new GitHub repositories MUST be created as private** unless the user explicitly requests a public repo.
- Assigned issues and PRs are discovered by reading `workforces/workrules.md` (and the `workstate.md` tracker).
- Unassigned issues in configured repos should be surfaced as potential work items.
- Tasks should be saved as GitHub issues in the correct project repo for tracking.

## Repo Type Hierarchy

- **Workforce** – Central command. Can spawn sub-workforces or projects.
- **Project** – A specific initiative with its own repo and issue tracking.

## Coordinator & Auto-Delegation Protocol

- **Auto-Execution Mode**: When `--auto` or `--all` is passed in `/work`, `/feature`, `/plan`, or when `auto_delegate: true` is configured in `workforces/workrules.md`, the primary chat MUST operate as an autonomous **Coordinator**.
- **No Manual Step-by-Step Handoffs**: When in auto-execution mode, the Coordinator MUST NOT stop between tasks to ask the user "Should I do task 2 now?" or require the user to copy-paste prompts.
- **Task Loop Execution**:
  1. Parse the task list/breakdown (from `workstate.md`, plan, or PRD).
  2. Identify independent/unblocked tasks and execute them sequentially or via parallel sub-processes (`run_command` async or subagents).
  3. Validate implementation (compile, run tests, check linters).
  4. Mark completed in `workforces/workstate.md` and unblock dependent tasks.
  5. Loop to the next unblocked task until all tasks are complete.
  6. Present a final consolidated **Execution Summary Report**.

## Rule Cascading

- A parent workforce can read all child `workforces/README.md` files to get context.
- A project should NOT need to know about other projects. Keep context scoped.

