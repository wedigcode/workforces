---
description: Report a deferred issue, bug, debt, or spontaneous feature idea to the inbox — then let the project-manager subagent triage it. Use when any agent or human finds something that can't be worked on right now.
---

# /task — Issue & Feature Reporting, Evolution, and Triage

Report any bug, design change, tech debt, or spontaneous feature idea to the workforce inbox with bidirectional session lineage. The `@scribe` tracks and evolves issues during conversations, and the `@project-manager` triages them into active work.

---

## Usage

```
/task                           → Show inbox summary + pending triage count
/task report                    → Interactive: report a new issue (guided prompts)
/task update [id|path]          → Update existing issue with requirement changes/evolution notes
/task triage                    → Invoke project-manager to triage all pending inbox items with session context
/task list                      → List all issues (inbox + triaged)
/task list --inbox              → Show only untriaged inbox items
/task list --type idea          → Filter by type: bug | debt | design | refactor | security | idea
/task list --severity P0        → Filter by severity: P0 | P1 | P2 | P3
```

---

## `/task report` — Interactive Reporting

When an agent or human runs `/task report`, gather the following:

1. **Title** — One sentence: what is the problem or feature idea? (required)
2. **Type** — `bug` | `debt` | `design` | `refactor` | `security` | `idea` (default: `bug`)
3. **Severity estimate** — P0–P3 (agent's best guess; PM will override)
4. **Affected file(s)** — Which file(s) are involved? (optional)
5. **Origin Session Context** — Active session sequence (e.g. `022`) or session note path (optional)
6. **Description** — Full context: what was found/discussed, where, why it matters
7. **Suggested action** — What should be done? (optional)
8. **Deciding factor / Evolution note** — Initial reasoning or requirement summary

Then call the script:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "[title]" \
    --type [type] \
    --severity [P0-P3] \
    --reporter [agent-name-or-human] \
    --session-id "[seq]" \
    --session-file "workforces/session-context/[seq]_[date]_[slug].md" \
    --file "[filepath]" \
    --description "[description]" \
    --suggested-action "[action]" \
    --evolution-note "[decision-note]" \
    --sync-session
```

**Confirm to the user:** `✅ Issue logged: workforces/issues/inbox/[filename].md (Linked to Session #[seq])`

---

## Updating Tracked Issues (Mid-Session Evolution)

When ideas or requirements change later in the conversation:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --update "[issue-path-or-slug]" \
    --evolution-note "Requirement pivot: [reason for change]" \
    --sync-session
```

---

## `/task triage` — PM Triage with Cross-Session Rationale

Invokes the `project-manager` as a subagent to process all pending inbox items:

1. Read all files in `workforces/issues/inbox/`
2. For each issue, the PM reviews the origin session context note and `## 🧠 Session Lineage & Deciding Factors` to understand the full history and trade-offs.
3. For each issue, the PM decides:

   | PM Decision | Action |
   |-------------|--------|
   | **P0/P1** | Create GitHub issue (with session link) → add to workstate → move to `triaged/` |
   | **P2** | Add to workstate backlog (with session link) → move to `triaged/` |
   | **P3** | Log in workstate backlog only → move to `triaged/` |
   | **Wont-fix / Duplicate** | Mark in frontmatter → move to `triaged/` → no workstate entry |

4. Present a triage summary table with origin session links and key rationales.
5. Ask for user approval before writing to workstate or creating GitHub issues.

---

## `/task list` — Browse Issues

Show a formatted table of issues. Default shows all (inbox + triaged):

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
```
