---
name: wf-plan
description: Transforms high-level project goals or PRD specifications into phased, actionable engineering plans with explicit dependency mapping and concurrency topologies. Reach for this skill or trigger it when scoping multi-stage development initiatives, conducting pre-plan codebase audits to avoid reinventing existing patterns, breaking down epics into estimated tasks, selecting parallel worktree topologies, or scaffolding roadmaps into `workforces/workstate.md`.
---
# Skill: /wf-plan — Project Planner

Breaks down work into phased, actionable tasks with estimates, dependencies, and risk assessment.

---

## Usage

```
/wf-plan [goal]                     → Create a plan for a goal
/wf-plan [goal] --auto              → Create plan, push to workstate, and automatically execute all tasks end-to-end
/wf-plan --from-prd [path] --auto   → Import PRD, build plan, push tasks to workstate, and auto-execute all tasks
/wf-plan --push-to-work             → Sync Phase 1 tasks into workforces/workstate.md & GH issues
/wf-plan --estimate                 → Add time estimates to existing plan
/wf-plan --risks                    → Add risk assessment to existing plan
```

---

## Step 0 — Scope Judgement & Pre-Plan Architecture Audit

> [!IMPORTANT]
> MUST be executed BEFORE drafting the implementation plan.

1. **Determine Scope Gate**:
   - **Purely Local Task** (isolated helper, UI tweak, single-file bug with no external events/integrations/env config): inspect target file and callers, then plan/fix immediately.
   - **System-Wired Task** (touches domain events, subscribers, webhooks, queues, 3rd-party services, or env/IaC config): run full macro-context audit below.
2. **Read Repo Living OKF Docs First**: Inspect `<repo>/docs/index.md` and matching `docs/architecture/*.md` cards (via `affected_files:` frontmatter) to understand existing services, event dispatchers, subscribers, `Key Dependencies & Blast Radius`, and `Constraints & Why` notes.
3. **Find at Least 1 Existing Analog & Map Blast Radius**: Search (`grep_search` on module import paths/exported symbols, `list_dir`) and optionally run `scaffold_repo_okf.py --impact <file>` on shared/cross-module targets to inspect direct importers, tests, and Git co-changed files so new code groups cleanly into existing extension points.
4. **Verify IaC & Environment Config Parity**: If config/env vars change, inspect `template.yaml`, `template.yml`, `samconfig.toml`, `serverless.yml`, or `.env.example` across environments; never plan `"production"` code defaults or unapproved live deployments.
5. **Record Findings**: Include `## Existing Codebase Audit Findings` (existing analog reused, subscribers affected, IaC config parity) in the plan.

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

## Step 4b — Execution Topology & Parallelization Strategy (`wf-agent-parallelization`)

Classify the plan's tasks into their Git concurrency mode so execution delegates cleanly:
- **Parallel Worktrees (`Workspace: 'share'`)**: For independent parallel tasks (e.g. `[task 2.1]` and `[task 2.2]`). Spawns subagents in isolated worktrees (`.worktrees/<slug>`) with zero `.git/index.lock` contention.
- **Vertical Relay (`gh-stack`)**: For layered dependency chains (e.g. `[task 1.1] → [task 1.2]`). Executed sequentially layer-by-layer and submitted as linked stacked PRs.
- **Direct Single-Branch**: For localized standalone tasks.

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

### Existing Codebase Audit Findings
- **Searched Files & Queries:** [paths, grep patterns, symbol queries checked]
- **Pre-Existing Entities & Methods:** [existing tables, models, functions, legacy scripts found]
- **Existing vs. Missing Capabilities:** [what already exists to reuse vs. what is missing to build]

### Detailed Breakdown
[full task list from Step 3]

### Risks
[from Step 5]
```

**⏸ PAUSE** — (Skipped if `--auto` flag is used or `auto_delegate: true` is configured).

If `--auto` flag is present:
- Automatically run `/wf-plan --push-to-work` (appends tasks to `workforces/workstate.md` and creates GitHub issues).
- Immediately dispatch parallel subagents via `wf-agent-parallelization` (Topology 1 isolated worktrees or Topology 2 vertical relays) to begin executing tasks.

If standard mode:
- Ask user if they want to push Phase 1 tasks into active execution state (`workforces/workstate.md` and `workforces/tasks/`).

---

## Flags

| Flag | Behavior |
|------|----------|
| `--auto` | Create plan, sync tasks to `workforces/workstate.md`, and execute all tasks automatically end-to-end. |
| `--from-prd [path]` | Import goal, scope, and initial task breakdown directly from a feature PRD document. |
| `--push-to-work` | Push Phase 1 tasks directly into `workforces/workstate.md` and create tracked GitHub issues. |
| `--estimate` | Add/re-evaluate time estimates for an existing plan. |
| `--risks` | Run a risk assessment matrix on an existing plan. |
