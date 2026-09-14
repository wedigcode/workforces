---
trigger: always_on
---

# Continuous Session Context & Scribe Protocol

Ensures conversation milestones, architectural rationale, and active task states are continuously persisted.

---

## 1. Post-Interaction Updates
- **Active Note Identification**: Inspect `workforces/session-context/` to identify the active session note, or create the next sequential note (e.g. `053_...`).
- **Post-Turn Synchronization**: After any interaction modifying code, architectural choices, product specs, or tasks, update `workforces/session-context/<seq>_<date>_<slug>.md`.
- **Zero-Narrative Parsimony**: Keep notes dense, factual, and devoid of conversational filler.

---

## 2. Mandatory Pre-Response Checklist

Before outputting your final text response after modifying code, architecture, or requirements:

1. **Spontaneous Ideas & Tasks Check**: If new action items, feature ideas, bugs, or technical debt were proposed, execute:
   ```bash
   python3 .agents/skills/task-tracker/scripts/report-task.py \
       --title "<Title>" --type [tag] --priority [P0|P1|P2|P3] \
       --reporter <agent> --session-id "<seq>" \
       --session-file "workforces/session-context/<seq>_<date>_<slug>.md" \
       --description "<Problem & Value>" --suggested-action "<Plan>" --sync-session
   ```
   *(Fallback: `python3 skills/task-tracker/scripts/report-task.py ...`)*
2. **Session Context Update**: Ensure `workforces/session-context/<seq>_<date>_<slug>.md` is updated.
3. **Lineage Verification**: Verify new tasks appear in frontmatter `tracked_tasks`.
