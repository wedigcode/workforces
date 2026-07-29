---
description: Multi-phase project planning with task breakdown, estimation, and dependency mapping. Use when scoping work, planning sprints, or breaking down epics.
---

# /plan — Project Planner

Breaks down work into phased, actionable tasks with estimates, dependencies, and risk assessment.

---

## Usage

```
/plan [goal]                     → Create a plan for a goal
/plan --from-prd [path]          → Build plan & estimates from a PRD (e.g. docs/prd-*.md)
/plan --push-to-work             → Sync Phase 1 tasks into workforces/workstate.md & GH issues
/plan --estimate                 → Add time estimates to existing plan
/plan --risks                    → Add risk assessment to existing plan
```

---

## Step 1 — Define the Goal

1. State the goal in one sentence (or extract from PRD if `--from-prd` flag is used)
2. Define "done" — what does success look like?
3. Identify scope boundaries — what's explicitly *not* included?

```markdown
## 📋 Plan: [Goal]

**Objective:** [one sentence]
**Done when:** [measurable completion criteria]
**Out of scope:** [explicitly excluded items]
```

---

## Step 2 — Break Down into Phases

1. Group work into logical phases (each phase should be deployable):

```markdown
### Phases

| Phase | Focus | Depends On |
|-------|-------|-----------|
| 1 | [foundation / setup] | — |
| 2 | [core feature] | Phase 1 |
| 3 | [polish / edge cases] | Phase 2 |
```

---

## Step 3 — Task Breakdown

For each phase, list specific tasks:

```markdown
### Phase 1: [Name]

| # | Task | Estimate | Risk | Notes |
|---|------|----------|------|-------|
| 1.1 | [task] | [hours] | Low | |
| 1.2 | [task] | [hours] | Med | [dependency or risk note] |
| 1.3 | [task] | [hours] | Low | |

**Phase total:** [X hours]
```

### Estimation Guide

| Confidence | Multiplier | When |
|-----------|------------|------|
| **High** — done it before | 1x | Routine work |
| **Medium** — similar to past work | 1.5x | Some unknowns |
| **Low** — first time | 2-3x | Significant unknowns |

---

## Step 4 — Dependency Map

```markdown
### Dependencies

[task 1.1] → [task 1.2] → [task 2.1]
                        → [task 2.2] (parallel)
[task 2.1] + [task 2.2] → [task 3.1]
```

Critical path: the longest chain of dependent tasks = minimum timeline.

---

## Step 5 — Risk Assessment

```markdown
### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [what could go wrong] | Low/Med/High | Low/Med/High | [how to prevent or handle] |
```

---

## Step 6 — Output the Plan

```markdown
## 📋 Implementation Plan: [Goal]

**Timeline:** [total estimated hours/days]
**Phases:** [X]
**Tasks:** [X]
**Critical risks:** [X]

### Summary
| Phase | Tasks | Estimate | Status |
|-------|-------|----------|--------|
| 1 — [name] | [X] | [X hrs] | ⬜ Not started |
| 2 — [name] | [X] | [X hrs] | ⬜ Not started |
| 3 — [name] | [X] | [X hrs] | ⬜ Not started |

### Detailed Breakdown
[full task list from Step 3]

### Risks
[from Step 5]
```

**⏸ PAUSE** — Ask user if they want to push Phase 1 tasks into `/work` execution state (`workforces/workstate.md`) and create GitHub issues.

If yes → run `/plan --push-to-work` (appends Phase 1 tasks to `Active Tasks` in `workstate.md` and triggers `github-project-planning` skill for issue creation).

---

## Flags

| Flag | Behavior |
|------|----------|
| `--from-prd [path]` | Import goal, scope, and initial task breakdown directly from a feature PRD document. |
| `--push-to-work` | Push Phase 1 tasks directly into `workforces/workstate.md` and create tracked GitHub issues. |
| `--estimate` | Add/re-evaluate time estimates for an existing plan. |
| `--risks` | Run a risk assessment matrix on an existing plan. |
