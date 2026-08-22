---
trigger: always_on
---

# Rule: Continuous Session Context & Scribe Protocol

## Automatic Post-Interaction Context Updating

1. **Active Session File Identification:**
   - At the beginning of a conversation (or upon first substantive interaction), inspect `workforces/session-context/` to identify the active or newest session context note.
   - If starting a new session or topic, create the next sequential note (e.g. `022_2026-08-22_topic.md`).

2. **Post-Interaction Update Protocol:**
   - After any interaction with the human where product requirements, architectural choices, code changes, or tasks are modified or agreed upon:
   - Update the active `workforces/session-context/<seq>_<date>_<slug>.md` file with the updated summary, decisions ("why"), active file links, and task statuses.

3. **Spontaneous Ideas & Issue Tracking Protocol:**
   - When new feature ideas, bugs, design requirements, or technical debt items are discussed, capture them into `workforces/issues/inbox/` using `report-issue.py` with `--session-id`, `--session-file`, and `--sync-session`.
   - When requirements or trade-offs evolve later in the session, update the existing issue via `report-issue.py --update <path> --evolution-note "<reason>" --sync-session` to maintain an immutable history of deciding factors.
   - **Explicit User Rejections:** When the user explicitly rejects an idea ("bad idea", "reject that", "not needed", "out of scope"), do NOT delete the file or leave it pending in inbox. Execute `report-issue.py --update <path> --reject "<reason>" --sync-session` to archive it to `workforces/issues/completed/` with `triage_status: "rejected"` while preserving full audit history.

4. **Zero-Narrative Parsimony:**
   - Maintain dense, facts-only markdown formatting adhering to the `session-context` skill frontmatter and schema.
   - Never add conversational filler to session notes.

---

### 🚨 MANDATORY PRE-RESPONSE CHECKLIST
Before outputting your final text response after any interaction that modifies code, architectural decisions, product requirements, or roadmaps:
1. **Spontaneous Ideas & Issues Check:** If new feature ideas, roadmap phases, architectural concepts, bugs, or technical debt were discussed or proposed, you MUST execute:
   ```bash
   python3 .agents/skills/issue-tracker/scripts/report-issue.py \
       --title "<Title>" \
       --type [idea|bug|debt|design|refactor|security] \
       --severity [P0|P1|P2|P3] \
       --reporter <agent> \
       --session-id "<seq>" \
       --session-file "workforces/session-context/<seq>_<date>_<slug>.md" \
       --description "<Core problem & 10x value>" \
       --suggested-action "<Implementation plan & target workflow>" \
       --sync-session
   ```
   *(Fallback: `python3 skills/issue-tracker/scripts/report-issue.py ...`)*
   for each item BEFORE generating the final response.
2. **Session Context Update:** If not automatically created or updated by `report-issue.py --sync-session`, invoke `write_to_file` to create or update `workforces/session-context/<seq>_<date>_<slug>.md`.
3. **Lineage Verification:** Ensure all new or evolving issues appear in `tracked_issues` frontmatter and the session context note exists on disk before concluding the turn.

