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

Grok discovers project slash commands as flat `*.md` files under `.grok/commands/`. The filename stem is the command name (`work.md` → `/work`).

---

## Command name collisions

Grok already owns some slash names. Workforces remaps those two on install and update:

| Workforces original | Installed as |
|---------------------|--------------|
| `/plan` | `/wf-plan` |
| `/context` | `/wf-context` |

Grok’s own `/plan` stays plan mode. Grok’s `/context` stays the token meter. Grok’s `/workflows` is Grok’s Rhai runner — that is a different system from Workforces markdown workflows.

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

Or run `/update-workforces` after install.
