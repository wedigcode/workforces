---
description: Report a deferred issue, bug, debt, or idea to the inbox — then let the project-manager subagent triage it. Use when any agent or human finds something that can't be worked on right now.
---

# /task — Issue Reporting & Triage

Report any issue, bug, design problem, tech debt, or idea to the workforce inbox. The project-manager subagent decides if it's worth addressing and when.

---

## Usage

```
/task                           → Show inbox summary + pending triage count
/task report                    → Interactive: report a new issue (guided prompts)
/task triage                    → Invoke project-manager to triage all pending inbox items
/task list                      → List all issues (inbox + triaged)
/task list --inbox              → Show only untriaged inbox items
/task list --type bug           → Filter by type: bug | debt | design | refactor | security | idea
/task list --severity P0        → Filter by severity: P0 | P1 | P2 | P3
```

---

## `/task report` — Interactive Reporting

When an agent or human runs `/task report`, gather the following:

1. **Title** — One sentence: what is the problem? (required)
2. **Type** — `bug` | `debt` | `design` | `refactor` | `security` | `idea` (default: `bug`)
3. **Severity estimate** — P0–P3 (agent's best guess; PM will override)
4. **Affected file(s)** — Which file(s) are involved? (optional)
5. **Description** — Full context: what was found, where, why it matters
6. **Suggested action** — What should be done? (optional)

Then call the script:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "[title]" \
    --type [type] \
    --severity [P0-P3] \
    --reporter [agent-name-or-human] \
    --file "[filepath]" \
    --description "[description]" \
    --suggested-action "[action]"
```

**Confirm to the user:** `✅ Issue logged: workforces/issues/inbox/[filename].md`

---

## `/task triage` — PM Triage

Invokes the `project-manager` as a subagent to process all pending inbox items:

1. Read all files in `workforces/issues/inbox/`
2. For each issue, the PM decides:

   | PM Decision | Action |
   |-------------|--------|
   | **P0/P1** | Create GitHub issue → add to workstate → move to `triaged/` |
   | **P2** | Add to workstate backlog → move to `triaged/` |
   | **P3** | Log in workstate backlog only → move to `triaged/` |
   | **Wont-fix / Duplicate** | Mark in frontmatter → move to `triaged/` → no workstate entry |

3. Present a triage summary table
4. Ask for user approval before writing to workstate or creating GitHub issues

---

## `/task list` — Browse Issues

Show a formatted table of issues. Default shows all (inbox + triaged):

```markdown
### 📋 Issue Tracker

#### ⏳ Inbox (Pending Triage) — 3 items

| File | Title | Type | Severity | Reporter | Age |
|------|-------|------|----------|---------|-----|
| 20260813-... | Dead code in utils.py | debt | P2 | clean-coder | 2h |

#### ✅ Triaged — 12 items

| Title | Type | Priority | Decision | GitHub |
|-------|------|----------|----------|--------|
| Fix login race condition | bug | P1 | → workstate | #45 |
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

## For Agents — Quick Reference

Any agent that discovers something it can't fix now should use `run_command`:

```bash
# From within any agent or workflow — minimal required args:
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "Brief title of the issue" \
    --description "What you found, where, and why it matters." \
    --reporter my-agent-name \
    --severity P2 \
    --type bug
```

**Rule:** Report and move on. Do NOT stop your current task to fix a deferred issue. The PM will handle prioritization.

---

## Storage Layout

```
workforces/
  issues/
    inbox/          ← Unreviewed. Written directly by agents.
      YYYYMMDD-HHMMSS-<slug>.md
    triaged/        ← Reviewed by PM. Includes decision + GitHub link.
      YYYYMMDD-HHMMSS-<slug>.md
```

Issues are plain Markdown files with YAML frontmatter — readable by humans, parseable by scripts, surfaced in `/work` and `/work sync`.
