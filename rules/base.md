---
trigger: always_on
---

# Workforces Base Rules

These rules apply to all workforces and projects. They are enforced by the AI agents at all times.

---

## GitHub Rules & Multi-Repository Scoping

- **Strict Workforce Multi-Repo Scoping**: All GitHub issue/PR queries, PR code reviews, and Google Jules (`@google/jules`) session reviews MUST iterate across all repositories configured in `workforces/workrules.md` / `workstate.md` under `tracked_repos` (passing `--repo <owner/repo>` to `gh`). Ignore any PRs or Jules sessions from unrelated personal repos outside the active workforce scope.
- **Automated Remote GitHub Reconciliation**: During standups (`/wf-sync`), personal syncs (`/wf-sync --me`), or task operations, the system automatically checks linked PRs/issues on GitHub. When a remote PR is merged or closed, the corresponding local task in `workforces/tasks/` is automatically transitioned to `done` and synced to `workforces/workstate.md`.
- **Single Source of Truth Task Architecture**: `workforces/tasks/*.md` is the authoritative single source of truth for all tasks, decisions, priorities, and lineage. `workforces/workstate.md` is a projected dashboard view dynamically maintained in parity by `report-task.py` and `personal_sync.py`.
- **Jules Active Session Status Filter**: When scanning for active Jules code review tasks, filter strictly for sessions where `Status != 'Completed'` (e.g. `In Progress`, `""` [empty string/pending], `Needs Review`). Archived/completed sessions are excluded from active work queues.
- **All new GitHub repositories MUST be created as private** unless the user explicitly requests a public repo.
- Assigned issues and PRs are discovered by reading `workforces/workrules.md` (and the `workstate.md` tracker).
- Unassigned issues in configured repos should be surfaced as potential work items.
- Tasks should be saved as GitHub issues in the correct project repo for tracking.

## Repo Type Hierarchy

- **Workforce** – Central command. Can spawn sub-workforces or projects.
- **Project** – A specific initiative with its own repo and issue tracking.

## Coordinator & Auto-Delegation Protocol

- **Auto-Execution Mode**: When `--auto` or `--all` is passed in `/wf-work`, `/wf-feature`, `/wf-plan`, or when `auto_delegate: true` is configured in `workforces/workrules.md`, the primary chat MUST operate as an autonomous **Coordinator**.
- **No Manual Step-by-Step Handoffs**: When in auto-execution mode, the Coordinator MUST NOT stop between tasks to ask the user "Should I do task 2 now?" or require the user to copy-paste prompts.
- **Execution Topology Selection Protocol (`agent-parallelization`)**:
  Before delegating coding tasks, the Coordinator MUST evaluate task dependencies and explicitly declare the execution topology:
  1. **Horizontal Fan-Out (Parallel Worktrees)**: Used for 2+ independent issues or bugs. The Coordinator MUST spawn subagents with `Workspace: 'share'` (Git worktree isolation in `.worktrees/<slug>`). **NEVER run concurrent coding subagents in `Workspace: 'inherit'`** to eliminate `.git/index.lock` contention and filesystem crosstalk.
  2. **Vertical Relay (Linear Stack via `gh stack`)**: Used for single epics with layered dependencies (Schema ➔ API ➔ UI). Agents execute sequentially in a relay using `gh stack init` and `gh stack add`, concluding with `gh stack submit` for stacked PR review.
  3. **Direct Single-Branch**: Used for localized atomic fixes (<1h, <5 files).
- **Task Loop Execution**:
  1. Parse the task list/breakdown (from `workforces/tasks/`, `workstate.md`, plan, or PRD).
  2. Classify tasks into the optimal execution topology.
  3. Execute independent tasks concurrently via isolated worktrees (`Workspace: 'share'`) or sequential stack relays.
  4. Validate implementation (compile, run tests, check linters).
  5. Mark completed in `workforces/tasks/` and `workforces/workstate.md` and unblock dependent tasks.
  6. Output a **Developer Inspection Card** for each finished branch (`cd .worktrees/<slug> && npm test`, `PORT=3001 npm run dev`).
  7. Loop to the next unblocked task until all tasks are complete.
  8. Present a final consolidated **Execution Summary Report**.

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

