---
description: Core workforce orchestrator — GitHub queue, active tasks, and planning in one command
---

# /work — Workforce Orchestrator

Your single command center. Scans your GitHub queue, surfaces the top task, and connects to planning when needed — all from `workforces/workstate.md`.

---

## Usage

```
/work                    → Full run: GitHub queue + issue inbox + top task
/work --auto (or --all)  → Auto-coordinator mode: execute all active/pending tasks end-to-end
/work site-setup         → Greenfield site setup & Product Brief pipeline (delegates to /site-setup)
/work feature [idea]     → Start feature research & PRD pipeline (delegates to /feature)
/work feature [idea] --auto → Research, plan, and automatically execute all tasks end-to-end
/work plan [goal]        → Create execution plan & estimates (delegates to /plan)
/work plan --from-prd    → Convert recent PRD into execution plan & estimates
/work investigate [svc]  → Incident triage & postmortem (delegates to /investigate)
/work improve [pillar]   → Audit & continuous improvement across cleanup, performance, security, health, testing (delegates to /work improve)
/work sync               → Run standup sync: wins, losses, next goals, and blockers
/work status             → Show all active and pending tasks
/work done [#]           → Mark a task complete (unblocks dependent tasks)
/work skip [#]           → Skip a task (won't re-show)
```

---

## First Run — Setup

On first run (no `workforces/workstate.md` exists), ask:

1. **GitHub usernames** — who to scan issues/PRs for (default: `@me`)
2. **Ignored repos** — any repos to skip

Write to `workforces/workrules.md`:

```markdown
# Work Rules

## Config
github_usernames: @me
ignored_repos:
goals_dir: workforces/goals/
```

