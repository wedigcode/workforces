# Workforces

A lean collection of AI agent skills, workflows, and rules. When installed, everything lives in a `workforces/` directory inside your project.

---

## Structure

```
workforces/           ← installed repo root
├── skills/           ← reusable skill modules (SKILL.md)
├── workflows/        ← slash-command workflows
├── agents/           ← agent personas (by department)
├── rules/            ← always-on behavioral rules
│
├── memory/           ← runtime: skill config + state (gitignored in projects)
│   └── <skill-name>.md
└── knowledge-catalog/ ← runtime: OKF project knowledge base (you own this)
```

**`memory/`** — written by skills. Stores config (IDs, tokens, usernames) and state (last-synced, last-run).  
**`knowledge-catalog/`** — written by you and your project agents. OKF-formatted knowledge about your systems, APIs, and data.

---

## Core Components

### Skills

| Skill | Description |
|-------|-------------|
| [`memory-management`](skills/memory-management/SKILL.md) | Protocol for reading/writing skill memory and navigating OKF knowledge catalogs |
| [`github-project-planning`](skills/github-project-planning/SKILL.md) | Create GitHub Issues, manage Projects V2 boards, set custom fields |

### Workflows

| Workflow | Command | Description |
|----------|---------|-------------|
| [`work`](workflows/work.md) | `/work` | GitHub queue + top task surface + planning handoff |
| [`project-management`](workflows/project-management.md) | `/work plan` | Gap analysis → task generation → GitHub issue creation |

### Agents

| Agent | Path | Role |
|-------|------|------|
| Project Manager | [`agents/project-manager.md`](agents/project-manager.md) | Strategic planning: generates, scores, and sequences work |

---

## Quick Start

1. Run `/work` — on first run it will ask for your GitHub username and set up `workforces/workrules.md` and `workforces/workstate.md`
2. Run `/work plan` — connects to GitHub Projects V2 (will guide you through setup on first run)

---

## Design Notes

- **No SDKs.** Everything is markdown + YAML + `gh` CLI.
- **Skill memory** lives in `workforces/memory/<skill>.md` — plain markdown, human-readable.
- **Knowledge catalog** is OKF format: each file has YAML frontmatter (`type`, `description`, `tags`) + markdown body. AI navigates it progressively via `index.md`.
- **Plugins:** Subcommands like `/work retro`, `/work metrics`, `/work goals` are not built yet — they'll be added as plugins.

---

## Setup Notes

> During first config, the agent will ask how you like your AI responses (e.g. keep it short, no bullet points, under 100 words). This gets written to `workforces/workrules.md` under `## AI Preferences`.
