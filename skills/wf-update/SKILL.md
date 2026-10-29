---
name: wf-update
description: Updates and recompiles the installed Workforces toolkit across active AI host environments (.agents/, .claude/, .grok/, .github/, .cursor/) using the wf-management toolkit management skill. Reach for this skill or trigger it when updating .agents/ files or multi-host installations, executing dry-run or live updates, checking version hashes, pruning obsolete assets, and interactively discovering or upgrading workspace Team Packs.
---
# Skill: /wf-update — Workforces Updater

Updates and recompiles the installed Workforces toolkit in the current project using the `wf-management` skill. It reads `workforces/config.json`, auto-detects any newly added AI host folders (`.agents/`, `.claude/`, `.grok/`, `.github/`, `.cursor/`), compiles host-native frontmatter, file extensions, relative links, and lifecycle hooks from canonical sidecar JSON + `config/hosts/*.json`, prunes obsolete assets, and interactively prompts to discover or update Team Packs.

---

## Usage

```
/wf-update                                → Update all active/detected AI hosts and review teams
/wf-update --dry                          → Preview changes in dry-run mode without modifying files
/wf-update --force                        → Force re-compilation regardless of version hash
/wf-update --hosts claude,copilot,cursor  → Target specific AI hosts (--editor alias supported)
/wf-update --no-auto-detect               → Update only saved hosts in workforces/config.json
/wf-update --non-interactive              → Run update without interactive prompts (for automation)
```

---

## When to Use

Run `/wf-update` when:
- You want the latest agents, rules, plugins, or skills compiled natively for your active AI host(s).
- You added another AI tool to the repository (e.g., `.claude/` or `.cursor/` alongside `.agents/`) and want Workforces auto-compiled into it.
- The upstream workforces repo has released updates, bug fixes, or new Team Packs.
- You want to migrate legacy `.github/copilot/` files to native `.github/{agents,instructions,skills,prompts}` layouts.

---

## Autonomous AI Agent Protocol

When the user invokes `/wf-update` or requests an update to the workforces toolkit:

### Step 1 — Read Current Version & Active Host Config

Inspect `workforces/.version` and `workforces/config.json` (if present) to retrieve the installed commit hash, date, active `hosts`, `auto_detect_hosts`, and `installed_teams`:

```
commit: abc1234
date:   2026-09-01
```

If `workforces/.version` or `workforces/config.json` does not exist yet, treat the installed version as "unknown" and proceed with auto-detection and fresh compilation.

### Step 2 — Fetch & Dry Run

Run the updater script from the active host toolkit directory (`.agents`, `.claude`, `.grok`, `.github`, `.cursor`, or `skills/`) in dry-run mode to inspect proposed changes before modifying any files:

```bash
bash .agents/skills/wf-management/scripts/update.sh ./ --dry --non-interactive
```
*(Multi-host / legacy fallbacks: `.claude/skills/wf-management/scripts/update.sh`, `.grok/skills/wf-management/scripts/update.sh`, `.github/skills/wf-management/scripts/update.sh`, `.cursor/skills/wf-management/scripts/update.sh`, `.github/copilot/skills/wf-management/scripts/update.sh`, or `skills/wf-management/scripts/update.sh`.)*

**Self-Healing Pre-`wf-` Bootstrap:** If `wf-management/scripts/update.sh` does not exist yet in any host directory (for example, after an older `workforce-management` install), bootstrap directly from a temporary upstream clone with `--force`:

```bash
tmp_wf="$(mktemp -d)" && git clone --depth=1 https://github.com/wedigcode/workforces.git "$tmp_wf" && bash "$tmp_wf/skills/wf-management/scripts/update.sh" ./ --force --non-interactive && rm -rf "$tmp_wf"
```

Review the dry-run output to determine:
- Active and newly detected AI hosts (`antigravity`, `claude`, `grok`, `copilot`, `cursor`)
- Files to be compiled/updated vs. skipped (identical)
- Obsolete files and orphaned hooks to be pruned

### Step 3 — Apply Multi-Host Toolkit Updates

Execute the update script to compile host-native assets, prune obsolete files/hooks, and update manifests:

```bash
bash .agents/skills/wf-management/scripts/update.sh ./ --non-interactive
```
*(Or the corresponding `.claude/`, `.grok/`, `.github/`, `.cursor/`, or `skills/` path detected in Step 2; append `--hosts <csv>` or `--no-auto-detect` if requested by the user.)*

This safely:
1. Compiles canonical sidecar JSON + Markdown into native frontmatter, extensions (`.agent.md`, `.instructions.md`, `.prompt.md`, `.mdc`), and rewritten relative links across all active AI hosts.
2. Compiles/merges native lifecycle hooks per host (`.agents/plugins/*/hooks.json`, non-destructive merge into `.claude/settings.json`, `.grok/hooks.json` + `.grok/plugins/*/`, clean skip on `copilot` & `cursor`).
3. Removes obsolete files recorded in `workforces/.manifest.json` (including legacy `.github/copilot/` and pre-`wf-` paths) and prunes deactivated `wf-*` hook entries without touching user hooks or custom files.
4. Persists `workforces/config.json`, `workforces/.manifest.json`, and `workforces/.version` while protecting workspace state in `workforces/`.

### Step 4 — Report Summary

Present a clean update summary to the user:

```markdown
### ✅ Workforces Toolkit Layer Updated

**Active Hosts:** `antigravity, claude`
- Compiled / Updated: X files
- Skipped: Y files (identical)
- Pruned: Z obsolete files

**Manifest & Version:** `<old-hash>` → `<new-hash>`
```

### Step 5 — Interactive Team Discovery & Installation / Update

After updating the core toolkit layer, check team status:

1. **Scan Team Status:**
   - Inspect `.agents/teams/` (or the active host's `teams/` directory / bundled `wf-management/hosts/teams.json`) to discover all available Team Packs (`compliance`, `dev`, `growth`, `marketing`, `operations`, `sales`, `social`, `design`, `launch`, `advisor`).
   - Read `workforces/config.json`, `workforces/workrules.md`, and `workforces/workstate.md` to see which teams are already active/installed in the workspace.

2. **Prompt the User:**
   - Surface available uninstalled teams and active installed teams.
   - Offer the user options to:
     - Install new Team Packs needed for upcoming milestones.
     - Upgrade existing active teams with the latest domain principles, personas, and SOP rules.

3. **Register Selected Teams:**
   - For newly selected teams, run:
     ```bash
     bash .agents/skills/wf-management/scripts/setup.sh ./ --teams <team-list> --non-interactive
     ```
   - Register newly instantiated teams in `workforces/workstate.md` under `## Active Teams`.

