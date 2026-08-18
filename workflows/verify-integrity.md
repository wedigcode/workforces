---
description: Verify file references, link integrity, and extract pending subtasks across workspace files
---

# /verify-integrity — Workspace Reference & Task Lineage Auditor

Scans all workspace markdown files (`.md`) and JSON manifests (`.json`) to audit link integrity, detect dangling references, extract unchecked subtasks, and auto-generate missing dependency files.

> 💡 **Native Agent**: Run natively via `@compliance` or CLI: `jetski --agent compliance`


---

## When to Use

Run `/verify-integrity` when:
- You created or updated documentation, plans, PRDs, or team packs and want to ensure 0 broken links.
- You want to verify that all files referenced in manifests or markdown files exist on disk.
- You want to extract pending `- [ ]` subtasks into `workforces/workstate.md`.

---

## Step 1 — Run Reference & Lineage Audit

Execute the validator script in fix mode to scan all files and auto-create missing dependency files:

```bash
python3 .agents/skills/workforce-management/scripts/validate-references.py ./ --fix
```

---

## Step 2 — Update Work State Tracker

Read the audit output and update `workforces/workstate.md`:
1. Append any unresolved subtasks under `## Pending Dependencies & Tasks`.
2. Clear resolved dependencies.

---

## Step 3 — Report Completion Summary

Output a summary showing:
- Total files audited.
- Broken references fixed/created.
- Pending subtasks logged in `workforces/workstate.md`.
