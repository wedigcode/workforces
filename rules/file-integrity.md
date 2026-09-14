---
trigger: always_on
---

# File Reference & Task Lineage Protocol

Enforces reference lineage, zero broken links, subtask tracking, and adaptive gap discovery across all workforce agents.

---

## 1. Zero Ghost References
- **Strict Invariant**: Every referenced file path or markdown link (`[text](path)`) MUST exist on disk.
- If a created file references a target that does not exist, immediately create the target file with structured content.

## 2. Task Tracking, Session Lineage & Completion Gates
- Whenever new feature horizons, dependencies, unhandled risks, or tasks (`- [ ]`) are discussed:
- Report each item to `workforces/tasks/` via `report-task.py` with `--session-id`, `--session-file`, and `--sync-session`.
- `workforces/tasks/*.md` is the authoritative single source of truth; `workstate.md` is a projected dashboard synchronized by tooling.
- **Completion Gate**: Never declare a parent task or turn complete until all immediate child files, assets, dependent tasks, and session records are satisfied and persisted to disk.

## 3. Decision Escalation Threshold (Stop & Ask)
- Major or breaking architectural discoveries (auth breaks, DB schema mutations, brand strategy pivots) require an immediate halt:
  1. STOP execution immediately.
  2. Formulate 2–3 structured trade-offs.
  3. Present to the user and wait for approval before proceeding.

## 4. Automated & Manual Validation
- Run reference audits via:
  ```bash
  python3 .agents/skills/workforce-management/scripts/validate-references.py ./ --fix
  ```
  *(Fallback: `python3 skills/workforce-management/scripts/validate-references.py ./ --fix`)*
