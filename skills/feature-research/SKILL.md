---
name: feature-research
description: Multi-phase pipeline that turns a feature idea into a gap analysis, PRD, and prioritized work breakdown (P0/P1/P2). Enforces research-first development across workforces and projects. Use when scoping new features.
---

# Feature Research

Turn a feature idea into a well-researched, actionable plan — before writing any code. This skill defines a 5-phase pipeline that produces a gap analysis, implementation strategy, PRD, and work breakdown.

## When to Use

- A new feature idea is proposed and needs scoping
- You need to understand how a feature relates to existing code across workforces and project repositories
- You want to produce a PRD before starting implementation
- You need to break a feature into GitHub-ready P0/P1/P2 tasks

## Required Skills

Always load these skills before starting the pipeline:
- **`memory-management`** — for reading project knowledge catalog (`workforces/knowledge-catalog/`) and project memory
- **`github-project-planning`** — for project boards and GitHub issue creation

---

## The Pipeline

```
Phase 0: Clarify the Request
    ↓ (user confirms)
Phase 1: Gap Analysis (cross-project)
    ↓ (user reviews)
Phase 2: Implementation Strategy
    ↓
Phase 3: PRD Generation
    ↓ (user reviews)
Phase 4: Work Breakdown (P0/P1/P2)
    ↓ (hand off to github-project-planning)
```

Pause for user review after Phases 0, 1, and 3. Do not proceed without confirmation.

---

## Phase 0 — Clarify the Request

**Goal:** Ensure the feature idea is specific enough to research.

Before doing any research, produce a **Feature Brief**:

```markdown
## Feature Brief

**Feature:** [one-line description]
**Target User:** [who benefits — end users, admins, internal team]
**Target Project(s) / Repo(s):** [which project(s)/repo(s) will be modified]
**Problem:** [what problem does this solve]
**Success Criteria:** [how do we know it's working]
**Proposed By:** [who requested this — user, stakeholder, team]
```

### Clarification Rules

- If the request is vague → ask specific questions before proceeding
- If the target project/repo is unclear → inspect workspace configuration (`workforces/workrules.md`, `workforces/projects/`, `workforces/workstate.md`) to determine it
- If the feature could mean multiple things → present options and ask which one

> [!IMPORTANT]
> Do NOT start Phase 1 until the user has confirmed the Feature Brief is accurate.

---

## Phase 1 — Gap Analysis

**Goal:** Determine what already exists across workforces and projects, and what's missing.

### Gathering Context

1. Read workspace configuration in `workforces/workrules.md` and `workforces/workstate.md`.
2. Inspect tracked project definitions in `workforces/projects/` and Open Knowledge Format (OKF) files in `workforces/knowledge-catalog/` to map entities, APIs, and services.
3. Check `workforces/memory/github-project-planning-skill.md` for tracked repository metadata.
4. Locate project repository roots (sibling folders at `../` relative to workspace root, subdirectories, or specified paths).
   - If a project directory is not found → pause and ask the user for the path.
5. For each relevant project, investigate:
   - Does this feature (or something similar) already exist?
   - How is the analogous workflow currently handled?
   - What entities, APIs, services, and database tables are involved?

### Output Format

Produce a **Gap Analysis Document** using this template:

```markdown
# [Feature Name] Gap Analysis
## [Source] (existing) vs. [Target] (proposed)

---

## Existing Codebase Audit Findings

- **Searched Files & Queries:** [list files, tables, directories, and symbol queries searched via code-graph/grep_search/list_dir]
- **Pre-Existing Entities & Methods:** [list existing database tables, models, legacy utilities, or helper methods]
- **Existing vs. Missing Capabilities:** [clear breakdown of what already exists vs what needs to be built]

---

## Overview

| Dimension | Current ([source]) | Proposed ([target]) |
|---|---|---|
| **Architecture** | [how it works now] | [how it would work] |
| **Auth method** | [current auth] | [proposed auth] |
| **Data model** | [current entities] | [proposed entities] |
| ... | ... | ... |

---

## Missing in Target (what needs to be built)

| Field / Behavior | Where in Source | Priority |
|---|---|---|
| [field] | [location] | High / Medium / Low |

---

## Missing in Source (what Target adds that's new)

| Field / Behavior | Target Location | Notes |
|---|---|---|
| [field] | [location] | [context] |

---

## Priority Gaps to Close

> [!IMPORTANT]
> These items are **required** before the feature can ship.

1. **[Gap 1]** — [why it's critical]
2. **[Gap 2]** — [why it's critical]
...
```

### Quality Bar

The gap analysis should be thorough and clear:
- Side-by-side comparison table covering architecture, auth, data, and UX
- Explicit list of what each side is missing
- Prioritized list of gaps with reasoning
- Alerts/warnings for items with compliance, security, or data implications

> After producing the gap analysis, save it as an artifact and pause for user review.

---

## Phase 2 — Implementation Strategy

**Goal:** Determine the technical approach based on the gap analysis.

Answer these questions:

1. **Where does the feature live?** Which project(s), repo(s), and module/namespace(s)?
2. **External services:** What APIs, SDKs, or third-party services are needed?
3. **Shared libraries / contracts:** Do shared libraries or SDKs need modifications? What's the impact?
4. **Database changes:** What new tables, columns, or indexes are needed? Which project owns them?
5. **API endpoints:** What new or modified endpoints are required?
6. **Auth/permissions:** Which user entity and permission system applies?
7. **Deployment order:** Which project/repo deploys first?

### Output Format

Append an **Implementation Strategy** section to the feature document:

