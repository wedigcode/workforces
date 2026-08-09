---
trigger: always_on
---

# Workforces Base Rules

These rules apply to all workforces and projects. They are enforced by the AI agents at all times.

---

## GitHub Rules & Repository Scoping

- **Strict Workforce Repo Scoping**: All GitHub issue/PR queries, PR code reviews, and Google Jules (`@google/jules`) session reviews MUST filter strictly for the active target repository or repos explicitly configured in `workforces/workrules.md` / `workstate.md`. Ignore any PRs or Jules sessions from unrelated personal repos outside the active workforce scope.
- **Jules Active Session Status Filter**: When scanning for active Jules code review tasks, filter strictly for sessions where `Status != 'Completed'` (e.g. `In Progress`, `""` [empty string/pending], `Needs Review`). Archived/completed sessions are excluded from active work queues.
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

## Discovered Gap & Decision Escalation Protocol

During execution (whether in standard mode or auto-coordinator mode):

1. **Continuous Gap & Risk Detection:**
   - As tasks execute, if an overlooked dependency, missing asset (e.g. missing branding guidelines, missing DB schema, unhandled auth flow break), or breaking risk is discovered:
   - Log the gap immediately in `workforces/workstate.md` under `## Unforeseen Risks & Discovered Gaps`.

2. **Threshold Assessment (Minor vs. Major):**
   - **Minor / Scope-Enclosed Issue:** (e.g. creating a missing helper file, adding a missing utility method, or extending an internal interface without breaking changes)
     -> Auto-fix or auto-generate the missing dependency, log it in `workforces/workstate.md`, and continue execution.
   - **Major / Architectural / User Decision Issue:** (e.g. auth flow break requiring OAuth integration instead of simple link, major DB schema change, missing core brand strategy choices, breaking API changes)
     -> **STOP EXECUTION IMMEDIATELY.**
     -> Formulate clear decision options with trade-offs.
     -> Present the decision to the user (via interactive question tool or structured prompt) and wait for user direction before proceeding.

## Rule Cascading

- A parent workforce can read all child `workforces/README.md` files to get context.
- A project should NOT need to know about other projects. Keep context scoped.
