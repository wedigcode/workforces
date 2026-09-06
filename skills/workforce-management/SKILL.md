---
name: workforce-management
description: Manages the lifecycle, installation, updates, and configuration of the Workforces toolkit across multi-editor environments (.agents/, .github/copilot/, .claude/, .grok/). Reach for this skill when installing modular team packs (e.g., dev, marketing, sales), safely pruning unused team configurations with reference-counted dependency resolution, updating core toolkit files, or adjusting workspace settings.
---
# Skill: Workforce Management

Manage the lifecycle of the Workforces toolkit, including setup, automated updates, modular team pack installation, reference-counted pruning/uninstallation, configuration tuning, and preferences mapping.

---

## Triggering & Execution

Triggered via conversational requests or directly using the underlying CLI automation scripts:

### Prompt Triggers
- *"Install [team-name] team pack"* (e.g. marketing, sales, dev, growth, compliance)
- *"Uninstall / prune [team-name] team"* (safely removes unused agents and rules while retaining shared dependencies)
- *"List installed teams and active agents"*
- *"Update the workforces toolkit"* (runs `update.sh` dry-run and updates `.agents/`)
- *"Synthesize a custom team for [domain]"*

### Script Commands
```bash
# Team Pack Management:
bash .agents/skills/workforce-management/scripts/setup.sh ./ --teams <team-name>
python3 .agents/skills/workforce-management/scripts/prune-team.py <team-name>

# Toolkit Updates:
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry --non-interactive
bash .agents/skills/workforce-management/scripts/update.sh ./ --non-interactive
```

---

## Principles

- **Zero Dependency:** The toolkit operates purely via standard shell tools (`bash`, `git`, `find`, `cp`, `diff`) and standard Python 3. No external package installs.
- **Toolkit Layer Isolation:** The AI runtime configuration, personas, skills, and rules live under the editor configuration folder (`.agents/`, `.github/copilot/`, `.claude/`, or `.grok/` for Grok Build). These are treated as a "read-only" toolkit layer and are safe to overwrite or prune.
- **Workspace Layer Ownership:** User configuration and state live under the `workforces/` directory in the project root:
  - `workrules.md` (user-owned preferences and rules)
  - `workstate.md` (runtime state and tracked parameters)
  - `goals/` (user goals and execution blueprints)
  - `personas/` (custom project voice profiles and target audience cards)
  - `knowledge-catalog/` (project-specific documentation and OKF catalog)
  - `.version` (tracking file for installed version hash)
  - `.manifest.json` (tracking manifest of installed toolkit files for safe obsolete asset pruning)
- **Reference-Counted Pruning:** When removing a team pack, shared dependencies (skills, rules, plugins) required by remaining active teams are automatically preserved.
- **Obsolete File Cleanup & User Asset Protection:** When updating the toolkit, obsolete files previously installed by Workforces are safely removed, while user-created files and custom directories in `.agents/` are strictly protected.
- **Context & Persona Retention:** Workspace persona cards, custom tone definitions, and historical team context in `workforces/` are preserved by default when uninstalled.
- **Non-Interactive Mode Support:** The installation and update scripts support command-line arguments to allow an AI agent to run them autonomously without blocking for user confirmation prompts.

---

## Installing an Upstream Team Pack

When you need capabilities for a new domain (e.g. adding `@marketer` via `marketing`, or `@social` via `social`):

1. **Register in Configuration**: Add team name to `installed_teams` in `workforces/workrules.md`.
2. **Sync Team Assets**:
   ```bash
   bash .agents/skills/workforce-management/scripts/setup.sh ./ --teams <team-name>
   ```
   *(Or run `bash .agents/skills/workforce-management/scripts/update.sh ./` to re-sync all configured teams).*
   The installer reads `teams/<team>/pack.json` and copies agents, rules, skills, and manifests.
3. **Update Workstate**: Register the newly installed team under `## Active Teams` in `workforces/workstate.md`.

---

## Uninstalling & Pruning a Team

When a domain team is no longer needed, uninstall it to eliminate runtime prompt bloat:

1. **Run the Pruner**:
   ```bash
   python3 .agents/skills/workforce-management/scripts/prune-team.py <team-name>
   ```
   *(Use `--dry` to preview changes without deleting files, or `--purge-data` to remove workspace folders in `workforces/teams/<team>/`).*
2. **Shared Dependencies Preserved**: Any skill, rule, or plugin required by another active team is automatically kept.
3. **Workspace Personas Preserved**: User business personas in `workforces/personas/` are retained by default.

---

## Toolkit Layer Updates Protocol

1. **Read Current Version**: Inspect `workforces/.version` to get the installed commit hash.
2. **Fetch & Dry Run**:
   ```bash
   bash .agents/skills/workforce-management/scripts/update.sh ./ --dry --non-interactive
   ```
3. **Apply Updates**:
   ```bash
   bash .agents/skills/workforce-management/scripts/update.sh ./ --non-interactive
   ```
4. **Summary**: Report updated, skipped, and pruned file counts.
5. **Interactive Team Discovery**: Prompt the user to discover, add, or upgrade workspace Team Packs.

---

## CLI Commands & Scripts

### 1. Setup & Installation
```bash
bash skills/workforce-management/scripts/setup.sh ./ --editor <editor> --type <type> --teams <teams>
```

### 2. Updating Toolkit
```bash
bash skills/workforce-management/scripts/update.sh ./
```

### 3. Pruning & Uninstalling Teams (`prune-team.py`)
```bash
# Safely prune unneeded team while preserving shared dependencies and workspace personas
python3 skills/workforce-management/scripts/prune-team.py <team-name>

# Preview changes without modifying files
python3 skills/workforce-management/scripts/prune-team.py <team-name> --dry

# Hard wipe including workspace data folder
python3 skills/workforce-management/scripts/prune-team.py <team-name> --purge-data
```
