---
name: workforce-management
description: Toolkit setup, updates, team installation, reference-counted pruning, and configuration management for workforces.
---

# Skill: Workforce Management

Manage the lifecycle of the Workforces toolkit, including setup, automated updates, modular team pack installation, reference-counted pruning/uninstallation, configuration tuning, and preferences mapping.

## Principles

- **Zero Dependency:** The toolkit should operate purely via standard shell tools (`bash`, `git`, `find`, `cp`, `diff`) and standard Python 3. No external package installs.
- **Toolkit Layer Isolation:** The AI runtime configuration, personas, workflows, and rules live under the editor configuration folder (`.agents/`, `.github/copilot/`, or `.claude/`). These are treated as a "read-only" toolkit layer and are safe to overwrite or prune.
- **Workspace Layer Ownership:** User configuration and state live under the `workforces/` directory in the project root. This folder contains:
  - `workrules.md` (fully user-owned preferences and rules)
  - `workstate.md` (runtime state and tracked parameters)
  - `goals/` (user goals and execution blueprints)
  - `personas/` (custom project voice profiles and target audience cards)
  - `knowledge-catalog/` (project-specific documentation and OKF catalog)
  - `.version` (tracking file for installed version hash)
- **Reference-Counted Pruning:** When removing a team pack, shared dependencies (skills, rules, workflows, plugins) required by remaining active teams are automatically preserved.
- **Context & Persona Retention:** Workspace persona cards, custom tone definitions, and historical team context in `workforces/` are preserved by default when uninstalled.
- **Non-Interactive Mode Support:** The installation and update scripts support command-line arguments to allow an AI agent to run them autonomously without blocking for user confirmation prompts.

## Files Structure

When installed, the project root contains:
```
.agents/               ← Read-only toolkit layer (safe to overwrite or prune)
├── agents/            ← Subagent prompt definitions (e.g. project-manager.md, programmer.md)
├── workflows/         ← Slash commands (e.g. work.md, teams.md)
├── skills/            ← Reusable skill directories (e.g. workforce-management/)
├── rules/             ← Enforced rules (e.g. base.md, clean-coder.md)
└── teams/             ← Installed Team Pack manifests (e.g. dev/pack.json)

workforces/            ← Workspace layer (user config, personas, and state)
├── README.md          ← Local workspace overview
├── workrules.md       ← AI priorities, installed_teams, and custom rules
├── workstate.md       ← Target repository configuration and run markers
├── personas/          ← User project voice profiles and target audience cards
├── goals/             ← Local planning files
└── .version           ← Current installed commit/version metadata
```

## Commands & Scripts

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
