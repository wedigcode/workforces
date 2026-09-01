---
description: Strategic planning workflow — invokes @project-manager to generate, prioritize, and sync work to GitHub
---

# /wf-project-management — Task Generation & Issue Creation Pipeline

Invoked by `/wf-work plan` or `/wf-project-management`. Runs a full planning cycle: reads goals and state, performs gap analysis, generates and scores new tasks, then creates GitHub Issues for P0/P1 work.

**Agent:** `@project-manager` (see `agents/project-manager.md`)

---

## Step 0 — Load Config

Read `workforces/memory/github-project-planning-skill.md`.

- **Missing or empty** → pause and tell the user:
  > _"GitHub project not configured. The `github-project-planning` skill needs to run setup before planning can create issues."_
  Then trigger the skill's setup flow.
- **Present** → extract `owner`, `owner_type`, project `id`, `tracked_repos`, and all field IDs. Continue.

---

## Step 1 — Read the Landscape

Before generating any work, read:

1. **Goals** — current quarter objectives from `workforces/goals/` (or `goals_dir` from `workrules.md`)
2. **State** — `workforces/workstate.md` for active, pending, and completed tasks
3. **GitHub board** — query live roadmap via `github-project-planning` skill to see what's already tracked

---

## Step 2 — Gap Analysis

Compare goals vs. current backlog. For each key result, identify:
- Is there active work covering it?
- What's missing?

```markdown
### 🔍 Gap Analysis — YYYY-MM-DD

| Goal / KR | Target | Current | Gap | Status |
|-----------|--------|---------|-----|--------|
| Launch product | 1 | 0 | -1 | 🔴 Off Track |

### What's Missing From the Backlog?
1. No tasks for KR2 — need X
```

---

## Step 3 — Generate + Score Tasks

For each gap, generate concrete tasks scored with RICE or ICE:

| # | Task | Priority | Score | Depends On |
|---|------|----------|-------|-----------|
| 1 | {task} | P0 | RICE: 850 | — |
| 2 | {task} | P1 | RICE: 620 | #1 |

**RICE** for strategic/revenue tasks: `(Reach × Impact × Confidence) ÷ Effort`  
**ICE** for tactical tasks: `Impact × Confidence × Ease` (each 1–10)

Always show scoring. No black-box prioritization.

**Present the full plan and ask for approval before writing anything.**

---

## Step 4 — Update `workforces/workstate.md`

After approval:

1. Add new tasks to Active Tasks table
2. Re-order by priority score
3. Add dependency notes
4. Leave `Issue: —` column to be filled in next step

---

## Step 5 — Create GitHub Issues (P0 + P1)

For every approved P0 and P1 task, use the `github-project-planning` skill:

1. Create the issue in the appropriate tracked repo, populated with **rich context** (objective, target files with paths/links, concrete acceptance criteria, and gotchas) to ensure other agents can complete the task.
2. Add to project board
3. Set **Status**, **Priority**, and **Size** custom fields (use option IDs from memory)
4. Write the issue number back into `workforces/workstate.md`

P2/P3 tasks → log in workstate only; create issues when they become active.

---

## Step 6 — Present the Roadmap

```markdown
## 🗺️ Roadmap — YYYY-MM-DD

### This Week (P0–P1)
| Task | Priority | Score | Issue | Status |
|------|----------|-------|-------|--------|
| {task} | P0 | RICE: 850 | #12 | 🆕 New |

### Next Sprint (P2)
| Task | Score |
|------|-------|
| {task} | ICE: 420 |

### 🎯 The One Thing
> **{top task}**
> _Reason: {why this is the single most important thing}_
```
