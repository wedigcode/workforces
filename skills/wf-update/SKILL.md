---
name: wf-update
description: Updates the installed Workforces toolkit in the current project using the workforce-management skill. Reach for this skill or trigger it when updating .agents/ files, executing dry-run or live updates, checking version hashes, pruning obsolete assets, and interactively discovering or upgrading workspace Team Packs.
---
# Skill: /wf-update — Workforces Updater

Updates the installed Workforces toolkit in the current project using the `workforce-management` skill. It automatically patches all toolkit files under `.agents/` (safe to overwrite), updates version info, and interactively prompts the user to discover, add, or update workspace Team Packs.

---

## Usage

```
/wf-update                     → Update toolkit and interactively discover/update teams
/wf-update --dry               → Preview changes in dry-run mode without modifying files
/wf-update --force             → Force re-sync of all toolkit files regardless of version hash
/wf-update --non-interactive   → Run update without interactive prompts (for automation)
```

---

## When to Use

Run `/wf-update` (or `/update-workforces`) when:
- You want the latest agents, rules, plugins, or skills.
- The upstream workforces repo has released updates, bug fixes, or new Team Packs.
- You want to check if your project installation is current and review team upgrades.

---

## Autonomous AI Agent Protocol

When the user invokes `/wf-update` or requests an update to the workforces toolkit:

### Step 1 — Read Current Version

Inspect `workforces/.version` to retrieve the installed commit hash and date:

```
commit: abc1234
date:   2026-09-01
```

If the file does not exist, treat the installed version as "unknown" and proceed with a fresh sync.

### Step 2 — Fetch & Dry Run

Run the updater script in dry-run mode to inspect proposed changes before modifying any files:

```bash
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry --non-interactive
```
*(Fallback: `bash skills/workforce-management/scripts/update.sh ./ --dry --non-interactive`)*

Review the dry-run output to determine:
- Files to be updated (new or modified in toolkit)
- Files to be skipped (identical)
- Obsolete files to be pruned

### Step 3 — Apply Toolkit Layer Updates

Execute the actual update script to apply changes, prune obsolete assets, and update manifests:

```bash
bash .agents/skills/workforce-management/scripts/update.sh ./ --non-interactive
```
*(Fallback: `bash skills/workforce-management/scripts/update.sh ./ --non-interactive`)*

This safely:
1. Overwrites core toolkit files in `.agents/` (or target editor directory).
2. Removes obsolete files previously recorded in `workforces/.manifest.json`.
3. Strictly protects user-created custom files in `.agents/` and workspace state in `workforces/`.
4. Updates `workforces/.version` and `workforces/.manifest.json`.

### Step 4 — Report Summary

Present a clean update summary to the user:

```markdown
### ✅ Workforces Toolkit Layer Updated

**Toolkit Files (.agents/):**
- Updated: X files
- Skipped: Y files (identical)
- Pruned: Z obsolete files

**Manifest & Version:** `<old-hash>` → `<new-hash>`
```

### Step 5 — Interactive Team Discovery & Installation / Update

After updating the core toolkit layer, check team status:

1. **Scan Team Status:**
   - Inspect `.agents/teams/` (or `teams/`) to discover all available Team Packs (`compliance`, `dev`, `growth`, `marketing`, `operations`, `sales`, `social`, `design`, `launch`, `advisor`).
   - Read `workforces/workstate.md` and `workforces/teams/` to see which teams are already active/installed in the workspace.

2. **Prompt the User:**
   - Surface available uninstalled teams and active installed teams.
   - Offer the user options to:
     - Install new Team Packs needed for upcoming milestones.
     - Upgrade existing active teams with the latest domain principles, personas, and SOP rules.

3. **Register Selected Teams:**
   - For newly selected teams, run:
     ```bash
     bash .agents/skills/workforce-management/scripts/setup.sh ./ --teams <team-name>
     ```
   - Register newly instantiated teams in `workforces/workstate.md` under `## Active Teams`.
