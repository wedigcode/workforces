---
description: Aligns on wins, losses, what is next, and help needed. Records logs in workforces/team-sync/YYYY-MM-DD.md.
---

# /work sync — Team Sync & Goal Alignment

A structured checkpoint to establish goals, review progress, and highlight blockers. This connects day-to-day tasks back to strategic objectives.

**Agent:** `@project-manager` (see `agents/project-manager.md`)

---

## Usage

```
/work sync         → Aligns on wins, losses, next goals, and blockers. Logs to workforces/team-sync/
```

---

## Step 1 — Read State

Before initiating the sync, read:
1. **Backlog & Current Tasks** — `workforces/workstate.md` to see what is completed, active, or pending.
2. **Strategic Goals** — `workforces/goals/` (or path from `goals_dir` in `workrules.md`).
3. **GitHub Queue** — Check assignee issues and PRs (using the `github-project-planning` skill) to identify new external priorities.

---

## Step 2 — Review Past Cycle

Identify and summarize progress since the last sync:

### 🏆 Wins (Accomplishments)
- What tasks in `workforces/workstate.md` were moved to **Completed**?
- What milestones were achieved?

### ⚠️ Losses & Roadblocks
- What tasks are currently blocked or delayed?
- What tasks were skipped or removed, and why?
- Did any unexpected issues arise?

---

## Step 3 — Establish Next Goals

Determine focus for the upcoming cycle:

### 🎯 What is Next for Us?
- Identify the single most important task (**"The One Thing"**).
- Sequence the next active tasks from the backlog (`workforces/workstate.md`) based on dependencies and RICE/ICE scores.
- Ensure all new active tasks align directly with strategic goals.

---

## Step 4 — Surface Blockers & Help Needed

Call out items requiring human assistance:

### 🙋 Help Needed
- Clarification on requirements.
- API keys, credentials, or environment access.
- Code review, approvals, or feedback on artifacts.

---

## Step 5 — Present Sync Summary

Present a beautifully formatted summary in the chat and ask for approval:

```markdown
## 🔄 Team Sync — YYYY-MM-DD

### 🏆 Wins
- [x] Task A — Description of achievement.
- [x] Task B — Description of achievement.

### ⚠️ Losses & Roadblocks
- [ ] Task C — Delayed due to unexpected API change.
- [ ] Task D — Blocked by credential requirements.

### 🎯 What is Next
- **The One Thing:** Task E (Priority P0) — Reason it is critical.
- [ ] Task F (Priority P1) — Supporting task.

### 🙋 Help Needed
- Need AWS credentials for task D.
- Need confirmation on user flow design for task E.

---
Approve this sync summary? (I will log it to `workforces/team-sync/` and update the active tasks in `workforces/workstate.md`)
```

---

## Step 6 — Record & Update State

After the user approves:

1. **Create the Sync Log:** Save the approved summary as `workforces/team-sync/YYYY-MM-DD.md`. Create the directory if it does not exist.
2. **Update Work State:**
   - Update `workforces/workstate.md` with new statuses (e.g. marking unblocked tasks, updating notes, setting started dates for new active tasks).
