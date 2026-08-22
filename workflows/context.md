---
description: Transient session context manager — save, list, load, and search session notes across sub-sessions with tracked issues and decision evolution
---

# /context — Session Context Manager

Preserves transient chat context, architectural decisions, product briefs, and spontaneous feature ideas across sub-sessions. Prevents loss of rationale and forgotten tasks when moving between chats or when context windows truncate.

**Agent:** `@scribe` (see `agents/scribe.md`)  
**Skills:** `session-context` (see `skills/session-context/SKILL.md`), `issue-tracker` (see `skills/issue-tracker/SKILL.md`)

---

## Usage

```
/context                     → Show active session context & recent notes list
/context save [topic]        → Distill current session, capture/update issues, and save next sequential note
/context list                → List all saved session notes numerically with topics, tags, and tracked issues
/context load [seq|slug]     → Hydrate specific past session context and tracked issues into current prompt memory
/context search [query]      → Ripgrep keywords, tags, and tracked issues across session notes
```

---

## Commands & Workflows

### 1. `/context save [topic]`
1. Spawns `@scribe` agent.
2. Traverses current session trajectory for:
   - Executive Summary / Product Brief
   - Architectural Decisions & Constraints ("Why")
   - Discovered Issues & Feature Ideas (`idea`, `bug`, `design`, `debt`, `refactor`)
   - Mid-session Decision Evolutions & Requirement Pivots
   - Active Files & Key Symbols
   - Keywords / Indexing Tags
3. Correlates and updates or reports issues via `report-issue.py`:
   - Updates existing session issues if requirements evolved (`--update ... --evolution-note ...`).
   - Reports new issues with bidirectional links (`--session-file ... --sync-session`).
4. Writes `workforces/session-context/<seq>_<YYYY-MM-DD>_<slug>.md`.
5. Returns confirmation summary:
   ```markdown
   ✅ Session context saved to `workforces/session-context/022_2026-08-22_topic.md` (Session #22)
   📋 Tracked Issues: 2 issues linked
   ```

### 2. `/context list`
1. Reads all markdown files in `workforces/session-context/`.
2. Extracts sequence, date, topic, tags, and tracked issues count.
3. Renders structured list:

```markdown
## 📜 Session Context History

| Sequence | Date | Topic | Tags | Tracked Issues | File |
|:---:|:---:|:---|:---|:---:|:---|
| #022 | 2026-08-22 | Scribe Issue Tracker Integration | `[scribe, issues]` | 2 | [022_...md](file:///path/to/022.md) |
| #021 | 2026-08-21 | Refero Design Overhaul | `[design, refero]` | 1 | [021_...md](file:///path/to/021.md) |
```

### 3. `/context load [seq|slug]`
1. Locates target file matching sequence number (e.g., `22`, `022`) or slug substring in `workforces/session-context/`.
2. Reads contents using `view_file`.
3. Extracts `🎯 Executive Summary & Product Brief`, `🧠 Decisions & Reasoning ("Why")`, and `📋 Tracked Issues & Feature Ideas`.
4. Hydrates current session context memory with target session details and tracked issue links.

### 4. `/context search [query]`
1. Uses `grep_search` to query `workforces/session-context/` for exact terms, tags, or file references.
2. Displays matching session titles, sequence numbers, snippet context, and linked issues.

---

## Auto-Recall Protocol

If the user says:
- *"Look at what we were just talking about"*
- *"Pull context from session X"*
- *"Based on our last session..."*

The workforce automatically runs `/context search` or `/context load` to reclaim relevant context before responding.
