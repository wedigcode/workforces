---
trigger: always_on
---

# Rule: Continuous Session Context & Scribe Protocol

## Automatic Post-Interaction Context Updating

1. **Active Session File Identification:**
   - At the beginning of a conversation (or upon first substantive interaction), inspect `workforces/session-context/` to identify the active or newest session context note.
   - If starting a new session or topic, create the next sequential note (e.g. `002_2026-08-05_topic.md`).

2. **Post-Interaction Update Protocol:**
   - After any interaction with the human where product requirements, architectural choices, code changes, or tasks are modified or agreed upon:
   - Update the active `workforces/session-context/<seq>_<date>_<slug>.md` file with the updated summary, decisions ("why"), active file links, and task statuses.

3. **Zero-Narrative Parsimony:**
   - Maintain dense, facts-only markdown formatting adhering to the `session-context` skill frontmatter and schema.
   - Never add conversational filler to session notes.

---

### 🚨 MANDATORY PRE-RESPONSE CHECKLIST
Before outputting your final text response after any interaction that modifies code, architectural decisions, or task requirements:
1. You MUST invoke `write_to_file` to create or update `workforces/session-context/<seq>_<date>_<slug>.md`.
2. Do NOT declare the turn complete or reply to the user until the session context note exists on disk.

