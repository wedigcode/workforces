---
name: wf-work
description: Runs token-aware autonomous maintenance, cross-harness code review, and approved backlog execution sweeps on idle capacity or recurring cron schedules. Reach for this skill or trigger it when dispatching scheduled background worker passes across codereview, docs architecture scaffolding, security audits, UX polish, performance tuning, rolling one-slice-per-day refactoring, or dependency housekeeping with PM inbox caps and claim locks.
---
# Skill: /wf-work — Token-Aware Autonomous Worker & Cross-Harness Queue Dispatcher

Dispatches recurring or on-demand background work across Antigravity, Claude Code, and Grok with atomic task claims, cross-harness code review priority, stateless 1-bite-per-day rolling refactoring, and PM discovery check-in controls.

---

## Subcommands & Modes

| Invocation | Priority / Guardrail | Behavior |
|---|---|---|
| `/wf-work` *(auto)* | P0 Review -> P1 Approved -> P2 Discovery | Claims highest-priority available work for the current harness. |
| `/wf-work codereview` | Always active (ignores discovery pause) | Picks up items/PRs with `authored_by_harness != current_harness` in `requires_code_review` and runs macro + Clean Coder review. |
| `/wf-work docs` | Respects PM pause + inbox cap | Audits stray root files, bulky specs needing dehydration, and scaffolds/updates `<repo>/docs/` OKF cards. |
| `/wf-work security` | Read-only discovery -> `issues/inbox/` | Audits exposed secrets, missing auth checks, `"production"` defaults, IaC parity, and dependency CVEs. |
| `/wf-work design` *(alias: `ux`)* | Read-only discovery -> `issues/inbox/` | Audits frontend UI consistency, a11y gaps, responsive regressions, and design anti-patterns. |
| `/wf-work optimization` *(alias: `perf`)* | Read-only discovery -> `issues/inbox/` | Profiles hotspots, N+1 queries, sequential async bottlenecks, and algorithmic complexity. |
| `/wf-work debt` *(aliases: `todo`, `refactor`)* | Read-only discovery -> `issues/inbox/` | Harvests `TODO`/`FIXME` clusters and proposes bounded `rolling_slice` 1-bite/day tasks on large files. |
| `/wf-work housekeeping` *(alias: `deps`)* | Read-only discovery -> `issues/inbox/` | Checks dependency/runtime drift, dead scripts, and config inconsistencies. |
| `/wf-work status` | Instant check | Reports current harness, discovery kill-switch, inbox count vs cap, and active multi-harness claims. |
| `/wf-work pause [reason]` | PM check-in control | Sets `issue_discovery: paused` in `workforces/config.json` (code review & approved queue keep running). |
| `/wf-work resume` | PM check-in control | Sets `issue_discovery: active` so discovery sweeps resume. |

---

## Execution Protocol

### Step 1: Run Dispatcher Gate & Claim Queue
```bash
python3 .agents/skills/wf-work/scripts/work_dispatch.py auto --root ./ --json
```
*(Fallback: `python3 skills/wf-work/scripts/work_dispatch.py auto --root ./ --json`)*

For dedicated cron schedules:
- **15-min Cross-Harness Review Cron**:
  ```bash
  python3 .agents/skills/wf-work/scripts/work_dispatch.py codereview --root ./ --json
  ```
- **Hourly / Window-Aware Discovery Sweep** (e.g. light usage / 1h remaining):
  ```bash
  python3 .agents/skills/wf-work/scripts/work_dispatch.py docs --root ./ --window-remaining-minutes 60
  ```
- **Pause / Check-in**:
  ```bash
  python3 .agents/skills/wf-work/scripts/work_dispatch.py pause --reason "Triaging existing inbox items" --root ./
  ```

### Step 2: Execute Claimed Work Safely
1. **Cross-Harness Code Review (`codereview`)**:
   - Inspect `<repo>/docs/index.md` + `docs/architecture/*.md` (`affected_files`) alongside Clean Coder checks (`wf-pr-review`).
   - Verify no `"prod"`/`"production"` defaults, verified IaC/SAM env parity, no bypass of existing dispatchers/subscribers, and portable Git links only.
   - Record verdict cleanly (moves task to `ready_for_human` or `todo` with `changes_requested`; **NEVER** calls `gh pr merge` or pushes live):
     ```bash
     python3 .agents/skills/wf-task-tracker/scripts/report-task.py --update "<task_path>" --complete-review approved --review-notes "..."
     ```
2. **Approved Queue Execution (`execute_approved_task`)**:
   - Create an isolated branch/worktree (`feat/...`, `fix/...`, `refactor/...`).
   - If `cadence == rolling_slice`, extract **only 1–3 small helper blocks** (strictly <= 1 slice per file per day), keeping diffs easy to verify.
   - Run `post_code_reviewer.py --run-checks --strict`, push feature branch, open a **Draft PR**, and hand off to another harness:
     ```bash
     python3 .agents/skills/wf-task-tracker/scripts/report-task.py --update "<task_path>" --request-review --pr "<pr_url>"
     ```
3. **Read-Only Discovery Sweeps (`docs`, `security`, `design`, `optimization`, `debt`, `housekeeping`)**:
   - **Never** open unsolicited feature PRs for discovered security/perf/design/debt/housekeeping issues. Log deduplicated findings into `workforces/issues/inbox/` via `report-issue.py` so `@wf-project-manager` triages and prioritizes them before coding starts.
   - Only `docs` sweeps on explicit branch/PR approval or local non-destructive architecture scaffolding update `<repo>/docs/`.

---

## Multi-Harness Concurrency & Lease Invariants
- Atomic OS lockfile (`workforces/tasks/.claim.lock`) prevents duplicate claims across concurrent Antigravity, Claude Code, and Grok workers.
- Stale leases expire after 90 minutes (`report-task.py --reclaim-stale`).
- Rolling refactors enforce a stateless **1-bite-per-day** invariant (`last_slice_date != today` and no open/in-progress/review slice on the same `file`).
- Hard Consent Gate (`Option A`) remains enforced at all times: Draft PRs only, zero unapproved merges or cloud deploys.