## Implementation Plan & Pre-Plan Codebase Audit Protocol

- **Mandatory Existing Codebase Audit Section**: Every `implementation_plan.md` artifact generated by workforce agents MUST include a dedicated section titled `## Existing Codebase Audit Findings`.
- **Pre-Plan Research Enforcement**: Symbol discovery (`code-graph`) and codebase searches (`grep_search`, `list_dir`) MUST execute *before* drafting the implementation plan.
- **Audit Disclosure Requirements**: The audit section MUST explicitly list:
  1. Searched files, tables, and directories (`grep_search`, `code-graph`, `list_dir`).
  2. Pre-existing entities, tables, legacy utilities, or methods related to the feature.
  3. Clear distinction between **what already exists** and **what is missing**.

## Factual Telemetry vs. Hypothesis Tracking Protocol

- **Strict Factual Grounding**: Domain subagents (especially `@sales`, `@marketer`, `@growth`) must NEVER fabricate customer quotes, conversion metrics, or historical demand out of thin air.
- **Pre-Outreach Baseline Reporting**: If no customer calls, email cadences, or marketing outreach have been executed yet, agents MUST state the factual baseline explicitly (e.g. *"0 customer discovery calls conducted to date; pre-launch stage"*).
- **Hypothesis Conversion**: Untested buyer assumptions, pricing theories, or speculative feature requests MUST NOT be presented as factual telemetry. Instead, they must be formulated as structured **Hypotheses** in `workforces/hypotheses/` with leading/lagging metrics, kill thresholds, and a notes/findings log as evidence is gathered.

## Autonomous AI Execution with Human Gatekeeping Protocol

- **End-to-End AI Autonomy**: AI subagents handle multi-step workflows, asset generation, research, code implementation, and multi-pass self-critiques autonomously without requiring intermediate manual human steps.
- **Human Gatekeeper Role**: Humans are brought in for high-level governance, strategic approvals ("yes/no/pivot"), budget authorization, and subjective design taste. Agents present clean, synthesized proposals ready for one-click human approval rather than dumping raw toil onto the human.

## Strategic Decision Sequence Protocol

Whenever conducting product discovery, evaluating feature proposals, formulating marketing positioning, or leading strategic reviews (`/wf-sync --strategy`), workforce agents MUST apply the **4-Step Executive Decision Sequence**:

1. **JTBD & Customer Validation**: State the specific Job-to-be-Done (Functional, Emotional, Social) and situational trigger. Reject solutions lacking causal triggers.
2. **Value Stick Audit**: Evaluate whether the proposal increases Willingness to Pay (WTP) or lowers Willingness to Sell (WTS). Ensure the proposal lengthens total value rather than playing a zero-sum game with margins.
3. **Growth Loop & Platform Dynamics**: Map how the initiative feeds back into a closed growth loop (viral, UGC, paid reinvestment, or marketplace supply/demand) and identify direct/indirect network effects.
4. **Unit Economics & Execution**: Evaluate impact on CAC, LTV ($\text{LTV:CAC} \ge 3\times$), CAC Payback ($< 12\text{mo}$), and Gross Margin. Run a **Sense-Seize-Transform** checklist to assign cross-functional execution ownership.

## Rule Cascading

- A parent workforce can read all child `workforces/README.md` files to get context.
- A project should NOT need to know about other projects. Keep context scoped.

## Response Usage Reporting Protocol

- If `workforces/tmp/turn-summary.txt` (or session-scoped `workforces/tmp/turn-summary-<conversation_id>.txt`) exists at the end of a turn, read its content and append the `📊 WORKFORCES TURN SUMMARY` block to your final markdown response.



