---
description: Report, update, evolve, and manage tasks and action items — with a simplified 5-state lifecycle (todo | in_progress | blocked | done | dropped), priority levels P0-P3, and deciding factor tracking.
---

# /task — Task & Action Item Reporting, Evolution, and Lifecycle

Report any business follow-up, feature idea, bug, design change, or action item to the workforce tasks with bidirectional session lineage. The `@scribe` tracks and evolves tasks during conversations with deciding factor logs.

---

## Usage

```
/task                           → Show active tasks summary (todo + in_progress)
/task add [title]               → Quick add a new task (e.g. /task add "Follow up with pilot lead" --priority P1 --type follow-up)
/task start [id|path]           → Mark task as in_progress
/task block [id|path] [reason]  → Mark task as blocked
/task done [id|path]            → Mark task as done
/task drop [id|path] [reason]   → Drop/reject a task with recorded deciding factors
/task update [id|path]          → Update existing task with requirement changes/evolution notes
/task list                      → List all tasks
/task list --status todo        → Filter by status: todo | in_progress | blocked | done | dropped
/task list --priority P1        → Filter by priority: P0 | P1 | P2 | P3
/task list --type follow-up     → Filter by tag/type
```

---

## `/task add` / Interactive Reporting

When an agent or human runs `/task add` or reports an item, gather the following:

1. **Title** — One sentence: what is the action item or task? (required)
2. **Type** — Freeform tag (e.g. `follow-up`, `idea`, `bug`, `debt`, `design`, `ops`, `business`, `marketing`, `security`)
3. **Priority** — `P0` (urgent), `P1` (high), `P2` (medium), `P3` (low)
4. **Assignee** — Person or agent responsible (e.g. `@user`, `@me`, `@aaron`, `@scribe`)
5. **Affected file(s)** — Which file(s) are involved? (optional)
6. **Origin Session Context** — Active session sequence (e.g. `026`) or session note path (optional)
7. **Description** — Full context: what needs to be done, why it matters
8. **Suggested action** — Recommended implementation plan or next step
9. **Deciding factor / Evolution note** — Initial reasoning or context

Then call the script:

```bash
python3 .agents/skills/task-tracker/scripts/report-task.py \
    --title "[title]" \
    --type [type] \
    --priority [P0-P3] \
    --assignee "@user" \
    --reporter [agent-name-or-human] \
    --session-id "[seq]" \
    --session-file "workforces/session-context/[seq]_[date]_[slug].md" \
    --file "[filepath]" \
    --description "[description]" \
    --suggested-action "[action]" \
    --evolution-note "[decision-note]" \
    --sync-session
```

**Confirm to the user:** `✅ Task created: workforces/tasks/[filename].md (Linked to Session #[seq])`

---

## In-Place Lifecycle Transitions

### Starting a Task (`/task start`)
```bash
python3 .agents/skills/task-tracker/scripts/report-task.py \
    --update "[task-path-or-slug]" \
    --start \
    --evolution-note "Started working on item." \
    --sync-session
```

### Blocking a Task (`/task block`)
```bash
python3 .agents/skills/task-tracker/scripts/report-task.py \
    --update "[task-path-or-slug]" \
    --block "Waiting on client API key." \
    --sync-session
```

### Completing a Task (`/task done`)
```bash
python3 .agents/skills/task-tracker/scripts/report-task.py \
    --update "[task-path-or-slug]" \
    --done \
    --evolution-note "Completed deliverable." \
    --sync-session
```

### Dropping a Task (`/task drop`)
```bash
python3 .agents/skills/task-tracker/scripts/report-task.py \
    --update "[task-path-or-slug]" \
    --drop "Decided against feature after user feedback." \
    --sync-session
```
5. Ask for user approval before writing to workstate or creating GitHub issues.

---

## `/task list` — Browse Issues

Show a formatted table of issues. Default shows all (inbox + triaged + completed):

```markdown
### 📋 Issue Tracker

#### ⏳ Inbox (Pending Triage) — 3 items

| File | Title | Type | Severity | Session | Reporter | Age |
|------|-------|------|----------|:-------:|---------|-----|
| 20260822-... | Adopt pastel palette | design | P2 | #022 | scribe | 2h |

#### ✅ Triaged — 12 items

| Title | Type | Priority | Session | Decision | GitHub |
|-------|------|----------|:-------:|----------|--------|
| Fix login race condition | bug | P1 | #015 | → workstate | #45 |

#### 📦 Completed & Rejected — 4 items

| Title | Type | Status | Session | Decision |
|-------|------|--------|:-------:|----------|
| ~~Dark mode only~~ | design | rejected | #011 | ❌ Rejected by user |
```

---

## `/task` — Summary View

Default view with no subcommand shows inbox health:

```markdown
### 📬 Issue Inbox

| Status | Count |
|--------|-------|
| ⏳ Pending triage | 3 |
| ✅ Triaged this week | 7 |
| 📦 Completed / Rejected | 4 |
| Total open in workstate | 12 |

Run `/task triage` to let the Project Manager review pending items.
Run `/task list` to see all issues.
```

---

## Storage Layout

```
workforces/
  issues/
    inbox/          ← Unreviewed. Written directly by agents & Scribe.
      YYYYMMDD-HHMMSS-<slug>.md
    triaged/        ← Reviewed by PM. Includes decision, session link, + GitHub link.
      YYYYMMDD-HHMMSS-<slug>.md
    completed/      ← Completed or Rejected ideas (preserves immutable audit trail).
      YYYYMMDD-HHMMSS-<slug>.md
```
