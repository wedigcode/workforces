# Setup Guide

This guide describes how to install, configure, and update the Workforces AI toolkit across single or multiple AI coding environments in any target repository.

---

## Quick Install (For Humans)

Clone the Workforces repository to a temporary folder and run `setup.sh` pointing to your target project root. By default, `setup.sh` auto-detects present AI host folders (or prompts interactively on a brand-new repo):

```bash
git clone https://github.com/wedigcode/workforces.git /tmp/workforces
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./
rm -rf /tmp/workforces
```

---

## Quick Install (For AI Agents)

If you are an AI assistant (Antigravity/Gemini, Claude Code, GitHub Copilot, Cursor, or Grok Build) tasked with installing this toolkit:

1. **Clone the Repo:** Clone `https://github.com/wedigcode/workforces.git` to a temporary path (`/tmp/workforces`).
2. **Detect Target AI Host(s):**
   - `setup.sh` automatically detects all workspace markers when `--hosts auto` (default) is used:
     - **Antigravity / Gemini** (`antigravity` / `gemini`): `.agents/`, `.gemini/`, or `GEMINI.md` → compiles into `.agents/` + `GEMINI.md`.
     - **Claude Code** (`claude` / `claude-code`): `.claude/` or `CLAUDE.md` → compiles into `.claude/` + `CLAUDE.md` and merges hooks into `.claude/settings.json`.
     - **GitHub Copilot / VS Code** (`copilot` / `vscode` / `github`): `.github/{agents,instructions,skills,copilot}`, `.github/copilot-instructions.md`, or `.vscode/` → compiles native `.github/{agents,instructions,skills,prompts}` + `.github/copilot-instructions.md`.
     - **Cursor** (`cursor`): `.cursor/` or `.cursorrules` → compiles native `.cursor/rules/*.mdc`, `.cursor/agents/*.md`, `.cursor/skills/*/SKILL.md`, `.cursor/commands/*.md`, and `AGENTS.md`.
     - **Grok Build** (`grok` / `grok-build`): `.grok/{agents,skills,rules,commands}` → compiles into `.grok/` + `AGENTS.md`. Do **not** treat a lone `AGENTS.md` as a Grok signal; pass `--hosts grok` explicitly on first Grok install. See [Grok Build](grok.md).
3. **Execute Non-Interactively:** Run `setup.sh` with `--non-interactive` (pass a single host, a comma-separated list for multi-AI repos, `all`, or `auto`):
   ```bash
   bash /tmp/workforces/skills/wf-management/scripts/setup.sh <target-path> --hosts <auto|all|csv> --type project --non-interactive
   ```
4. **Configure Rules & Preferences:** Edit `workforces/workrules.md` inside the target project to configure `github_usernames` and set formatting rules under `## AI Preferences`.

---

## Setup Options

```bash
# Auto-detect all present AI hosts (default) or install for specific / multiple hosts
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts auto                    # Auto-detect workspace AI folders
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts antigravity             # Antigravity / Gemini (.agents/)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts claude                  # Claude Code (.claude/ + settings.json hooks)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts copilot                 # GitHub Copilot (.github/*.agent.md & *.instructions.md)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts cursor                  # Cursor (.cursor/rules/*.mdc & agents/)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts grok                    # Grok Build (.grok/ + hooks.json)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts claude,copilot,cursor   # Multi-AI simultaneous compilation
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts all                     # All 5 supported AI hosts
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --hosts claude --no-auto-detect # Pin strictly to specified host(s)
# Note: --editor <list> is supported as a full alias for --hosts (including vscode, gemini, claude-code, grok-build)

# Select modular Team Packs (default: dev,design; or 'all' / 'none' / CSV)
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --teams dev,design,marketing

# Specify repository role
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --type project                  # Standard project codebase
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --type workforce                # Central coordinator tracking multiple projects

# Greenfield Site Setup & Dry Run
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --site-setup                    # Initializes docs/product-brief.md & workforces/images.json
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --skip-site-setup               # Skips site setup initialization
bash /tmp/workforces/skills/wf-management/scripts/setup.sh ./ --dry                           # Preview compilation without writing files
```

---

## Multi-AI Frontmatter Compiler & Sidecar Architecture

Instead of copying static single-editor files verbatim, `compile_assets.py` (pure Python 3 stdlib) compiles toolkit assets from a **two-layer metadata architecture**:

1. **Canonical Sidecar JSON (`agents/*.json`, `rules/*.json`, `skills/*/skill.json`, `plugins/*/plugin.json`):**
   Defines universal, platform-neutral metadata (`name`, `description`, semantic `capabilities`: `read`, `search`, `edit`, `multi_edit`, `execute`, `web`, `image`, `delegate`, `skills`, `background_only`, `always_on`, `globs`) plus an optional `"hosts": { "<ai>": { ... } }` override block.
2. **Host Adapter Profiles (`config/hosts/{antigravity,claude,grok,copilot,cursor}.json`):**
   Bundled into `<host>/skills/wf-management/hosts/` for offline updates and team pruning. Each profile maps semantic capabilities into native tool names, synthesizes host-valid YAML frontmatter, maps target directories and file extensions, rewrites intra-toolkit relative Markdown links (e.g., `wf-git-workflow.md` → `wf-git-workflow.instructions.md` on Copilot or `wf-git-workflow.mdc` on Cursor), and compiles lifecycle hooks natively.

