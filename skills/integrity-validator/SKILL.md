---
name: integrity-validator
description: Audits markdown documents, JSON manifests, and configuration files for broken relative links, dangling file paths, ghost references to non-existent assets, and uncompleted subtask checkboxes. Reach for this skill during quality gate checks, before git commits or releases, when verifying file lineage after moving or refactoring documentation, or when ensuring zero dead links across project docs.
---
# Skill: Integrity Validator & Reference Auditor

Enforces strict file reference integrity across workforces and projects. Scans all markdown files (`.md`) and JSON manifests (`.json`) to audit link integrity, detect dangling references, extract unchecked subtasks, and auto-generate missing dependency files.

Operates as an automated static analysis utility and lifecycle hook, eliminating the need for manual auditing agents or pseudo-personas.

---

## Triggering & Execution

This skill operates primarily through automated lifecycle execution and deterministic CLI tooling, as well as on-demand quality gate checks:

### 1. Automated Lifecycle Hook (Continuous Enforcement)
Configured via `plugins/workforce-integrity-plugin/hooks.json` to automatically execute on `PostToolUse` whenever files are created or modified (`write_to_file`, `replace_file_content`, `multi_replace_file_content`):
```bash
python3 skills/workforce-management/scripts/validate-references.py ./ --fix
```
This guarantees zero ghost references and self-healing link lineage in real time without human or agent overhead.

### 2. Quality Gate & Pre-Commit Execution
Run directly via CLI during release gates, pre-commit checks, or refactor audits:
```bash
python3 .agents/skills/workforce-management/scripts/validate-references.py ./ --fix
```
*(Fallback: `python3 skills/workforce-management/scripts/validate-references.py ./ --fix`)*

### 3. Conversational Prompts
- *"Verify reference integrity and broken links"*
- *"Check for ghost references across docs and skills"*
- *"Audit file lineage and extract pending subtasks"*

---

## Capabilities

1. **Reference Validation:** Audits all relative and markdown file links to verify target files exist on disk.
2. **Auto-Fixing:** Creates stub files for ghost references when invoked with `--fix`.
3. **Pending Subtask Extraction:** Scans tasks (`- [ ]` items) and reports pending dependencies into project tracking logs.

---

## Execution Protocol

### Step 1 — Run Reference & Lineage Audit
Execute the validator script in fix mode to scan all files and auto-create missing dependency files:
```bash
python3 .agents/skills/workforce-management/scripts/validate-references.py ./ --fix
```
*(Fallback: `python3 skills/workforce-management/scripts/validate-references.py ./ --fix`)*

### Step 2 — Update Work State Tracker
Read the audit output and update `workforces/workstate.md`:
1. Append any unresolved subtasks under `## Pending Dependencies & Tasks`.
2. Clear resolved dependencies.

### Step 3 — Report Completion Summary
Output a summary showing:
- Total files audited.
- Broken references fixed/created.
- Pending subtasks logged in `workforces/workstate.md`.
