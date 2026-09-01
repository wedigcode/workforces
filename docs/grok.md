# Grok Build

Workforces can install into [Grok Build](https://x.ai/cli) the same way it installs into Antigravity, Claude Code, and VS Code Copilot.

```bash
git clone https://github.com/wedigcode/workforces.git /tmp/workforces
bash /tmp/workforces/skills/workforce-management/scripts/setup.sh ./ --editor grok --type project --non-interactive
rm -rf /tmp/workforces
```

Then start a new Grok session in the target project so it picks up `.grok/` and `AGENTS.md`.

---

## Layout

| Path | Role |
|------|------|
| `.grok/agents/` | Specialist personas |
| `.grok/commands/` | Slash-command workflows (not `workflows/`) |
| `.grok/skills/` | Skill directories (`SKILL.md` + scripts) |
| `.grok/rules/` | Always-on rules |
| `AGENTS.md` | Project context (created if missing) |
| `workforces/` | Workspace layer (same as other hosts) |

Grok discovers project slash commands as flat `*.md` files under `.grok/commands/`. The filename stem is the command name (`wf-work.md` → `/wf-work`).

---

## Command Namespace & Collision Avoidance

All Workforces workflows use the standard `wf-` prefix natively across all platforms to prevent collisions with host-reserved keywords (such as Grok's built-in `/plan`, `/context`, and `/workflows`):

| Workforces Command | Role |
|---------------------|------|
| `/wf-work` | Workforce Orchestrator & Task Execution Center |
| `/wf-plan` | Phased Project Planner & Estimates |
| `/wf-sync` | Multi-Mode Meeting & Standup Sync |
| `/wf-context` | Scribe Session Context Manager |
| `/wf-update` | Toolkit Updater |
| `/wf-advisor` | Strategic Advisory & Problem Discovery |
| `/wf-task` | Universal Task Tracker |

Grok’s own `/plan` stays plan mode. Grok’s `/context` stays the token meter. Grok’s `/workflows` remains Grok’s native Rhai runner.

---

## Auto-detect

`setup.sh` / `update.sh` treat the host as Grok only when `.grok/skills`, `.grok/commands`, or `.grok/agents` already exist.

Do **not** key off a lone `AGENTS.md`. Many Grok projects have that file without Workforces.

Pass `--editor grok` explicitly on first install.

---

## Host mapping

Toolkit files are still written in Claude / Antigravity language. On a Grok host:

| Written as | Use instead |
|------------|-------------|
| `python3` | `python` on Windows if `python3` is missing |
| `.agents/skills/...` | `.grok/skills/...` |
| `.agents/workflows/...` | `.grok/commands/...` |
| `generate_image` | Grok `image_gen` |
| `invoke_subagent` / `Task` | `spawn_subagent` (`subagent_type` = agent name) |

`setup.sh` and `update.sh` already fall back from `python3` to `python` when resolving team manifests.

---

## Updates

```bash
bash .grok/skills/workforce-management/scripts/update.sh ./ --dry
bash .grok/skills/workforce-management/scripts/update.sh ./
```

Or run `/wf-update` after install.
