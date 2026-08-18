---
trigger: always_on
---

# File Reference & Task Lineage Protocol

Every AI agent and workforce orchestrator MUST enforce complete reference lineage, zero broken links, full subtask tracking, and adaptive gap discovery.

---

## 1. Zero Ghost References

- Whenever creating or editing a file (`.md`, `.json`, `.yaml`, etc.), **every referenced file path or artifact link MUST exist on disk**.
- If a created file references another file (e.g. `[link text](file:///path/to/file)`, `personas/*.md`, `rules/*.md`, `workflows/*.md`, `workforces/...`), the agent MUST:
  1. Check if the target file exists on disk.
  2. If it does NOT exist, **immediately create the target file** with complete, structured content.

## 2. Subtask & Discovered Gap Tracking

- When a created file or execution step mentions required follow-ups, pending dependencies, unhandled risks, or unchecked tasks (`- [ ]` items):
  - The agent MUST report the issue to the **issue inbox** using `report-issue.py`:
    ```bash
    python3 .agents/skills/issue-tracker/scripts/report-issue.py \
        --title "[Brief title]" \
        --type [bug|debt|design|refactor|security|idea] \
        --severity [P0|P1|P2|P3] \
        --reporter [agent-name] \
        --description "[What was found and why it matters]" \
        --suggested-action "[Recommended next step]"
    ```
    *(Fallback: `python3 skills/issue-tracker/scripts/report-issue.py` if running inside source toolkit root)*
  - **Do NOT** write freeform gap notes into `workforces/workstate.md` sections (`## Pending Dependencies & Tasks` or `## Unforeseen Risks & Discovered Gaps`). The inbox is the single source of truth for discovered issues.
  - `workforces/workstate.md` is reserved for **active task tracking** (tasks the team is currently executing), not gap discovery. The project-manager promotes inbox items to workstate during triage.
  - The agent MUST NOT declare a main task complete until all immediate child dependencies (files, assets) referenced in created files are generated and satisfied.

## 3. Decision Escalation Threshold (Stop & Ask Rule)

- If during execution, an overlooked dependency or architectural conflict is discovered that constitutes a **Major / Breaking Issue** (e.g. auth flow break requiring OAuth integration, major DB schema mutation, or missing brand strategy choices):
  1. **STOP EXECUTION IMMEDIATELY.** Do not attempt to guess or bypass user intent on major decisions.
  2. Formulate 2–3 structured decision options with trade-offs.
  3. Present the options to the user (via interactive question modal or question formulation workflow) and wait for explicit user approval before resuming work.

## 4. Automated Validation Guardrail & Hooks

- **Automated Hook Execution:** When `workforce-integrity-plugin` is active, the system automatically triggers validation via `post_tool_call` hooks upon file mutations (`write_to_file`, `replace_file_content`, `multi_replace_file_content`).
- **Session Lineage Enforcement:** The hook verifies that active session context files exist in `workforces/session-context/`. If mutations occur without session context recording, a warning is raised.
- **Manual Verification:** After creating or modifying team packs, plans, PRDs, or major documentation, run:
  ```bash
  python3 .agents/skills/workforce-management/scripts/validate-references.py ./ --fix
  ```
  *(Fallback: `python3 skills/workforce-management/scripts/validate-references.py ./ --fix`)*
- Ensure 0 dangling references exist and active session context is saved before presenting completion summaries to the user.
