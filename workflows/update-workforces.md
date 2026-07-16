---
description: Update workforces toolkit — auto-patch .agents/ files and review workspace changes
---

# /update-workforces — Workforces Updater

Updates the installed Workforces toolkit in the current project using the `workforce-management` skill. It automatically patches all toolkit files under `.agents/` (safe to overwrite) and updates the version info.

---

## When to Use

Run `/update-workforces` when:
- You want the latest agents, workflows, or skills.
- The upstream workforces repo has released changes.
- You want to check if your install is current.

---

## Step 1 — Read Current Version

Read `workforces/.version` to get the installed commit hash:

```
commit: abc1234
date:   2026-02-10
```

If the file doesn't exist, treat the installed hash as "unknown" and proceed with a full overwrite of `.agents/`.

---

## Step 2 — Fetch & Dry Run

Run the updater script in dry-run mode first to check what files will be updated:

```bash
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry --non-interactive
```

If the command reports that the toolkit is already up to date, report this to the user and stop.

---

## Step 3 — Apply Toolkit Layer Updates

Execute the actual update script to copy the latest files:

```bash
bash .agents/skills/workforce-management/scripts/update.sh ./ --non-interactive
```

This overwrites all `.agents/` files (agents, workflows, skills, rules) with the latest versions and updates the version hash inside `workforces/.version`.

---

## Step 4 — Summary & Confirmation

Report what changed during the run in a structured layout:

```markdown
### ✅ Workforces Updated

**Toolkit (.agents/):**
- Updated: X files
- Skipped: Y files (identical)

**Version:** <old-hash> → <new-hash>
```
