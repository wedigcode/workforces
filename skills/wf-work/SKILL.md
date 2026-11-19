---
name: wf-work
description: Runs token-aware autonomous maintenance, cross-harness code review, ranked documentation discovery, and approved backlog execution sweeps on idle capacity or recurring cron schedules across single or configured multi-repo workspaces. Reach for this skill or trigger it when dispatching background worker passes across codereview, docs discovery and OKF/docblock authoring, security audits, UX polish, performance tuning, rolling one-slice-per-day refactoring, or dependency housekeeping with PM inbox caps, multi-repo disambiguation, and claim locks.
---
# Skill: /wf-work — Token-Aware Autonomous Worker & Cross-Harness Queue Dispatcher

Dispatches recurring or on-demand background work across Antigravity, Claude Code, and Grok with atomic task claims, cross-harness code review priority, ranked documentation recommendations (OKF architecture cards + inline docblocks), multi-repo disambiguation, stateless 1-bite-per-day rolling refactoring, and PM discovery check-in controls.

---

## Subcommands & Modes

| Invocation | Priority / Guardrail | Behavior |
|---|---|---|
| `/wf-work` *(auto)* | P0 Review -> P1 Approved -> P2 Discovery | Claims highest-priority available work for the current harness. |
| `/wf-work codereview` | Always active (ignores discovery pause) | Picks up items/PRs with `authored_by_harness != current_harness` in `requires_code_review` and runs macro + Clean Coder review. |
| `/wf-work docs [--repo <name\|all>]` | Respects PM pause + inbox cap | Syncs `<repo>/docs/index.md`, ranks undocumented/stale modules by blast radius & inline docblock coverage, audits stray root files & bulky specs, and logs `type: docs` recommendations into `workforces/issues/inbox/` for PM promotion. |
| `/wf-work security [--repo <name\|all>]` | Read-only discovery -> `issues/inbox/` | Audits exposed secrets, missing auth checks, `"production"` defaults, IaC parity, and dependency CVEs. |
| `/wf-work design` *(alias: `ux`)* | Read-only discovery -> `issues/inbox/` | Audits frontend UI consistency, a11y gaps, responsive regressions, and design anti-patterns. |
| `/wf-work optimization` *(alias: `perf`)* | Read-only discovery -> `issues/inbox/` | Profiles hotspots, N+1 queries, sequential async bottlenecks, and algorithmic complexity. |
| `/wf-work debt` *(aliases: `todo`, `refactor`)* | Read-only discovery -> `issues/inbox/` | Harvests `TODO`/`FIXME` clusters and proposes bounded `rolling_slice` 1-bite/day tasks on large files. |
| `/wf-work housekeeping` *(alias: `deps`)* | Read-only discovery -> `issues/inbox/` | Checks dependency/runtime drift, dead scripts, and config inconsistencies. |
| `/wf-work status` | Instant check | Reports current harness, discovery kill-switch, inbox count vs cap, and active multi-harness claims. |
| `/wf-work pause [reason]` | PM check-in control | Sets `issue_discovery: paused` in `workforces/config.json` (code review & approved queue keep running). |
| `/wf-work resume` | PM check-in control | Sets `issue_discovery: active` so discovery sweeps resume. |

---

## Multi-Repo & Sibling-Repo Disambiguation (`--repo`)

`/wf-work` resolves configured repositories from `workforces/config.json`, `workforces/workrules.md` (`tracked_repos`), `workforces/workstate.md`, and `workforces/projects/*.md` (including sibling `../<repo>` clones). It never scans unconfigured directories.
- **Single repository**: Runs directly on that repository.
- **Multiple repositories configured & `--repo` omitted**: `work_dispatch.py` returns `action: "needs_repo_selection"` with `available_repos` without modifying files. **Ask the user** which repository to target, or whether to run across `all`.
- **Explicit target**: Pass `--repo <name|slug|path>` for one repository, or `--repo all` to run across all configured/sibling repositories (logging `[<repo>]`-tagged inbox items under the shared inbox cap).

---

## Execution Protocol

### Step 1: Run Dispatcher Gate & Claim Queue
```bash
python3 .agents/skills/wf-work/scripts/work_dispatch.py auto --root ./ --json
```
*(Fallback: `python3 skills/wf-work/scripts/work_dispatch.py auto --root ./ --json`)*

For dedicated cron schedules or repo-scoped runs:
- **15-min Cross-Harness Review Cron**:
  ```bash
  python3 .agents/skills/wf-work/scripts/work_dispatch.py codereview --root ./ --json
  ```
- **Hourly / Window-Aware Docs Discovery Sweep**:
  ```bash
  python3 .agents/skills/wf-work/scripts/work_dispatch.py docs --root ./ --repo all --window-remaining-minutes 60
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
   - **Promoted `type: docs` Tasks**:
     - Work in an isolated `docs/<module>` branch/worktree inside the task's `repo` (if set).
     - Follow `wf-doc-generator`: author/enrich `<repo>/docs/architecture/<module>.md` (`doc_status: documented`, refactor-ready OKF schema + `last_verified_commit`) and refresh `docs/index.md` via `scaffold_repo_okf.py --scan`.
     - Add concise 2–4 line module/class boundary docblocks, public docstrings, and brief inline *"why"* comments to undocumented symbols in that module's source files.
     - Run `post_code_reviewer.py --run-checks --strict`, push feature branch, open a **Draft PR**, and hand off via `--request-review`.
   - **Promoted `refactor` / `debt` / Feature Tasks**:
     - Create an isolated branch/worktree (`feat/...`, `fix/...`, `refactor/...`).
     - Read matching `<repo>/docs/architecture/*.md` cards and run `pre_impact_analyzer.py --file <target>` before modifying code.
     - If `cadence == rolling_slice`, extract **only 1–3 small helper blocks** (strictly <= 1 slice per file per day), keeping diffs easy to verify.
     - Keep matching `docs/architecture/*.md` (`affected_files`, `Constraints, Invariants & Gotchas`, `last_verified_commit`) synchronized with code changes.
     - Run `post_code_reviewer.py --run-checks --strict`, push feature branch, open a **Draft PR**, and hand off to another harness:
       ```bash
       python3 .agents/skills/wf-task-tracker/scripts/report-task.py --update "<task_path>" --request-review --pr "<pr_url>"
       ```
3. **Read-Only Discovery Sweeps (`docs`, `security`, `design`, `optimization`, `debt`, `housekeeping`)**:
   - **Never** open unsolicited feature PRs or rewrite source files during discovery sweeps. Log deduplicated findings and doc recommendations into `workforces/issues/inbox/` via `report-issue.py` so `@wf-project-manager` triages and promotes them (`--promote-issue ... --approve`) before authoring starts.
   - Default `docs` discovery only refreshes `<repo>/docs/index.md` / starter scaffold structure non-destructively and recommends ranked modules for PM approval.

---

## Multi-Harness Concurrency & Lease Invariants
- Atomic OS lockfile (`workforces/tasks/.claim.lock`) prevents duplicate claims across concurrent Antigravity, Claude Code, and Grok workers.
- Stale leases expire after 90 minutes (`report-task.py --reclaim-stale`).
- Rolling refactors enforce a stateless **1-bite-per-day** invariant (`last_slice_date != today` and no open/in-progress/review slice on the same `file`).
- Hard Consent Gate (`Option A`) remains enforced at all times: Draft PRs only, zero unapproved merges or cloud deploys.
