---
name: session-context
description: Preserves transient conversation context, architectural decisions, rationale ("why"), and active task states across chat sub-sessions (`workforces/sessions/`). Reach for this skill when concluding long sessions to distill milestones, hydrating context when resuming a project after context truncation, tracking decision evolution across conversation boundaries, or searching historical session notes for past reasoning.
---
# Session Context Skill

Provides transient, cross-session memory preservation to prevent context loss, reasoning drift, and lost specs when transitioning between chat sessions or when long context windows truncate.

---

## Triggering & Agent Actions

Session context operations run automatically via `@scribe` hooks and can also be triggered directly through natural conversation:

- **Save Context**: User says *"Save session context on [topic]"* or agent automatically distills session at milestones.
- **List Sessions**: User asks *"Show recent sessions"* or *"List past session notes"*.
- **Load / Hydrate Context**: User says *"Recall session 040"* or *"Look at what we discussed earlier"*.
- **Search Notes**: User asks *"Search session history for [query]"*.

---

## Surface & Storage

| Surface | Path | Schema / Structure |
|---------|------|-------------------|
| **Session Notes** | `workforces/session-context/<seq>_<date>_<slug>.md` | Markdown with Open Session Format frontmatter |
| **Tracked Tasks** | `workforces/tasks/` | YAML-frontmatter tasks & action items linked to origin sessions |
| **Index / Directory** | `workforces/session-context/` | Numerically indexed & timestamped notes |

---

## 1. File Format & Schema

Every session context file stored under `workforces/session-context/` MUST adhere to the following schema:

```markdown
---
session_id: "001"
sequence: 1
created_at: 2026-08-05T16:20:00Z
updated_at: 2026-08-05T16:20:00Z
topic: Feature Brief & Task Breakdown
tags: [feature-name, brief, architecture, tasks]
active_files:
  - path/to/relevant/file.ts
parent_session_id: null
tracked_tasks:
  - id: "20260805-162000-feature-brief-task"
    file: "workforces/tasks/20260805-162000-feature-brief-task.md"
    title: "Feature Brief & Task"
    type: "follow-up"
    priority: "P1"
    status: "todo"
---

# Session 001: <Topic Title>

## 🎯 Executive Summary & Product Brief
- High-level objective and core requirements defined during session.

## 🧠 Decisions & Reasoning ("Why")
- **Decision:** Why option A was chosen over option B.
- **Rejected:** Trade-offs and reasons for rejecting alternatives.

## 📋 Tracked Tasks & Action Items
- [Feature Brief & Task](file:///absolute/path/to/workforces/tasks/20260805-162000-feature-brief-task.md) (`follow-up` | P1) — Initial formulation and core acceptance criteria.

## 📁 Key Files & Code Symbols
- [file.py](file:///absolute/path/to/file.py#L10-L40) — Core logic modified/discussed

## 🔑 Keywords & Scanning Hooks
`keyword1`, `keyword2`, `tag1`, `topic_name`
```

---

## 2. Sequence & File Naming Protocol

1. **Scan Existing Files:**
   Look in `workforces/session-context/` for files matching `[0-9]{3}_*.md`.
2. **Calculate Next Sequence:**
   - If empty/none exist: sequence = 1 (`001`).
   - If max existing sequence is N: sequence = N + 1 (formatted zero-padded `003`).
3. **Format Filename:**
   `<seq>_<YYYY-MM-DD>_<kebab-case-slug>.md`
   Example: `001_2026-08-05_session-context-design.md`

---

## 3. Continuous Task Tracking & Decision Evolution Protocol

During any session:
1. **Task & Idea Capture:** When an action item, follow-up, feature request, design choice, or bug is discussed, invoke `report-task.py` with `--session-id`, `--session-file`, and `--sync-session`.
2. **Dynamic Evolution & Status Transitions:** When requirements pivot or tasks move through their lifecycle (`--start`, `--block`, `--done`, `--drop`), invoke `report-task.py --update <path> --evolution-note "<reason>" --sync-session` so the task's `## 🧠 Session Lineage & Deciding Factors` and the session note stay synchronized.

---

## 4. Operations & Protocols

### A. Saving Context
1. Spawns `@scribe` subagent (or executes directly) to distill current session into Open Session Format.
2. Traverses current session trajectory for:
   - Executive Summary / Product Brief
   - Architectural Decisions & Constraints ("Why")
   - Discovered Issues & Feature Ideas (`idea`, `bug`, `design`, `debt`, `refactor`)
   - Mid-session Decision Evolutions & Requirement Pivots
   - Active Files & Key Symbols
   - Keywords / Indexing Tags
3. Correlates and updates or reports issues via `report-task.py`:
   - Updates existing session issues if requirements evolved (`--update ... --evolution-note ...`).
   - Reports new issues with bidirectional links (`--session-file ... --sync-session`).
4. Calculates sequence number and writes `workforces/session-context/<seq>_<YYYY-MM-DD>_<slug>.md`.
5. Returns confirmation summary:
   ```markdown
   ✅ Session context saved to `workforces/session-context/022_2026-08-22_topic.md` (Session #22)
   📋 Tracked Issues: 2 issues linked
   ```

### B. Listing Contexts
1. Reads all files in `workforces/session-context/*.md`.
2. Parses frontmatter (`sequence`, `created_at`, `topic`, `tags`, `tracked_tasks`).
3. Renders structured list:
   ```markdown
   ## 📜 Session Context History

   | Sequence | Date | Topic | Tags | Tracked Issues | File |
   |:---:|:---:|:---|:---|:---:|:---|
   | #022 | 2026-08-22 | Scribe Issue Tracker Integration | `[scribe, issues]` | 2 | [022_...md](file:///path/to/022.md) |
   | #021 | 2026-08-21 | Refero Design Overhaul | `[design, refero]` | 1 | [021_...md](file:///path/to/021.md) |
   ```

### C. Loading Context
1. Matches `<seq|slug>` against existing session files (e.g., `22`, `022`, `slug`).
2. Reads contents using `view_file`.
3. Extracts `🎯 Executive Summary & Product Brief`, `🧠 Decisions & Reasoning ("Why")`, and `📋 Tracked Tasks & Action Items`.
4. Hydrates current session context memory with target session details and tracked issue links.

### D. Keyword Searching
1. Searches YAML frontmatter `tags`, `topic`, and `Keywords & Scanning Hooks` section across all session notes.
2. Uses `grep_search` to query `workforces/session-context/` for exact terms, tags, or file references.
3. Displays matching session titles, sequence numbers, snippet context, and linked issues.

---

## 5. Automatic Context Hydration Rule

When a user prompt references past conversations (e.g., *"Look at what we were just talking about"*, *"In the last session..."*, or *"Based on session 1"*):
1. Auto-invoke session keyword search or inspect the highest sequence note in `workforces/session-context/`.
2. Load and present the relevant context before executing new instructions.

---

## 6. Mandatory Pre-Response Checklist

Before outputting your final text response after any interaction that modifies code, architectural decisions, or task requirements:
1. You MUST invoke `write_to_file` to create or update `workforces/session-context/<seq>_<date>_<slug>.md`.
2. Do NOT declare the turn complete or reply to the user until the session context note exists on disk.
