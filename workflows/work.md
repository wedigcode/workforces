---
description: Core workforce orchestrator — GitHub queue, active tasks, and planning in one command
---

# /work — Workforce Orchestrator

Your single command center. Scans your GitHub queue, surfaces the top task, and connects to planning when needed — all from `workforces/workstate.md`.

---

## Usage

```
/work              → Full run: GitHub queue + top task
/work sync         → Run standup sync: wins, losses, next goals, and blockers
/work plan         → Invoke @project-manager to generate + prioritize new work
/work status       → Show all active and pending tasks
/work done [#]     → Mark a task complete
/work skip [#]     → Skip a task (won't re-show)
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

## Step 2 — GitHub Queue

```bash
# Issues assigned to me
gh issue list --assignee @me --state open --limit 30

# PRs needing my review
gh pr list --search "review-requested:@me" --state open --limit 30

# My open PRs
gh pr list --author @me --state open --limit 30
```

Flag **stale issues** (>30 days) — recommend push forward, delegate, or close.

**Present as:**

```markdown
### 🔔 GitHub Queue

| Type | Repo | # | Title | Age | Action |
|------|------|---|-------|-----|--------|
| Issue | repo | #12 | Fix login bug | 3d | Review |

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

When the user picks a task (or accepts the recommendation):

1. Work on it directly or activate the appropriate skill/agent.
2. **Emergent Tasks & Ideas:** If new tasks, bugs, refactor needs, or feature ideas pop up during execution, immediately use the `github-project-planning` skill to create a new GitHub issue. Ensure it is populated with rich context (acceptance criteria, target files, etc.) so any agent can pick it up and complete it later.
3. Update `workforces/workstate.md` with results when done.

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

### `/work sync`

Invokes the `@project-manager` agent to run a sync/standup session. See [`workflows/sync.md`](./sync.md).

It reviews wins, losses, what's next, and blockers, then logs the session to `workforces/team-sync/YYYY-MM-DD.md`.

### `/work plan`

Invokes the `@project-manager` agent for a full planning run. See [`workflows/project-management.md`](./project-management.md).

This always includes GitHub issue creation — not just a workstate update.

### `/work status`

Show all tasks: active, pending, and completed.

### `/work done [#]`

1. Move task to Completed in workstate
2. Check if any task was blocked on this → unblock it
3. Show updated queue

### `/work skip [#]`

Set status to `skipped` — won't re-appear in the top task surface.
