---
name: session-context
description: Manages transient session notes and context preservation across chat sub-sessions. Actively tracks issues and spontaneous feature ideas, maintains decision evolution history, and preserves bidirectional lineage across sessions. Use when saving context before closing a session, loading past session context, or scanning session notes by sequence or keywords.
---

# Session Context Skill

Provides transient, cross-session memory preservation to prevent context loss, reasoning drift, and lost specs when transitioning between chat sessions or when long context windows truncate.

---

## Surface & Storage

| Surface | Path | Schema / Structure |
|---------|------|-------------------|
| **Session Notes** | `workforces/session-context/<seq>_<date>_<slug>.md` | Markdown with Open Session Format frontmatter |
| **Tracked Issues** | `workforces/issues/inbox/` | YAML-frontmatter issues linked to origin sessions |
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
tracked_issues:
  - id: "20260805-162000-feature-brief-task"
    file: "workforces/issues/inbox/20260805-162000-feature-brief-task.md"
    title: "Feature Brief & Task"
    type: "idea"
    severity: "P2"
    status: "inbox"
---

# Session 001: <Topic Title>

## 🎯 Executive Summary & Product Brief
- High-level objective and core requirements defined during session.

## 🧠 Decisions & Reasoning ("Why")
- **Decision:** Why option A was chosen over option B.
- **Rejected:** Trade-offs and reasons for rejecting alternatives.

## 📋 Tracked Issues & Feature Ideas
- [Feature Brief & Task](file:///absolute/path/to/workforces/issues/inbox/20260805-162000-feature-brief-task.md) (`idea` | P2) — Initial formulation and core acceptance criteria.

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

## 3. Continuous Issue Tracking & Decision Evolution Protocol

During any session:
1. **Idea & Issue Capture:** When a new idea, feature request, design choice, or bug is discussed, invoke `report-issue.py` with `--session-id`, `--session-file`, and `--sync-session`.
2. **Dynamic Evolution:** When earlier decisions or specs pivot (e.g. changing color from red to pastel, or changing database strategy), invoke `report-issue.py --update <path> --evolution-note "<reason>" --sync-session` so the issue's `## 🧠 Session Lineage & Deciding Factors` stays current.

---

## 4. Operations & Protocols

### A. Saving Context (`/context save [topic]`)
1. Invoke the `scribe` sub-agent to distill the current conversation into the Open Session Format.
2. Calculate the sequence number.
3. Write the formatted file to `workforces/session-context/<seq>_<date>_<slug>.md`.
4. Return a 1-line confirmation with file path and session number.

### B. Listing Contexts (`/context list`)
1. Read all files in `workforces/session-context/*.md`.
2. Parse frontmatter (`sequence`, `created_at`, `topic`, `tags`, `tracked_issues`).
3. Output a summary table sorted by sequence descending.

### C. Loading Context (`/context load <seq|slug>`)
1. Match `<seq|slug>` against existing session files (e.g. `1` or `001` or `dedup`).
2. Read target session note.
3. Extract `Executive Summary`, `Decisions & Reasoning`, and `Tracked Issues`.
4. Inject extracted context directly into active prompt memory.

### D. Keyword Searching (`/context search <query>`)
1. Search YAML frontmatter `tags`, `topic`, and `Keywords & Scanning Hooks` section across all session notes.
2. Return matching session IDs, sequence numbers, and summaries.

---

## 5. Automatic Context Hydration Rule

When a user prompt references past conversations (e.g., *"Look at what we were just talking about"*, *"In the last session..."*, or *"Based on session 1"*):

1. Auto-invoke `/context search` or inspect the highest sequence note in `workforces/session-context/`.
2. Load and present the relevant context before executing new instructions.

---

## 6. Mandatory Pre-Response Checklist

Before outputting your final text response after any interaction that modifies code, architectural decisions, or task requirements:
1. You MUST invoke `write_to_file` to create or update `workforces/session-context/<seq>_<date>_<slug>.md`.
2. Do NOT declare the turn complete or reply to the user until the session context note exists on disk.
