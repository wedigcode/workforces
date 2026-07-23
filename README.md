# Workforces

A lean, portable AI toolkit containing agent personas, slash-command workflows, reusable skills, and behavioral rules.

---

## Workforce vs. Project

When installing this toolkit, you'll choose a **type** that describes the role of the target repository:

### Project (`--type project`)
A **standard codebase** where you're doing the actual work — writing code, shipping features, fixing bugs. Most repos fall into this category (e.g. a web app, API service, or internal tool).

Installing the toolkit into a project repo gives your AI assistant full context about that codebase: its goals, GitHub queue, and team preferences. The `workforces/` workspace folder tracks state and goals *scoped to that project*.

### Workforce (`--type workforce`)
A **central coordinator repo** that tracks and manages multiple project repos. It's not where code gets written — it's the command center. A workforce-type install is appropriate when the repo's purpose is to orchestrate tasks, maintain shared knowledge, or manage cross-project planning across an entire team or product portfolio.

> **In short:** a *project* is where work happens; a *workforce* is what coordinates across many projects.

---

## Toolkit Structure

When installed, the toolkit separates static agent assets (the **Toolkit Layer**) from your runtime states and configurations (the **Workspace Layer**):

```
.agents/               ← Toolkit Layer (automatically updated, read-only)
├── agents/            ← Specialist agent personas (e.g., project-manager.md)
├── workflows/         ← Slash-command workflows (e.g., work.md)
├── skills/            ← Reusable skill modules (e.g., workforce-management/)
└── rules/             ← Always-on rules (e.g., base.md)

workforces/            ← Workspace Layer (user-owned configuration and state)
├── README.md          ← Workspace overview
├── workrules.md       ← User configurations, settings, and response preferences
├── workstate.md       ← Workspace tracking state
├── goals/             ← RICE-scored blueprints and goals
└── team-sync/         ← YYYY-MM-DD.md files documenting standups and syncs
```

---

## Installation Guide

### For AI Assistants (Autopilot Install)
If you are an AI assistant (Antigravity, Claude Code, or VS Code Copilot) tasked with installing this repo:
1. Clone this repository to `/tmp/workforces`.
2. Inspect the host environment and run:
   ```bash
   bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor <editor-type> --type <repo-type> --non-interactive
   ```
   *Replace `<editor-type>` with `antigravity`, `vscode`, or `claude` depending on the user's workspace profile, and `<repo-type>` with `project` or `workforce`.*
3. Configure the user's response preferences inside `workforces/workrules.md` under `## AI Preferences`.

### For Humans (Manual Install)
```bash
git clone https://github.com/wedigcode/workforces.git /tmp/workforces
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./
rm -rf /tmp/workforces
```
For more setup options and environment configuration, see the [Setup Guide](docs/setup.md).

---

## Core Components

### Skills
| Skill | Description |
|-------|-------------|
| [`memory-management`](skills/memory-management/SKILL.md) | Protocol for navigating OKF catalogs and managing workspace memories |
| [`github-project-planning`](skills/github-project-planning/SKILL.md) | Create/update GitHub issues and interact with Project V2 boards |
| [`workforce-management`](skills/workforce-management/SKILL.md) | Update, patch, and align settings for the Workforces toolkit |
| [`feature-research`](skills/feature-research/SKILL.md) | Research-first pipeline: gap analysis, PRD, and work breakdown across projects |

### Workflows
| Command | Workflow | Description |
|---------|----------|-------------|
| `/work` | [`work`](workflows/work.md) | Scans GitHub queue, surfaces top active tasks, handles completion |
| `/work sync` | [`sync`](workflows/sync.md) | Aligns on wins, losses, next goals, and blockers; logs daily syncs |
| `/work plan` | [`project-management`](workflows/project-management.md) | Strategic gap analysis, task generation, and issue scheduling |
| `/feature` | [`feature`](workflows/feature.md) | Multi-phase feature scoping, gap analysis, PRD generation, and task breakdown |
| `/update-workforces` | [`update-workforces`](workflows/update-workforces.md) | Dry-run, patch toolkit layer files, and summarize updates |

---

## Updating

Update the installed toolkit using the built-in update workflow:

```bash
# Preview modifications
bash .agents/skills/workforce-management/scripts/update.sh ./ --dry

# Apply updates
bash .agents/skills/workforce-management/scripts/update.sh ./
```

Or ask your AI assistant: `/update-workforces`.
