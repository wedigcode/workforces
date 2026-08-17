---
name: workforce-management
description: Toolkit setup, updates, and configuration management for workforces.
---

# Skill: Workforce Management

Manage the lifecycle of the Workforces toolkit, including setup, automated updates, configuration tuning, and preferences mapping.

## Principles

- **Zero Dependency:** The toolkit should operate purely via standard shell tools (`bash`, `git`, `find`, `cp`, `diff`) and the GitHub CLI (`gh`). No external package installs.
- **Toolkit Layer Isolation:** The AI runtime configuration, personas, workflows, and rules live under the editor configuration folder (`.agents/`, `.github/copilot/`, or `.claude/`). These are treated as a "read-only" toolkit layer and are safe to overwrite.
- **Workspace Layer Ownership:** User configuration and state live under the `workforces/` directory in the project root. This folder contains:
  - `workrules.md` (fully user-owned preferences and rules)
  - `workstate.md` (runtime state and tracked parameters)
  - `goals/` (user goals and execution blueprints)
  - `knowledge-catalog/` (project-specific documentation and OKF catalog)
  - `.version` (tracking file for installed version hash)
- **Non-Interactive Mode Support:** The installation and update scripts must support command-line arguments to allow an AI agent to run them autonomously without blocking for user confirmation prompts.

## Files Structure

When installed, the project root contains:
```
.agents/               ← Read-only toolkit layer (safe to overwrite during update)
├── agents/            ← Personas (e.g. project-manager.md, brand-strategist.md)
├── workflows/         ← Slash commands (e.g. work.md, teams.md)
├── skills/            ← Reusable skill directories (e.g. workforce-management/)
├── rules/             ← Enforced rules (e.g. base.md, brand-voice.md)
└── teams/             ← Installed Team Pack manifests (e.g. brand-marketing/team.json)

workforces/            ← Workspace layer (user config and state)
├── README.md          ← Local workspace overview
├── workrules.md       ← AI priorities, installed_teams, and custom rules
├── workstate.md       ← Target repository configuration and run markers
├── goals/             ← Local planning files
└── .version           ← Current installed commit/version metadata
```

## AI Installation & Configuration Protocol

If an AI agent is instructed to "install" this toolkit:
1. **Clone the Source Repo:** Clone the workforces repository to a temporary directory.
2. **Execute setup.sh:** Run `bash skills/workforce-management/scripts/setup.sh ./ --editor <editor> --type <type> --teams <teams>`.
   - Use `--editor antigravity` to use the `.agents/` folder.
   - Use `--type project` for standard project targets.
   - Use `--type workforce` for parent command repositories tracking child projects.
   - Use `--teams brand-marketing,sales-outreach` or `--teams all` to equip specialized Team Packs.
3. **Align Preferences:** Query the user (or inspect their active workspace) to set the custom AI priorities and team configs under `## Installed Teams` in `workforces/workrules.md`.