### Per-Host Compilation & Hook Matrix

| AI Host (`id` / aliases) | Target Base & Root Doc | Compiled Directories & Extensions | Frontmatter & Tool Mapping | Native Plugin / Hook Installation |
| :--- | :--- | :--- | :--- | :--- |
| **`antigravity`** (`gemini`) | `.agents/`<br>`GEMINI.md` | `agents/*.md`, `rules/*.md`, `skills/*/SKILL.md`, `workflows/*.md`, `plugins/*/`, `teams/*/` | `tools` (`view_file`, `write_to_file`, `run_command`, `send_message`, etc.), `mainAgent`, `subagent`, `commandExecutionPolicy`, `trigger: always_on` | Emits `.agents/plugins/<name>/{plugin.json,hooks.json}` (`PreToolUse` / `PostToolUse`) |
| **`claude`** (`claude-code`) | `.claude/`<br>`CLAUDE.md` | `agents/*.md`, `rules/*.md`, `skills/*/SKILL.md`, `commands/*.md`, `teams/*/` | `tools` (`Read`, `Write`, `Edit`, `MultiEdit`, `Bash`, `Grep`, `Glob`, `Task`), `model`, `skills`, scoped `paths` | Idempotently merges/prunes `wf-*` hook commands in `.claude/settings.json` without touching user keys |
| **`grok`** (`grok-build`) | `.grok/`<br>`AGENTS.md` | `agents/*.md`, `rules/*.md`, `skills/*/SKILL.md`, `commands/*.md`, `plugins/*/`, `teams/*/` | `allowed-tools` (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `web_search`, `image_gen`, `spawn_subagent`), `model`, `user-invocable` | Compiles `.grok/hooks.json` + `.grok/plugins/<name>/` with Grok tool matchers |
| **`copilot`** (`vscode`, `github`) | `.github/`<br>`.github/copilot-instructions.md` | `agents/*.agent.md`, `instructions/*.instructions.md`, `skills/*/SKILL.md`, `prompts/*.prompt.md`, `copilot/teams/*/` | Agent `tools` (`read`, `search`, `edit`, `execute`, `web`, `agent`), `user-invocable`; Rule `description`, `applyTo` | Skips unsupported JSON PreToolUse hooks cleanly; migrates & prunes legacy `.github/copilot/` on update |
| **`cursor`** | `.cursor/`<br>`AGENTS.md` | `agents/*.md`, `rules/*.mdc`, `skills/*/SKILL.md`, `commands/*.md`, `teams/*/` | Agent `model`, `readonly` (derived from capabilities), `is_background`; Rule `description`, `globs`, `alwaysApply` | Skips unsupported JSON PreToolUse hooks cleanly; compiles rules natively to `.mdc` |

---

## Persistent Install Configuration (`workforces/config.json`)

Both `setup.sh` and `update.sh` persist active multi-host settings to `workforces/config.json` alongside `workforces/.manifest.json` and `workforces/.version`:

```json
{
  "schema_version": 1,
  "repo_type": "project",
  "hosts": ["antigravity", "claude"],
  "auto_detect_hosts": true,
  "installed_teams": ["design", "dev"],
  "host_dirs": {
    "antigravity": ".agents",
    "claude": ".claude"
  },
  "updated_at": "2026-10-28T14:45:00Z"
}
```

- **Auto-Detection Priority:** On subsequent `update.sh` or `prune-team.py` runs, Workforces reads `hosts` from `workforces/config.json` and—when `auto_detect_hosts` is `true`—unions them with any newly added AI host directories in the workspace. Pass `--no-auto-detect` to lock strictly to the saved/specified hosts.
- **`.gitignore` Safeguards:** Setup automatically ensures `workforces/tmp`, `workforces/session-context/*`, `workforces/memory`, and `.worktrees` are ignored so scratch artifacts are never committed.

---

## Updating & Pruning Teams

Update all active AI hosts simultaneously or prune unused Team Packs with reference-counted dependency resolution:

```bash
# Preview multi-host updates without modifying files
bash .agents/skills/wf-management/scripts/update.sh ./ --dry

# Apply updates across all active/detected AI hosts (or run from .claude/, .grok/, .github/, .cursor/)
bash .agents/skills/wf-management/scripts/update.sh ./

# Reference-counted team pruning across all active hosts & hooks
python3 .agents/skills/wf-management/scripts/prune-team.py marketing
```

> **Upgrading from a pre-`wf-` install (`workforce-management`) or legacy `.github/copilot/`:** Run `/wf-update` (which automatically bootstraps from upstream if `wf-management` is missing and migrates legacy paths) or run once from a temporary clone (`tmp_wf="$(mktemp -d)" && git clone --depth=1 https://github.com/wedigcode/workforces.git "$tmp_wf" && bash "$tmp_wf/skills/wf-management/scripts/update.sh" ./ --force && rm -rf "$tmp_wf"`).

Or ask your AI assistant *"Update the workforces toolkit"* (or run `/wf-update`).

