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

If you are an AI assistant (such as Antigravity, Claude Code, VS Code Copilot, or Grok Build) tasked with installing this toolkit:

1. **Clone the Repo:** Clone this repository (`https://github.com/wedigcode/workforces.git`) to a temporary path.
2. **Detect Target & Environment:**
   - Inspect the target project directory to detect the correct editor:
     - If `.gemini/` or `GEMINI.md` exists, use `--editor antigravity` (uses `.agents/`).
     - If `.vscode/` or `copilot` config exists, use `--editor vscode` (uses `.github/copilot/`).
     - If `CLAUDE.md` exists, use `--editor claude` (uses `.claude/`).
     - If `.grok/skills`, `.grok/commands`, or `.grok/agents` already exist, use `--editor grok` (uses `.grok/`; workflows install as `commands/`). Do not treat a lone `AGENTS.md` as a Grok signal. See [Grok Build](grok.md).
3. **Execute Non-Interactively:** Run the setup script using the `--non-interactive` flag:
   ```bash
   bash /tmp/workforces/skills/workforce-management/scripts/setup.sh <target-path> --editor <detected-editor> --type project --non-interactive
   ```
4. **Configure rules & preferences:** Edit `workforces/workrules.md` inside the target project to configure `github_usernames` and set formatting rules under `## AI Preferences` reflecting the host capabilities and guidelines.

---

## Setup Options

```bash
# Specify target editor (auto-detects by default)
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor antigravity   # Antigravity/Gemini (uses .agents/)
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor vscode        # VS Code + Copilot (uses .github/copilot/)
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor claude        # Claude Code (uses .claude/)
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor grok          # Grok Build (uses .grok/; workflows → commands/)

# Specify repository role
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --type project         # Standard project codebase
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --type workforce       # Central coordinator tracking multiple projects

# Greenfield Site Setup (for new websites, SaaS apps, or landing pages)
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --site-setup           # Initializes docs/product-brief.md and workforces/images.json
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --skip-site-setup      # Skips site setup initialization

```

---

## Installed Components

| Location in Target | Contents |
|--------------------|----------|
| `<editor-dir>/agents/` | Subagent personas with standardized Antigravity frontmatter (e.g. `project-manager.md`) |
| `<editor-dir>/skills/` | Modular capability directories containing `SKILL.md` and supporting tools (e.g. `wf-plan/`, `workforce-management/`) |
| `<editor-dir>/rules/` | Global behavioral rules and constraints (e.g. `base.md`) |
| `<editor-dir>/hooks.json` | Native lifecycle hooks (`PreToolUse` for code-graph, `PostToolUse` for post-code-review) |
| `<editor-dir>/plugins/` | Domain plugin bundles (e.g. `workforce-programming-plugin`) |
| `workforces/` | Workspace configurations: objectives, states, version info, and `tmp/` scratch directory |
| `.gitignore` | Automatically includes `workforces/tmp`, `workforces/code-graph.json`, and `workforces/knowledge-catalog` to prevent committing generated local artifacts |

---

## Updating

Update the toolkit files by running the update script from your installed `workforce-management` skill:

```bash
# Run a preview dry-run
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry

# Apply updates (prunes obsolete workflows and updates skills/hooks)
bash .agents/skills/workforce-management/scripts/update.sh ./

# Grok Build (toolkit lives under .grok/)
bash .grok/skills/workforce-management/scripts/update.sh ./ --dry
```

Or ask your AI assistant *"Update the workforces toolkit"* to execute the updater interactively.
