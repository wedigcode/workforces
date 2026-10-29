---
name: wf-management
description: Manages the lifecycle, installation, multi-AI frontmatter compilation, updates, and configuration of the Workforces toolkit across multi-editor environments (.agents/, .claude/, .grok/, .github/, .cursor/). Reach for this skill when installing modular team packs (e.g., dev, marketing, sales), safely pruning unused team configurations with reference-counted dependency resolution, updating core toolkit scripts and files, or adjusting workspace settings in workforces/config.json.
---

# Workforce Management

Manages setup, multi-AI frontmatter & hook compilation, updates, modular team pack installation, and reference-counted pruning across multi-editor environments (`.agents/`, `.claude/`, `.grok/`, `.github/`, `.cursor/`).

---

## 1. Architectural Layers

- **Zero External Dependencies**: Operates purely with standard shell (`bash`, `git`, `find`, `cp`) and Python 3 stdlib.
- **Two-Layer Multi-AI Compiler (`compile_assets.py`)**:
  - **Canonical Sidecar JSON** (`agents/*.json`, `rules/*.json`, `skills/*/skill.json`, `plugins/*/plugin.json`): Stores universal, AI-agnostic metadata (`name`, `description`, semantic `capabilities`: `read`, `search`, `edit`, `multi_edit`, `execute`, `web`, `image`, `delegate`, `skills`, `background_only`, `always_on`, `globs`) plus an optional `"hosts"` object for per-AI overrides.
  - **Host Adapter Profiles** (`config/hosts/{antigravity,claude,grok,copilot,cursor}.json`, bundled into `skills/wf-management/hosts/` for offline updates and pruning): Maps capabilities to native AI tool names, synthesizes host-native YAML frontmatter, maps target folders & extensions (`.md`, `.agent.md`, `.instructions.md`, `.prompt.md`, `.mdc`), rewrites intra-toolkit relative Markdown links, and compiles native lifecycle hooks per host.
- **Toolkit Layer (`.agents/`, `.claude/`, `.grok/`, `.github/`, `.cursor/`)**: Read-only compiled engine layer containing host-native personas, rules, skills, commands/prompts, and hooks. Safe to recompile, update, or prune across single or multiple hosts simultaneously.
- **Workspace Layer (`workforces/`)**: User-owned state and persistent configuration:
  - `config.json` (persistent install settings: `hosts`, `auto_detect_hosts`, `repo_type`, `installed_teams`, `host_dirs`)
  - `workrules.md` (preferences and active teams)
  - `workstate.md` (runtime status dashboard)
  - `tasks/` (authoritative task records)
  - `session-context/` (session memory notes)
  - `personas/` (custom project brand voices)
  - `.version` & `.manifest.json` (version hash, active `hosts`, and compiled `installed_files` tracking)

---

## 2. Multi-AI Host Matrix & Hook Compilation

| AI Host (`--hosts` / `--editor`) | Base & Auto-Detect Signals | Compiled Layout & Extensions | Root Context Doc | Native Plugin / Hook Compilation |
| :--- | :--- | :--- | :--- | :--- |
| **`antigravity`** (`gemini`) | `.agents/`<br>Detect: `.agents`, `.gemini`, `GEMINI.md` | `agents/*.md`, `rules/*.md`, `skills/*/SKILL.md`, `workflows/*.md`, `plugins/*/`, `teams/*/` | `GEMINI.md` | `.agents/plugins/<name>/{plugin.json,hooks.json}` (`PreToolUse` / `PostToolUse`) |
| **`claude`** (`claude-code`) | `.claude/`<br>Detect: `.claude`, `CLAUDE.md` | `agents/*.md`, `rules/*.md`, `skills/*/SKILL.md`, `commands/*.md`, `teams/*/` | `CLAUDE.md` | Non-destructively merges/prunes `wf-*` hooks in `.claude/settings.json` |
| **`grok`** (`grok-build`) | `.grok/`<br>Detect: `.grok/{agents,skills,rules,commands}` | `agents/*.md` (`allowed-tools`), `rules/*.md`, `skills/*/SKILL.md`, `commands/*.md`, `plugins/*/`, `teams/*/` | `AGENTS.md` | Compiles `.grok/hooks.json` + `.grok/plugins/<name>/` |
| **`copilot`** (`vscode`, `github`) | `.github/`<br>Detect: `.github/{agents,instructions,skills,copilot}`, `.vscode` | `agents/*.agent.md`, `instructions/*.instructions.md`, `skills/*/SKILL.md`, `prompts/*.prompt.md`, `copilot/teams/*/` | `.github/copilot-instructions.md` | Skipped cleanly; migrates & prunes legacy `.github/copilot/` on update |
| **`cursor`** | `.cursor/`<br>Detect: `.cursor`, `.cursorrules` | `agents/*.md` (`readonly` / `is_background`), `rules/*.mdc` (`alwaysApply`), `skills/*/SKILL.md`, `commands/*.md`, `teams/*/` | `AGENTS.md` | Skipped cleanly; rules compile natively to `.mdc` |

---

## 3. Core Operations & CLI Commands

All commands run via `.agents/skills/wf-management/scripts/` (or `.claude/skills/...`, `.grok/skills/...`, `.github/skills/...`, `.cursor/skills/...`; source fallback: `skills/wf-management/scripts/`):

| Operation | Command Pattern | Key Invariant |
| :--- | :--- | :--- |
| **Setup & Install** | `bash .agents/skills/wf-management/scripts/setup.sh ./ --hosts <auto\|all\|csv> --teams <team>` | Auto-detects or compiles across specified hosts (`--editor` alias; `--no-auto-detect` pins hosts) and writes `workforces/config.json`. |
| **Toolkit Update** | `bash .agents/skills/wf-management/scripts/update.sh ./ --non-interactive` | Recompiles all active + newly detected hosts, prunes obsolete files/hooks via `.manifest.json`, and protects user files. |
| **Compile / Sync Source** | `python3 skills/wf-management/scripts/compile_assets.py --toolkit-root ./ --sync-source` | Syncs canonical Antigravity frontmatter & plugin `hooks.json` in source `.md` files from sidecar JSON. |
| **Prune Team** | `python3 .agents/skills/wf-management/scripts/prune-team.py <team>` | **Reference-Counted**: Preserves shared dependencies used by remaining teams and prunes across all active hosts & hooks. |
| **Validate Schema & Refs** | `python3 .agents/skills/wf-management/scripts/validate.py ./ && python3 .agents/skills/wf-management/scripts/validate-references.py ./ --fix` | Validates sidecar JSON, host schemas/extensions, and zero ghost references across all installed host directories. |

