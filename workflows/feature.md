---
description: Research-first feature pipeline — clarify, gap analysis, PRD, and work breakdown. Use when scoping a new feature across projects and workforces.
---

# /feature — Feature Research Pipeline

Turns a feature idea into a researched, documented, and task-broken deliverable — before any code gets written.

---

## Usage

```
/feature [idea]           → Start full pipeline (Phase 0–4)
/feature --gap-only       → Stop after gap analysis (Phase 0–1)
/feature --prd            → Skip to PRD (assumes gap analysis exists)
/feature --breakdown      → Skip to work breakdown (assumes PRD exists)
```

---

## Skills Required

Load these skills before starting:

1. **`feature-research`** — the pipeline definition, templates, and phase logic
2. **`memory-management`** — for reading project knowledge catalog (`workforces/knowledge-catalog/`) and project memory
3. **`github-project-planning`** — for issue creation and project board tracking

```
Read: skills/feature-research/SKILL.md
Read: skills/memory-management/SKILL.md
Read: skills/github-project-planning/SKILL.md
```

---

## Step 1 — Clarify (Phase 0)

1. Read the user's feature idea
2. Produce a **Feature Brief** using the template from `feature-research` skill
3. Present to the user for confirmation

```markdown
## Feature Brief

**Feature:** [one-line description]
**Target User:** [who benefits]
**Target Project(s) / Repo(s):** [which projects/repos will be modified]
**Problem:** [what problem this solves]
**Success Criteria:** [how we know it's done]
```

**⏸ PAUSE** — Wait for user to confirm the brief is accurate before proceeding.

---

## Step 2 — Gap Analysis (Phase 1)

1. Obtain context for the user's workforces and projects:
   - Read `workforces/workrules.md` and `workforces/workstate.md` for active workspace config and target projects.
   - Inspect `workforces/projects/` and OKF catalogs in `workforces/knowledge-catalog/` (if present) for architecture, API schemas, and entity ownership.
   - Read `workforces/memory/github-project-planning-skill.md` (if present) for tracked repositories.
2. Locate target project repos:
   - Check sibling directories at `../` relative to workspace root or specified project directories.
   - If not found → ask the user for the file path.
3. For each relevant project, investigate existing implementations.
4. Produce a **Gap Analysis Document** using the template from `feature-research` skill.
5. Save as an artifact.

**⏸ PAUSE** — Wait for user to review the gap analysis.

---

## Step 3 — Implementation Strategy (Phase 2)

1. Based on the gap analysis, determine:
   - Where the feature lives (project, repository, module/namespace)
   - External service dependencies
   - Shared library / service contract changes
   - Database migrations / schema updates needed
   - API endpoint changes
   - Deployment / rollout order
2. Append the **Implementation Strategy** to the feature document.

---

## Step 4 — PRD (Phase 3)

1. Using the gap analysis + strategy, generate a **PRD**
2. Save to `docs/prd-{feature-name}.md` in the target project repository
3. Present to the user for review

**⏸ PAUSE** — Wait for user to review and approve the PRD.

---

## Step 5 — Work Breakdown (Phase 4)

1. Break the PRD into tasks with P0/P1/P2 priorities
2. Estimate size (XS–XL) for each task
3. Map dependencies between tasks
4. Present the **Work Breakdown Table** to the user

```markdown
### P0 — Must Ship
| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|

### P1 — Should Ship
| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|

### P2 — Nice to Have
| # | Task | Project / Repo | Size | Depends On | Acceptance Criteria |
|---|------|----------------|------|-----------|-------------------|
```

**⏸ PAUSE** — Ask user if they want to create GitHub issues for P0/P1 tasks, or generate an execution timeline with estimates via `/plan`.

- If GitHub issues → hand off to `github-project-planning` skill for issue creation.
- If execution plan → run `/plan --from-prd docs/prd-{feature-name}.md`.

---

## Flags

| Flag | Behavior |
|------|----------|
| `--gap-only` | Run Phase 0 + Phase 1, then stop. Good for initial research. |
| `--prd` | Skip to Phase 3. Assumes a gap analysis already exists — look for it in recent artifacts. |
| `--breakdown` | Skip to Phase 4. Assumes a PRD exists — look for it in `docs/prd-*.md`. |

---

## Output Artifacts

| Phase | Output | Location |
|-------|--------|----------|
| 0 | Feature Brief | Inline (conversation) |
| 1 | Gap Analysis | Artifact (conversation) |
| 2 | Implementation Strategy | Appended to gap analysis artifact |
| 3 | PRD | `docs/prd-{feature-name}.md` in target project |
| 4 | Work Breakdown | Artifact (conversation) + GitHub Issues |
