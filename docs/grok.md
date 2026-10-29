# Grok Build

Workforces compiles natively into [Grok Build](https://x.ai/cli) alongside Antigravity, Claude Code, GitHub Copilot, and Cursor via `compile_assets.py` and `config/hosts/grok.json`.

```bash
git clone https://github.com/wedigcode/workforces.git /tmp/workforces
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts grok --type project --non-interactive
rm -rf /tmp/workforces
```
*(Note: `--editor grok` / `--editor grok-build` is also supported, and you can combine Grok with other AI hosts via `--hosts grok,claude,cursor`.)*

Then start a new Grok session in the target project so it picks up `.grok/` and `AGENTS.md`.

---

## Layout

| Path | Role |
|------|------|
| `.grok/agents/*.md` | Specialist personas compiled with Grok `allowed-tools`, `model`, and `user-invocable` frontmatter |
| `.grok/skills/*/SKILL.md` | Modular agent skills (`SKILL.md` + scripts; `wf-management/hosts/` bundled for offline updates) |
| `.grok/rules/*.md` | Always-on and path-scoped (`paths`) behavioral rules |
| `.grok/commands/*.md` | Compiled workflow commands |
| `.grok/plugins/*/` | Domain plugin manifests and hook bundles |
| `.grok/hooks.json` | Aggregated native lifecycle hooks (`PreToolUse` / `PostToolUse`) compiled with Grok tool matchers |
| `AGENTS.md` | Root project context pointing to `.grok/` (created if missing) |
| `workforces/` | Workspace layer including `workforces/config.json` and `workforces/.manifest.json` |

---

## Command Namespace & Collision Avoidance

All Workforces modular skills and commands use the standard `wf-` prefix natively across all platforms to prevent collisions with host-reserved keywords (such as Grok's built-in `/plan`, `/context`, and `/workflows`):

| Workforces Command / Skill | Role |
|---|---|
| `/wf-plan` | Phased Project Planner & Estimates |
| `/wf-sync` | Multi-Mode Meeting & Standup Sync |
| `/wf-advisor` | Strategic Advisory & Problem Discovery |
| `/wf-ideate` | Rapid Ideation & Micro-SaaS Unbundling |
| `/wf-investigate` | Incident Triage & Log Investigation |
| `/wf-question-formulation` | Decision Formulation & Trade-Off Escalation |

Grok’s own `/plan` stays plan mode. Grok’s `/context` stays the token meter. Grok’s `/workflows` remains Grok’s native Rhai runner.

---

## Auto-Detection & `workforces/config.json`

- `setup.sh` / `update.sh` auto-detect Grok only when `.grok/agents`, `.grok/skills`, `.grok/rules`, or `.grok/commands` already exist, or when `"grok"` is recorded in `workforces/config.json`.
- Workforces does **not** key off a lone `AGENTS.md` (which Cursor and standalone projects also use).
- Pass `--hosts grok` (or `--editor grok`) explicitly on first install; `workforces/config.json` persists `"hosts": ["grok"]` automatically for all subsequent updates and team pruning.

---

## Native Frontmatter & Hook Compilation (`config/hosts/grok.json`)

During `setup.sh` and `update.sh`, `compile_assets.py` translates universal sidecar JSON capabilities (`agents/*.json`, `rules/*.json`, `skills/*/skill.json`, `plugins/*/plugin.json`) into native Grok schemas:

| Capability / Asset | Compiled Grok Output |
|--------------------|----------------------|
| `read`, `search`, `edit`, `multi_edit`, `execute` | `allowed-tools: [Read, Grep, Glob, Write, Edit, Bash]` |
| `web`, `image`, `delegate` | `web_search`, `image_gen`, `spawn_subagent` |
| `background_only: true` (e.g. `wf-scribe`) | `user-invocable: false` |
| Lifecycle hooks (`plugins/*/plugin.json`) | `.grok/hooks.json` + `.grok/plugins/<name>/hooks.json` matching `Write\|Edit\|write_file\|edit_file\|MultiEdit` |
| CLI script execution | `setup.sh`, `update.sh`, and hook commands automatically fall back from `python3` to `python` on Windows; invoke installed scripts via `.grok/skills/...` |

---

## Updates & Team Pruning

```bash
bash .grok/skills/wf-management/scripts/update.sh ./ --dry
bash .grok/skills/wf-management/scripts/update.sh ./
python3 .grok/skills/wf-management/scripts/prune-team.py <team-name>
```

Or ask your AI assistant *"Update workforces"* (or run `/wf-update`) after install.

