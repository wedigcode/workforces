---
name: jules-integration
description: Integration with Google Jules CLI (@google/jules) for discovering, reviewing, testing, updating, and closing Jules coding sessions and scheduled tasks.
---

# Skill: Google Jules CLI Integration

Integrates Google's asynchronous coding agent **Jules** (`@google/jules`) with Workforces. Discovers active/remote sessions, conducts automated code reviews on Jules outputs, fixes/updates generated code, and reports session status to the `@project-manager` agent for standup syncs.

---

## 1. Global Installation Check

Before running Jules operations, verify CLI availability:
```bash
which jules || npx @google/jules --help || npm list -g @google/jules
```
If `jules` command is not in PATH, use `npx @google/jules <command>`.
If `@google/jules` is not installed, notify the user:
> *"ℹ️ `@google/jules` is not installed globally. Install via `npm i -g @google/jules` to enable Jules async session tracking."*

---

## 2. Session Discovery & Filtering Protocol

### Identify Current Repository Target
First, get the current workforce repository name:
```bash
CURRENT_REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || git config --get remote.origin.url)
```

### List & Filter Remote Jules Sessions
```bash
jules remote list --session
```
> ⚠️ **Strict Repo & Active Status Filtering Rules**:
> 1. **Repository Filter**: Filter results to ONLY process or review Jules sessions whose `repo` matches `$CURRENT_REPO` or repositories explicitly tracked in `workforces/workrules.md` / `workstate.md`. Disregard sessions from any external repositories.
> 2. **Active Status Filter**: When checking for active code review tasks, filter for sessions whose status is **NOT `Completed`** (e.g. `In Progress`, `""` [empty string/pending], `Needs Review`). Completed sessions are archived unless explicitly requested for historical patch audits.

---

## 3. Jules Code Review & Refactoring Protocol

When Jules completes or progresses on a session:

1. **Pull & Apply Session Patch**:
   ```bash
   jules remote pull --session <session_id> --apply
   ```
   *Alternatively, use teleport:*
   ```bash
   jules teleport <session_id>
   ```

2. **Code Review & Quality Check**:
   - Audit patch against **Clean Coder Rules** (`rules/clean-coder.md`).
   - Run `python3 skills/code-graph/scripts/graph_indexer.py --scan ./ --query "<method_name>"` to verify Jules did not create duplicate helper functions.
   - Verify proper error handling (no swallowed exceptions).

3. **Run Test Suites**:
   - Execute project test suites (`npm test`, `pytest`, `go test`, etc.).
   - If tests fail or code quality issues exist, apply targeted refactoring and commit updates cleanly.

4. **Session Closing & Merge**:
   - Once verified and tests pass, commit and push changes or open PR to complete/close the session.

---

## 4. Project Manager & Standup Sync Integration

During scheduled tasks or `/work sync`:
- Query `jules remote list --session`.
- Strictly filter for sessions matching the current active workspace repository (`$CURRENT_REPO`) or repos listed in `workforces/workrules.md`.
- Filter for active code review tasks where `Status != 'Completed'` (e.g. `In Progress`, `""` [empty/pending], `Needs Review`).
- Surface active non-completed Jules sessions to `@project-manager`:

```markdown
### 🤖 Google Jules Active Sessions

| Session ID | Repo | Title / Task | Status | Action Recommended |
|------------|------|--------------|--------|--------------------|
| 123456 | org/repo | Add payment retry handler | Completed | Pull patch & review code |
| 789012 | org/repo | Refactor auth middleware | In Progress | Monitor progress |
```
