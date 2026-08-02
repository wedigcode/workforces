---
name: integrity-validator
description: File reference, link lineage, and subtask integrity validator for workforces. Scans markdown and configuration files to ensure zero broken links, no ghost references, and tracked pending subtasks.
---

# Integrity Validator Skill

This skill enforces strict file reference integrity across workforces and projects.

## Capabilities

1. **Reference Validation:** Audits all relative and markdown file links to verify target files exist on disk.
2. **Auto-Fixing:** Creates stub files for ghost references when invoked with `--fix`.
3. **Pending Subtask Extraction:** Scans tasks (`- [ ]` items) and reports pending dependencies into project tracking logs.

## Usage

```bash
python3 skills/workforce-management/scripts/validate-references.py ./ --fix
```