```markdown
## Implementation Strategy

### Architecture

[Describe where the feature lives and how components connect]

### Project / Repo Changes

| Project / Repo | What Changes | Depends On |
|----------------|-------------|-----------|
| `[main-app]` | [changes] | — |
| `[shared-lib]` | [changes] | — |
| `[api-service]` | [changes] | `[main-app]` API |

### External Dependencies

| Service | Purpose | New Integration? |
|---------|---------|-----------------|
| [service] | [why] | Yes / No |

### Database Changes

| Project / Repo | Table/Entity | Change Type | Details |
|----------------|-------------|------------|---------|
| [project] | [table] | New / Modify | [details] |

### Deployment Order

1. [first project/repo — why]
2. [second project/repo — why]
```

---

## Phase 3 — PRD Generation

**Goal:** Produce a Product Requirements Document from the research.

Using the gap analysis and implementation strategy, generate a PRD.

### Output Location

Save to: `docs/prd-{feature-name}.md` in the **target project repository**.

### PRD Template

```markdown
# PRD: [Feature Name]

**Author:** [name]
**Date:** [YYYY-MM-DD]
**Status:** Draft | Review | Approved
**Target Project(s) / Repo(s):** [projects/repos]

---

## Problem Statement

[What problem does this feature solve? Who is affected? What's the impact of not solving it?]

## User Stories

- As a [user type], I want to [action] so that [benefit]
- As a [user type], I want to [action] so that [benefit]

## Functional Requirements

### Must Have (P0)
- [ ] [requirement] — [acceptance criteria]
- [ ] [requirement] — [acceptance criteria]

### Should Have (P1)
- [ ] [requirement] — [acceptance criteria]

### Could Have (P2)
- [ ] [requirement] — [acceptance criteria]

### Won't Have (this release)
- [explicitly excluded items]

## Non-Functional Requirements

- **Performance:** [targets — response time, throughput]
- **Security:** [auth, encryption, compliance]
- **Scalability:** [expected load, growth]
- **Monitoring:** [logging, alerts, dashboards]

## Dependencies & Risks

| Dependency / Risk | Impact | Mitigation |
|------------------|--------|-----------|
| [item] | [impact] | [how to address] |

## Out of Scope

[What this feature explicitly does NOT include]

## References

- [Link to gap analysis]
- [Link to related PRDs or docs]
- [Link to relevant Knowledge Items / OKF files]
```

> After generating the PRD, pause for user review before proceeding to work breakdown.

---

## Phase 4 — Work Breakdown

**Goal:** Break the PRD into GitHub-ready tasks with priority levels.

### Priority Levels

| Priority | Meaning | Criteria |
|----------|---------|----------|
| **P0** | Must ship — blocks launch | Core functionality, no workarounds, data/compliance risk |
| **P1** | Should ship — high value | Directly supports the feature goal, has workarounds |
| **P2** | Nice to have — can follow | Enhancements, polish, edge cases, UX improvements |

### Size Estimates

| Size | Time | Characteristics |
|------|------|----------------|
| **XS** | < 2 hours | Config change, copy update, one-file fix |
| **S** | 2-4 hours | Single feature, 1-3 files, well-understood |
| **M** | 1-2 days | Multi-file change, needs testing, some unknowns |
| **L** | 3-5 days | Cross-cutting concern, new patterns, integration |
| **XL** | 1-2 weeks | New system, significant architecture, high risk |

### Output Format

```markdown
## Work Breakdown: [Feature Name]

### P0 — Must Ship

| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|
| 1 | [task] | [project] | M | — | [criteria] |
| 2 | [task] | [project] | S | #1 | [criteria] |

### P1 — Should Ship

| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|
| 3 | [task] | [project] | M | #1 | [criteria] |

### P2 — Nice to Have

| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|
| 4 | [task] | [project] | S | #3 | [criteria] |

### Summary

| Priority | Tasks | Total Effort |
|----------|-------|-------------|
| P0 | [N] | [X days] |
| P1 | [N] | [X days] |
| P2 | [N] | [X days] |
| **Total** | **[N]** | **[X days]** |
```

### GitHub Integration

After the user approves the work breakdown:
- **P0 and P1 tasks** → hand off to `github-project-planning` skill for issue creation
- **P2 tasks** → create issues only when they're ready to be picked up
- Each issue body should include:
  - Description from the task row
  - Acceptance criteria
  - Dependencies (link to blocking issues)
  - Target project/repo (if different from current workspace)
  - Link back to the PRD

---

## Anti-Patterns

| ❌ Don't | ✅ Do |
|---------|------|
| Start coding before the gap analysis | Complete Phase 1 before touching code |
| Skip the clarification phase | Vague inputs produce bad research |
| Assume a feature is repo-local | Check workspace context — features can touch multiple projects |
| Write the PRD from scratch without research | The gap analysis IS the research — the PRD synthesizes it |
| Create all work items as P0 | P0 means "blocks launch" — be honest about priority |
| Skip user review between phases | The pipeline has pause points for a reason |
| Guess about project repository locations | Check `workforces/projects/`, `workforces/workrules.md`, or sibling folders at `../`; ask user if not found |

---

## Quick Reference

| Phase | Input | Output | Pause? |
|-------|-------|--------|--------|
| 0 — Clarify | Feature idea (raw) | Feature Brief | ✅ Yes |
| 1 — Gap Analysis | Feature Brief | Gap Analysis Document | ✅ Yes |
| 2 — Strategy | Gap Analysis | Implementation Strategy | No (flows into Phase 3) |
| 3 — PRD | Gap Analysis + Strategy | `docs/prd-{feature}.md` | ✅ Yes |
| 4 — Breakdown | PRD | P0/P1/P2 task table | ✅ Yes (before GitHub issue creation) |
