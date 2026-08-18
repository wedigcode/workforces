---
description: Codebase hygiene, background knowledge refresh, OKF catalog build, and code cleanliness audit.
---

# Workflow: `/clean` (Codebase Hygiene & Knowledge Maintenance)

Run codebase maintenance to keep the Code Graph, OKF Knowledge Catalog, and workspace hygiene in top condition.

---

## Steps

### Step 1: Force Full Code Graph & OKF Catalog Rebuild
Re-indexes all codebase symbols and regenerates individual OKF concept Markdown files under `workforces/knowledge-catalog/code/`:

```bash
python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog/code --build-okf --force
```
*(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py ...`)*

---

## Step 2: Code Cleanliness Audit

Run automated quality and hygiene checks:

1. **Dead Code & Unused Symbols**: Identify indexed symbols with zero downstream callers across the codebase.
2. **Workspace Scratch Cleanup**: Sweep `workforces/tmp/` and temporary execution logs older than 7 days.
3. **Broken Relative Links**: Scan `workforces/knowledge-catalog/` for references pointing to non-existent files.
4. **Git Workspace Hygiene**: Report untracked artifacts or uncommitted scratch files.

---

## Step 3: Deferred Issue Reporting

For any issues found in Step 2 that cannot be fixed immediately (e.g. dead code intertwined with active logic, architectural debt, breaking-change refactors), report each one to the issue inbox:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "[Brief description]" \
    --type debt \
    --severity P2 \
    --reporter clean \
    --file "[affected file]" \
    --description "[What was found and why it can't be fixed now]" \
    --suggested-action "[What should be done]"
```
*(Fallback: `python3 skills/issue-tracker/scripts/report-issue.py`)*

Do NOT silently drop findings. Every unfixable issue from the clean audit becomes an inbox item.

---

## Step 4: Summary Report

Outputs a clean summary matrix:

```markdown
### 🧹 [Codebase Maintenance Summary]

| Check | Status | Details |
|-------|--------|---------|
| **Code Graph Index** | ✅ Up to date | 32 symbols indexed in `workforces/code-graph.json` |
| **OKF Knowledge Catalog** | ✅ Rebuilt | Catalog synced at `workforces/knowledge-catalog/code/index.md` |
| **Dead Code / Unused Symbols** | ⚠️ 2 found | `unused_helper()` (src/utils.ts:L14) |
| **Workspace Scratch Clean** | ✅ Clean | 0 stale files removed |
| **Issues Reported to Inbox** | 📬 2 logged | Run `/task triage` for PM review |
```
