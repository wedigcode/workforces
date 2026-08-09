---
name: pr-review
description: Automated GitHub PR code review, commenting via gh CLI, and escalation of PR blockers to Project Manager standup syncs.
---

# Skill: GitHub PR Automated Code Review

Discovers open Pull Requests across workforce repositories, performs automated code reviews against Clean Coder rules, posts review feedback using `gh`, and escalates critical issues to human standup syncs.

---

## Workflow Protocol

### Step 1: Discover Open PRs (Workforce Repos Only)
1. Determine the active workforce repository name:
   ```bash
   gh repo view --json nameWithOwner -q '.nameWithOwner'
   ```
2. Query open PRs strictly for the active repo or repos listed in `workforces/workrules.md` / `workstate.md`:
   ```bash
   # List open PRs in current workforce repo
   gh pr list --repo <owner/repo> --state open --limit 30
   ```
> ⚠️ **Repository Scoping Rule**: Ignore any PRs belonging to external or unrelated repositories outside the workforce project scope.

### Step 2: Extract & Audit PR Code Diff
For each open PR:
```bash
gh pr diff <pr_number>
```
Audit the diff against **Clean Coder Rules** (`rules/clean-coder.md`):
- **SOLID / DRY / KISS**: Are functions small, focused, and free of duplicated code?
- **Existing Method Check**: Does the PR introduce redundant helper functions that already exist in `workforces/code-graph.json`?
- **Error Handling**: Are there any swallowed exceptions, empty `catch`/`except` blocks, or unhandled promise rejections?
- **Testing**: Are corresponding unit/integration tests added or updated for new features/bugfixes?
- **Security & Performance**: Are untrusted inputs sanitized? Are there expensive unindexed queries or $O(n^2)$ loops?

### Step 3: Submit GitHub PR Review / Comment
Use `gh pr review` to post structured feedback directly on GitHub:

#### 1. Constructive Feedback / Changes Requested
```bash
gh pr review <pr_number> --request-changes -b "### 🔍 Workforce Automated PR Review

**Issues Found:**
- ⚠️ **Error Swallowing:** Line 45 in \`src/auth.ts\` catches errors silently. Please rethrow or log with context.
- 💡 **Duplication:** Method \`formatUserDate\` duplicates existing utility \`formatDate\` in \`src/utils/date.ts\`.

Please update these before merging."
```

#### 2. Comment / Approval
```bash
gh pr review <pr_number> --comment -b "### 🔍 Workforce Automated PR Review

✅ Code aligns with SOLID/DRY principles and tests pass cleanly."
```

### Step 4: Scheduled Run & Project Manager Escalation
During scheduled tasks or `/work sync`:
- If a PR has requested changes, is stale (>7 days), or has unresolved blocking feedback, flag it for the `@project-manager` agent:
  > *"🔴 **PR Review Escalation:** PR #<number> ([title]) has open review notes. Added to standup sync for human review."*
