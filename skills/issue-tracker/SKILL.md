---
name: issue-tracker
description: |
  Lightweight deferred-issue capture system for workforce agents. Any agent or workflow
  that finds a bug, design problem, tech debt item, or idea it cannot address immediately
  can call report-issue.py to log it to the inbox. The project-manager subagent then
  triages the inbox, assigns priority, and promotes to workstate or GitHub issues.
  The inbox is surfaced in /work and /work sync.
---

# Issue Tracker

A structured pipeline for deferring issues discovered during agent execution — without losing them or blocking the current task.

## When to Use

- An agent finds a bug but is mid-task and can't stop to fix it
- `/clean` or `post-code-review` spots tech debt not worth fixing right now
- The `@designer` flags a design anti-pattern in a component not currently being edited

- A security vulnerability is found that requires separate attention
- An idea surfaces during execution that belongs in the backlog

---

## Core Concepts

### The Inbox (`workforces/issues/inbox/`)

Unstructured, untriaged issues written directly by agents. Any agent can append to the inbox immediately — no approval or judgment required at report time.

### Triaged (`workforces/issues/triaged/`)

Issues that the project-manager has reviewed and either:
- Promoted to `workstate.md` as a P0/P1/P2/P3 task
- Created as a GitHub issue (P0/P1)
- Marked as `wont-fix` or `duplicate`

---

## How to Report an Issue (from any agent)

Use `run_command` to call the script:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "Dead code in utils.py" \
    --type bug \
    --severity P2 \
    --reporter clean-coder \
    --file src/utils.py \
    --description "Found unreachable function calculate_legacy_tax() at line 47. Zero callers." \
    --suggested-action "Remove the function and its test stub."
```

### Arguments

| Arg | Required | Values | Description |
|-----|----------|--------|-------------|
| `--title` | ✅ | string | Short, descriptive title |
| `--type` | | `bug` `debt` `design` `refactor` `security` `idea` | Category (default: `bug`) |
| `--severity` | | `P0` `P1` `P2` `P3` | Estimated urgency (default: `P2`) |
| `--reporter` | | string | Agent/workflow name that found it (default: `unknown`) |
| `--file` | | filepath | Affected file path |
| `--description` | ✅ | string | Full description of the problem |
| `--suggested-action` | | string | What the PM/dev should do about it |

### When to Estimate Severity

| Severity | Meaning |
|----------|---------|
| `P0` | Critical — production broken, security hole, or data loss risk |
| `P1` | High — actively hurts users or blocks a major task |
| `P2` | Medium — should be fixed, not urgent (most common) |
| `P3` | Low — nice to have, minor improvement, or idea |

> **Note:** The project-manager makes the final severity call. Report your best estimate — it's just a hint.

---

## Triage Protocol (Project Manager)

When invoked for triage (via `/task triage` or during `/work sync`):

1. **Read all inbox files:** `workforces/issues/inbox/*.md`
2. **For each issue, decide:**
   - **P0/P1** → Create GitHub issue immediately, add to `workstate.md`, move file to `triaged/`
   - **P2** → Add to `workstate.md` backlog, move file to `triaged/`
   - **P3** → Log in `workstate.md` as backlog-only, move file to `triaged/`
   - **Wont-fix / Duplicate** → Mark in frontmatter, move to `triaged/`, no workstate entry

3. **Update each issue file frontmatter** before moving it:
   ```yaml
   triage_status: triaged    # was: pending
   github_issue: "#123"      # or ~ if none
   ```

4. **Report back** a triage summary.

---

## Issue File Format

Issues are stored as Markdown files with YAML frontmatter:

```markdown
---
title: "Dead code in utils.py"
type: bug
severity: P2
reporter: clean-coder
reported_at: 2026-08-13T05:00:00
status: inbox
file: "src/utils.py"
triage_status: pending
github_issue: ~
---

# Dead code in utils.py

**Type:** `bug` | **Severity:** `P2` | **Reporter:** `clean-coder`
...
```

---

## Integration Points

| System | How it connects |
|--------|----------------|
| `/work` | Step 2 checks inbox count and surfaces "⚠️ N issues pending triage" |
| `/work sync` | Project-manager reviews inbox as part of sync session |
| `/task` | Slash command for humans and agents to report issues interactively |
| `project-manager` agent | Triages inbox on demand or during sync |
| `programmer` agent | Reports deferred code issues via `report-issue.py` |
| `designer` agent | Reports deferred design issues via `report-issue.py` |
| `post-code-review` | Appends unfixable findings to inbox automatically |

