---
description: Update workforces toolkit — auto-patch .agents/ files, interactively discover & offer new/updated Team Packs, and review workspace changes
---

# /update-workforces — Workforces Updater

Updates the installed Workforces toolkit in the current project using the `workforce-management` skill. It automatically patches all toolkit files under `.agents/` (safe to overwrite), updates version info, and interactively prompts the user to discover, add, or update workspace Team Packs.

---

## When to Use

Run `/update-workforces` when:
- You want the latest agents, workflows, or skills.
- The upstream workforces repo has released changes or new Team Packs.
- You want to check if your install is current and offer team upgrades.

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

---

## Step 3 — Apply Toolkit Layer Updates

Execute the actual update script to prune obsolete toolkit assets and copy the latest files:

```bash
bash .agents/skills/workforce-management/scripts/update.sh ./ --non-interactive
```

This safely removes obsolete toolkit files from `.agents/` (while strictly preserving user-created files), overwrites active toolkit files with the latest versions, and updates `workforces/.version` and `workforces/.manifest.json`.

---

## Step 4 — Summary & Confirmation

Report what changed during the run in a structured layout:

```markdown
### ✅ Workforces Toolkit Layer Updated

**Toolkit (.agents/ & .agents/teams/):**
- Updated: X files
- Skipped: Y files (identical)
- Pruned: Z obsolete files

**Manifest & Version:** <old-hash> → <new-hash>
```

---

## Step 5 — Interactive Team Discovery & Installation / Update

After updating the core toolkit layer, **always interact with the user** to manage workspace teams:

1. **Scan Team Status:**
   - Inspect `.agents/teams/` to find all available Team Pack building blocks (`compliance`, `dev`, `growth`, `marketing`, `operations`, `sales`).
   - Check `workforces/workstate.md` and `workforces/teams/` to see which teams are already active/installed in the workspace.

2. **Interactively Prompt User:**
   - Present the user with the list of available teams:
     - **Uninstalled Teams Available:** (Teams in `.agents/teams/` not yet in `workforces/teams/`)
     - **Active Installed Teams:** (Teams currently active in `workforces/teams/`)
   - Ask the user directly (via chat or `ask_question` options):
     - *"Which new Team Packs would you like to build out for this project? (e.g. Sales, Marketing, Growth, Dev, Operations, Compliance)"*
     - *"Would you like to upgrade any of your existing active teams with the latest domain principles, personas, and SOP workflows?"*

3. **Build Out & Register Selected Teams:**
   - For any selected team, invoke `/teams add <team-name>` or synthesize full team assets inside `workforces/teams/<team-name>/` (`team.json`, `personas/`, `rules/`, `workflows/`).
   - Register newly instantiated teams in `workforces/workstate.md` under `## Active Teams`.
