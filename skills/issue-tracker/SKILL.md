---
name: issue-tracker
description: Captures and preserves deferred bugs, technical debt, design flaws, and spontaneous feature ideas discovered during active workflows without interrupting execution. Reach for this skill whenever encountering an issue that cannot be fixed immediately, recording emergent backlog items with session lineage and deciding factors (`workforces/issues/inbox/`), or triaging accumulated inbox reports into prioritized engineering tasks.
---
# Issue Tracker

A structured pipeline for capturing and evolving deferred issues, bugs, tech debt, and spontaneous feature ideas discovered during agent execution or extended chat sessions — without losing context or blocking active workflows.

---

## When to Use

- An agent finds a bug but is mid-task and can't stop to fix it
- `/clean` or `post-code-review` spots tech debt not worth fixing right now
- The `@designer` flags a design anti-pattern in a component not currently being edited
- A spontaneous feature idea or architectural concept surfaces during a multi-hour conversation
- The `@scribe` records a requirement pivot or decision evolution mid-session
- An idea surfaces during execution that belongs in the project backlog

---

## Core Concepts

### The Inbox (`workforces/issues/inbox/`)

Untriaged issues and feature ideas written directly by agents or the `@scribe`. Any agent can append or update issues immediately with origin session links.

### Triaged (`workforces/issues/triaged/`)

Issues that the project-manager has reviewed and either:
- Promoted to `workstate.md` as a P0/P1/P2/P3 task
- Created as a GitHub issue (P0/P1)

### Completed & Rejected (`workforces/issues/completed/`)

Issues and feature ideas that have either been completed or explicitly rejected by the user/team (`triage_status: "rejected"` or `status: "completed"`). Moving rejected ideas here preserves an immutable audit trail with deciding factors while keeping the active inbox and sprint backlog clean.

### Session Lineage & Decision Evolution

Long conversations often evolve (e.g. user proposes red styling, then 2 hours later pivots to a soft pastel palette, or rejects a feature outright). Rather than creating duplicate issues or losing previous rationale, `report-issue.py` supports `--update`, `--evolution-note`, and `--reject` to append timestamped decision milestones to `## 🧠 Session Lineage & Deciding Factors`.

---

## How to Report an Issue or Feature Idea

Use `run_command` to call the script:

```bash
# 1. Report a new issue linked to active session context:
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "Adopt soft pastel color palette" \
    --type design \
    --severity P2 \
    --reporter scribe \
    --session-id "022" \
    --session-file "workforces/session-context/022_2026-08-22_topic.md" \
    --file "src/styles/theme.css" \
    --description "Replace harsh saturated colors with a soft pastel palette." \
    --suggested-action "Define design tokens in theme.css" \
    --evolution-note "Initial discussion: user requested softer UI tones." \
    --sync-session
```

### Updating an Existing Issue (Mid-Session Evolution)

When requirements pivot or trade-offs are decided later in the session:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --update "workforces/issues/inbox/20260822-071500-adopt-soft-pastel-color-palette.md" \
    --evolution-note "Pivoted from lavender to muted alpine sage for WCAG contrast compliance." \
    --sync-session
```

### Rejecting an Issue / Idea (Explicit User Rejection)

When the user rejects an idea or says it's a bad direction, move it to `completed/` with `triage_status: "rejected"`:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --update "workforces/issues/inbox/20260822-071500-adopt-soft-pastel-color-palette.md" \
    --reject "User explicitly rejected this idea: out of scope for MVP." \
    --sync-session
```

