---
name: task-tracker
description: Manages deferred action items, task lifecycles (todo, in_progress, blocked, done, dropped), and priority queues (P0-P3) in `workforces/tasks/`. Reach for this skill when logging action items mid-conversation, answering "what do we have to work on?", surfacing active or blocked tasks during daily standups, recording task dependency changes with session lineage, or running personal sync reviews.
---
# Task Tracker

A structured, zero-friction pipeline for capturing, evolving, and managing tasks, business follow-ups, and spontaneous ideas discovered during sessions — without losing context or blocking active workflows.

---

## Triggering & Agent Actions

Agents and Scribe invoke the task tracker automatically via `report-task.py` and `personal_sync.py`, responding to natural user requests or workflow events:

- **Create Task**: User says *"Add task: [title]"* or an agent detects an unhandled follow-up.
- **Update Status**: User says *"Mark task X as done/blocked/dropped"* or an agent finishes a work item.
- **Show Active Tasks**: User asks *"What are my active tasks?"*, *"What do we have to work on?"*, or during `/wf-sync`.
- **Personal Sync**: Aggregated via `python3 skills/task-tracker/scripts/personal_sync.py --root ./`.
- **Antigravity Execution**: Active tasks route directly to modern Antigravity subagents via `agent-parallelization` (isolated worktrees in `.worktrees/<slug>`).

---

## When to Use

- An action item arises during a business or consultative conversation (e.g. *"follow up with pilot lead"*)
- An agent identifies a bug or technical debt mid-task that isn't worth fixing immediately
- The `@designer` flags a design enhancement for a component not currently being edited
- A spontaneous idea or architectural concept surfaces during a session
- The `@scribe` records a requirement pivot or decision evolution mid-session
- An item is completed, blocked, or dropped with explicit deciding factors

---

## Core Concepts

### Unified Status Lifecycle (`status`)

Tasks use a single 5-state lifecycle matching natural todo workflows:
- **`todo`**: Actionable task ready to be worked on (default state upon creation).
- **`in_progress`**: Actively being worked on or executed.
- **`blocked`**: Waiting on external dependency, review, or answer.
- **`done`**: Successfully completed.
- **`dropped`**: Intentionally abandoned, rejected, or won't fix (with deciding factors logged).

### In-Place Task Management (`workforces/tasks/`)

Tasks are stored as Markdown files with YAML frontmatter in `workforces/tasks/` (or `.scribe/tasks/`).
Status transitions modify frontmatter (`status: in_progress`, `status: done`, etc.) **in-place**, preserving stable file links and git history.

### Flexible Categorization (`type`) & Universal Priority (`priority`)

- **`type`**: Freeform tag (e.g. `follow-up`, `idea`, `bug`, `debt`, `design`, `ops`, `business`, `marketing`, `security`).
- **`priority`**: `P0` (critical/urgent), `P1` (high), `P2` (medium), `P3` (low).

---

## How to Report & Manage Tasks

### 1. Report a New Task

```bash
python3 skills/task-tracker/scripts/report-task.py \
    --title "Follow up with pilot team lead regarding security questionnaire" \
    --type follow-up \
    --priority P1 \
    --assignee "@user" \
    --reporter scribe \
    --session-id "026" \
    --session-file "workforces/session-context/026_2026-08-23_claude_scribe_product_brief.md" \
    --description "Send updated SOC2 summary and schedule 15m review." \
    --suggested-action "Draft email and attach SOC2 bridge letter." \
    --evolution-note "Initial discussion: user agreed to follow up by Tuesday." \
    --sync-session
```

### 2. Update Status In-Place

```bash
# Start working on a task:
python3 skills/task-tracker/scripts/report-task.py \
    --update "follow-up-with-pilot-team-lead" \
    --start \
    --evolution-note "Started drafting email response." \
    --sync-session

# Mark task as completed:
python3 skills/task-tracker/scripts/report-task.py \
    --update "follow-up-with-pilot-team-lead" \
    --done \
    --evolution-note "Sent email and scheduled call for Thursday." \
    --sync-session

# Mark task as blocked:
python3 skills/task-tracker/scripts/report-task.py \
    --update "follow-up-with-pilot-team-lead" \
    --block "Waiting for updated SOC2 bridge letter from legal." \
    --sync-session
```

### 3. Drop / Reject a Task (Deciding Factor Log)

When a task is dropped or rejected, keep the audit trail and record the rationale:

```bash
python3 skills/task-tracker/scripts/report-task.py \
    --update "follow-up-with-pilot-team-lead" \
    --drop "Lead reached out directly; separate follow-up no longer required." \
    --sync-session
```

### 4. Search Similar Tasks & List Tasks

```bash
# Check similarity before creating:
python3 skills/task-tracker/scripts/report-task.py --find-similar "security questionnaire"

# List todo and in-progress tasks:
python3 skills/task-tracker/scripts/report-task.py --list --status todo
```

### 5. Personal Sync & Follow-Up Aggregator (`/sync --me`)

Aggregate your in-flight tasks, git workspace, session context, and GitHub reviews/issues in a single command:

```bash
# Run personal sync in markdown format:
python3 skills/task-tracker/scripts/personal_sync.py --root ./ --format markdown

# Output as JSON for programmatic integration:
python3 skills/task-tracker/scripts/personal_sync.py --root ./ --format json
```

---

## Task File Schema

```markdown
---
title: "Follow up with enterprise pilot lead regarding security questionnaire"
type: "follow-up"
priority: "P1"
status: "todo"
reporter: "scribe"
assignee: "@user"
reported_at: "2026-08-23T12:00:00"
updated_at: "2026-08-23T12:15:00"
file: ~
session_id: "026"
session_file: "workforces/session-context/026_2026-08-23_claude_scribe_product_brief.md"
recommended_tools: []
delegated_to: ~
github_labels: []
github_issue: ~
---

# Follow up with enterprise pilot lead regarding security questionnaire

**Type:** `follow-up` | **Priority:** `P1` | **Status:** `todo` | **Reporter:** `scribe` | **Assignee:** `@user`  
**Reported:** 2026-08-23 12:00 | **Updated:** 2026-08-23 12:15  
**Origin Session:** [026_2026-08-23_claude_scribe_product_brief.md](file:///path/to/session.md)  

## Description

Send over the updated SOC2 summary and clarify SSO deployment timeline.

## Suggested Action

Draft email response with attached SOC2 bridge letter and schedule 15m review call.

## 🧠 Session Lineage & Deciding Factors

- **2026-08-23 12:00:** Initial action item identified during pilot sync.
```