Create `workforces/workstate.md` with empty scaffolding (see [State Management](#state-management)).

---

## Step 1 — Read State

1. Read `workforces/workrules.md` — source of truth for:
   - `github_usernames` — who to scan
   - `ignored_repos` — repos to skip
   - `goals_dir` — where goals live
2. Read `workforces/workstate.md` — active and pending tasks
   - If missing → run Setup, then create it

---

## Step 2 — GitHub Queue & Issue Inbox

### 2a — Issue Inbox

Before querying GitHub, check the local issue inbox:

```bash
ls workforces/issues/inbox/*.md 2>/dev/null | wc -l
```

If the inbox has **1 or more** files, surface a prompt:

```markdown
### 📬 Issue Inbox — N items pending triage

| File | Title | Type | Severity | Reporter | Age |
|------|-------|------|----------|---------|-----|
| 20260813-... | Dead code in utils.py | debt | P2 | programmer | 2h |


💡 Run `/task triage` to let the Project Manager review these.
```

If the inbox is empty, skip this block.

### 2b — GitHub Queue & Async Worker Monitoring

```bash
# Issues assigned to me
gh issue list --assignee @me --state open --limit 30

# PRs needing my review
gh pr list --search "review-requested:@me" --state open --limit 30

# My open PRs
gh pr list --author @me --state open --limit 30

# Google Jules active sessions & scheduled tasks (if jules CLI is installed)
jules remote list --session
```

- **Async Worker Handoffs:** Scan `workforces/workstate.md` for tasks marked `delegated` or `async-pending` (e.g. delegated to Jules or external automation). If a Jules session or PR is `Completed` or `Needs Review`, surface the patch immediately to unblock downstream dependencies.
- **GitHub Label Taxonomy:**
  - `tool:<tool_name>` — e.g. `tool:jules`, `tool:google-stitch`, `tool:google-vids`
  - `delegated:<target>` — e.g. `delegated:jules`, `delegated:copilot`
  - `status:async-pending` / `status:needs-review`
  - `type:hypothesis` — for scientific experiments tracked via `hypothesis-tracker`
- Flag **stale issues** (>30 days) — recommend push forward, delegate, or close.

**Present as:**

```markdown
### 🔔 GitHub Queue & Async Workers

| Type | Repo | # / Session | Title | Age / Status | Action |
|------|------|---|-------|-----|--------|
| Issue | repo | #12 | Fix login bug | 3d | Review |
| Jules | repo | 891234 | Auth token cache refactor | Completed | Review & merge patch |

**Stale (>30 days):**
- [ ] #8 — Title (42d) → Close or delegate?

_Queue clear_ → ✅
```

---

## Step 3 — Surface Top Task

Present the highest-priority task from `workforces/workstate.md`:

```markdown
## 📋 /work

### 🔔 GitHub Queue
| Type | Repo | # | Title | Age |
|------|------|---|-------|-----|
| PR (review) | repo | #456 | Fix auth | 🔴 8d |

### 📌 Active Tasks
| # | Task | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 1 | Build landing page | P0 | in-progress | 2/3 done |
| 2 | Write welcome email | P1 | pending | Waiting on #1 |

### 🎯 Recommended Next
> **Build landing page** — P0
> _Reason: Highest priority active task. 2 tasks blocked until this ships._

---
`/work sync` · `/work plan` · `/work status` · `/work done 1`
```

---

## Step 4 — Execute

### Standard Mode
When the user picks a single task (or accepts the top recommendation):
1. Work on it directly or activate the appropriate skill/agent.
2. **Emergent Tasks & Ideas:** If new tasks, bugs, refactor needs, or feature ideas pop up during execution, immediately use the `github-project-planning` skill to create a new GitHub issue with rich context.
3. Update `workforces/workstate.md` with results when done.

### Auto-Execution / Coordinator Mode (`--auto` or `--all` or `auto_delegate: true`)
When invoked with `--auto`/`--all` or when `auto_delegate: true` is configured in `workrules.md`:
1. **Act as Coordinator**: Do not pause between individual tasks to prompt the user or require manual command entry.
2. **Task Loop**:
   - Select all active/pending tasks from `workforces/workstate.md` whose dependencies are met.
   - For independent tasks, execute sequentially or in parallel using background sub-processes / subagents.
   - Validate implementation (run tests/builds).
   - Mark task `completed` in `workforces/workstate.md`, which unblocks dependent tasks.
   - Automatically move to the next unblocked task.
3. **Completion**: Provide a consolidated summary of all completed work across the entire queue once finished.

---

## State Management

### `workforces/workstate.md` Format

```markdown
# Work State

## Active Tasks
| # | Task | Priority | Score | Status | Issue | Started | Notes |
|---|------|----------|-------|--------|-------|---------|-------|
| 1 | Build landing page | P0 | RICE: 850 | in-progress | #12 | 2026-07-15 | 2/3 done |
| 2 | Write welcome email | P1 | RICE: 580 | pending | — | — | Waiting on #1 |

## Completed
| Task | Priority | Issue | Completed | Notes |
|------|----------|-------|-----------|-------|
| Set up repo | P0 | #1 | 2026-07-14 | |
```

---

## Subcommands

### `/task [subcommand]`

Report deferred issues, bugs, design problems, and ideas. Invokes the `project-manager` subagent for triage.
See [`workflows/task.md`](./task.md) for the full command reference.

```
/task                  → Show inbox summary
/task report           → Guided issue reporting
/task triage           → PM triages all pending inbox items
/task list             → Browse all issues
```

---

### `/work site-setup`

Triggers the greenfield site setup and Product Brief pipeline. See [`workflows/site-setup.md`](./site-setup.md).

Coordinates multi-team handoffs across `@project-manager`, Marketing (`@marketer`), Design (`@designer` — inspiration, layout specs, tokens), Compliance (`@compliance`), and Engineering (`@programmer` — tech stack scaffolding under installer safeguard rules and language-specific AI protocol generation).


### `/work feature [idea]`

Triggers the research & specification pipeline. See [`workflows/feature.md`](./feature.md).


Runs gap analysis, produces feature brief & PRD, breaks down tasks, and optionally hands off to `/plan --from-prd`.

### `/work plan [goal]`

Triggers execution planning & estimation. See [`workflows/plan.md`](./plan.md).

Breaks down goals or PRDs into deployable phases, time estimates, dependency maps, and risk assessments. Supports `--push-to-work` to automatically populate `workforces/workstate.md` and create GitHub issues via [`workflows/project-management.md`](./project-management.md).

### `/work sync`

Runs a structured team sync or strategic review session. See [`workflows/sync.md`](./sync.md).

- `/work sync` or `/work sync --daily` — 5-minute tactical standup led by `@project-manager` (24h wins, roadblocks, The One Thing, inbox triage).
- `/work sync --strategy` — Deep strategic review led by `@advisor` (OKR pacing, SME round-table, hypothesis telemetry, kill/pivot thresholds, and 5-dimension diagnostics).
- `/work sync --goals` — Interactive goal scaffolding led by `@advisor` and `@project-manager` (North Star, Q1–Q4 OKRs, monthly milestones).
- `/work sync --me` — Personal standup & follow-up radar led by `@project-manager` (git state, active tasks, follow-ups required from you vs waiting on others, emails, chats, meetings & prep, notes).
Logs sessions to `workforces/team-sync/YYYY-MM-DD.md` (or `YYYY-MM-DD-me.md`).

### `/work investigate [service]`

Triggers incident triage and root-cause classification. See [`workflows/investigate.md`](./investigate.md).

Streams log output to workspace scratch space (`workforces/tmp/`), classifies root cause, generates incident postmortem, and optionally pushes P0/P1 fixes directly into `/plan` or `workforces/workstate.md`.

### `/work status`

Show all tasks: active, pending, and completed.

### `/work done [#]`

1. Move task to Completed in workstate
2. Check if any task was blocked on this → unblock it
3. Show updated queue

### `/work skip [#]`

Set status to `skipped` — won't re-appear in the top task surface.
