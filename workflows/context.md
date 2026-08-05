---
description: Transient session context manager — save, list, load, and search session notes across sub-sessions
---

# /context — Session Context Manager

Preserves transient chat context, architectural decisions, and product briefs across sub-sessions. Prevents loss of rationale when moving between chats.

**Agent:** `@scribe` (see `agents/scribe.md`)  
**Skill:** `session-context` (see `skills/session-context/SKILL.md`)

---

## Usage

```
/context                     → Show active session context & recent notes list
/context save [topic]        → Distill current session & save next sequential note (e.g. 001_...)
/context list                → List all saved session notes numerically with topics and tags
/context load [seq|slug]     → Hydrate specific past session context into current prompt memory
/context search [query]      → Ripgrep keywords and frontmatter tags across session notes
```

---

## Commands & Workflows

### 1. `/context save [topic]`
1. Spawns `@scribe` agent.
2. Traverses current session trajectory for:
   - Executive Summary / Product Brief
   - Architectural Decisions & Constraints ("Why")
   - Tasks Created / Workstate References
   - Active Files & Key Symbols
   - Keywords / Indexing Tags
3. Scans `workforces/session-context/` for highest sequence number `N`.
4. Writes `workforces/session-context/<seq>_<YYYY-MM-DD>_<slug>.md` where `<seq>` is `N+1` zero-padded (e.g., `002`).
5. Returns confirmation summary:
   ```markdown
   ✅ Session context saved to `workforces/session-context/002_2026-08-05_topic.md` (Session #2)
   ```

### 2. `/context list`
1. Reads all markdown files in `workforces/session-context/`.
2. Extracts sequence, date, topic, and tags.
3. Renders structured list:

```markdown
## 📜 Session Context History

| Sequence | Date | Topic | Tags | File |
|:---:|:---:|:---|:---|:---|
| #002 | 2026-08-05 | Net Pay Calculation Logic | `[pay, symfony]` | [002_2026-08-05_net-pay.md](file:///path/to/002_2026-08-05_net-pay.md) |
| #001 | 2026-08-05 | Session Context Design | `[context, scribe]` | [001_2026-08-05_session-context.md](file:///path/to/001_2026-08-05_session-context.md) |
```

### 3. `/context load [seq|slug]`
1. Locates target file matching sequence number (e.g., `1`, `001`) or slug substring in `workforces/session-context/`.
2. Reads contents using `view_file`.
3. Extracts `🎯 Executive Summary & Product Brief` and `🧠 Decisions & Reasoning ("Why")`.
4. Hydrates current session context memory with target session details.

### 4. `/context search [query]`
1. Uses `grep_search` to query `workforces/session-context/` for exact terms, tags, or file references.
2. Displays matching session titles, sequence numbers, and snippet context.

---

## Auto-Recall Protocol

If the user says:
- *"Look at what we were just talking about"*
- *"Pull context from session X"*
- *"Based on our last session..."*

The workforce automatically runs `/context search` or `/context load` to reclaim relevant context before responding.
