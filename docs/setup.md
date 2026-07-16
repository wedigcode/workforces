# Setup Guide

This guide describes how to install and update the Workforces AI toolkit in any target project repository.

---

## Quick Install (For Humans)

Clone the Workforces repository to a temporary folder and run the setup script pointing to your target project root:

```bash
git clone https://github.com/wedigcode/workforces.git /tmp/workforces
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./
rm -rf /tmp/workforces
```

---

## Quick Install (For AI Agents)

If you are an AI assistant (such as Antigravity, Claude Code, or VS Code Copilot) tasked with installing this toolkit:

1. **Clone the Repo:** Clone this repository (`https://github.com/wedigcode/workforces.git`) to a temporary path.
2. **Detect Target & Environment:**
   - Inspect the target project directory to detect the correct editor:
     - If `.gemini/` or `GEMINI.md` exists, use `--editor antigravity` (uses `.agents/`).
     - If `.vscode/` or `copilot` config exists, use `--editor vscode` (uses `.github/copilot/`).
     - If `CLAUDE.md` exists, use `--editor claude` (uses `.claude/`).
3. **Execute Non-Interactively:** Run the setup script using the `--non-interactive` flag:
   ```bash
   bash /tmp/workforces/skills/workforce-management/scripts/setup.sh <target-path> --editor <detected-editor> --type project --non-interactive
   ```
4. **Configure rules & preferences:** Edit `workforces/workrules.md` inside the target project to configure `github_usernames` and set formatting rules under `## AI Preferences` reflecting the host capabilities and guidelines.

---

## Setup Options

```bash
# Specify target editor (auto-detects by default)
bash setup.sh ./ --editor antigravity   # Antigravity/Gemini (uses .agents/)
bash setup.sh ./ --editor vscode        # VS Code + Copilot (uses .github/copilot/)
bash setup.sh ./ --editor claude        # Claude Code (uses .claude/)

# Specify repository role
bash setup.sh ./ --type project         # Standard project codebase (recommends local git-exclude)
bash setup.sh ./ --type workforce       # Central coordinator tracking multiple projects
```

---

## Installed Components

| Location in Target | Contents |
|--------------------|----------|
| `<editor-dir>/agents/` | Persona configurations (e.g. `project-manager.md`) |
| `<editor-dir>/workflows/` | Workflow slash commands (e.g. `work.md`, `update-workforces.md`) |
| `<editor-dir>/skills/` | Modular capability directories containing `SKILL.md` and supporting tools (e.g. `workforce-management/`) |
| `<editor-dir>/rules/` | Global rules and constraints (e.g. `base.md`, `token-parsimony.md`) |
| `workforces/` | Workspace configurations: objectives, states, and version info |

---

## Updating

Update the toolkit files by running the update script from your installed `workforce-management` skill:

```bash
# Run a preview dry-run
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry

# Apply updates
bash .agents/skills/workforce-management/scripts/update.sh ./
```

Or trigger `/update-workforces` inside your AI agent chat to execute the workflow interactively.