### Checking for Similar Issues

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --find-similar "pastel color palette"
```

---

## Script Arguments

| Arg | Required | Values | Description |
|-----|----------|--------|-------------|
| `--title` | ✅ (for new) | string | Short, descriptive title |
| `--type` | | `bug` `debt` `design` `refactor` `security` `idea` | Category (default: `bug`) |
| `--severity` | | `P0` `P1` `P2` `P3` | Urgency / leverage estimate (default: `P2`) |
| `--reporter` | | string | Agent/workflow name that found it (default: `scribe`) |
| `--file` | | filepath | Affected file path (optional) |
| `--description` | ✅ (for new) | string | Full description of the problem or feature |
| `--suggested-action` | | string | Recommended fix or next step |
| `--session-id` | | string | Origin session sequence ID (e.g. `022`) |
| `--session-file` | | filepath | Origin session context note path |
| `--evolution-note` | | string | Decision note recording rationale or requirement pivot |
| `--update` | | filepath/slug | Existing issue file to update |
| `--reject` | | string | Mark issue as rejected, set `triage_status: 'rejected'`, and move to `completed/` |
| `--status` | | `inbox` `triaged` `completed` `rejected` | Update status (moves file to inbox/, triaged/, or completed/) |
| `--sync-session` | | flag | Automatically update session context frontmatter & list |
| `--find-similar` | | string | Search existing inbox, triaged & completed issues by title |
| `--force` | | flag | Bypass duplicate similarity check |

---

## Issue File Format

Issues are stored as Markdown files with YAML frontmatter:

```markdown
---
title: "Adopt soft pastel color palette"
type: "design"
severity: "P2"
reporter: "scribe"
reported_at: "2026-08-22T07:15:00"
updated_at: "2026-08-22T08:30:00"
status: "inbox"
file: "src/styles/theme.css"
session_id: "022"
session_file: "workforces/session-context/022_2026-08-22_theme-strategy.md"
triage_status: "pending"
github_issue: ~
---

# Adopt soft pastel color palette

**Type:** `design` | **Severity:** `P2` | **Reporter:** `scribe`  
**Reported:** 2026-08-22 07:15 | **Updated:** 2026-08-22 08:30  
**Origin Session:** [022_2026-08-22_theme-strategy.md](file:///path/to/workforces/session-context/022_2026-08-22_theme-strategy.md)  
**Affected file:** `src/styles/theme.css`

## Description

Replace harsh saturated colors with a soft pastel palette.

## Suggested Action

Define design tokens in theme.css with muted primary and surface tokens.

## 🧠 Session Lineage & Deciding Factors

- **2026-08-22 07:15:** Initial discussion: user requested softer UI tones.
- **2026-08-22 08:30:** Pivoted from lavender to muted alpine sage for WCAG contrast compliance.

---

## Triage (PM fills in)

- **Decision:** _pending_
- **Assigned to:** _pending_
- **GitHub Issue:** _pending_
- **Notes:** _pending_
```

---

## Triage Protocol (Project Manager)

When invoked for triage (via task tracker triage or during `/wf-sync`):

1. **Read all inbox files:** `workforces/issues/inbox/*.md`
2. **Review Session Context:** Read `session_file` and `## 🧠 Session Lineage & Deciding Factors` to understand the full rationale before prioritizing.
3. **Decide & Act:**
   - **P0/P1** → Create GitHub issue (including session link in description), add to `workstate.md`, move file to `triaged/`
   - **P2** → Add to `workstate.md` backlog with session link, move file to `triaged/`
   - **P3** → Log in `workstate.md` as backlog-only, move file to `triaged/`
   - **Wont-fix / Duplicate** → Mark in frontmatter, move to `triaged/`, no workstate entry
4. **Update frontmatter:**
   ```yaml
   triage_status: "triaged"
   github_issue: "#123"
   ```

---

## Integration Points

| System | How it connects |
|--------|----------------|
| `@scribe` agent | Automatically captures new ideas & evolves tracked issues mid-session |
| `session-context` skill | Maintains `tracked_issues` in frontmatter and links in body |
| `/wf-sync` | Project-manager reviews inbox and cross-session lineage during standups |
| `task-tracker` | Interactive reporting, listing, and triage for humans & agents |
| `project-manager` agent | Triages inbox into workstate & GitHub with session context |
| `programmer` & `designer` | Reports deferred code or design issues via `report-issue.py` |
| `post-code-review` | Appends unfixable findings to inbox automatically |
