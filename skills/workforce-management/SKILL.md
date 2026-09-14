---
name: workforce-management
description: Manages the lifecycle, installation, updates, and configuration of the Workforces toolkit across multi-editor environments (.agents/, .github/copilot/, .claude/, .grok/). Reach for this skill when installing modular team packs (e.g., dev, marketing, sales), safely pruning unused team configurations with reference-counted dependency resolution, updating core toolkit files, or adjusting workspace settings.
---

# Workforce Management

Manages setup, updates, modular team pack installation, and reference-counted pruning across multi-editor environments (`.agents/`, `.github/copilot/`, `.claude/`, `.grok/`).

---

## 1. Architectural Layers

- **Zero External Dependencies**: Operates purely with standard shell (`bash`, `git`, `find`, `cp`) and standard Python 3.
- **Toolkit Layer (`.agents/`, etc.)**: "Read-only" engine layer containing agent personas, skills, and rules. Safe to update or prune.
- **Workspace Layer (`workforces/`)**: User-owned state and configuration:
  - `workrules.md` (preferences and active teams)
  - `workstate.md` (runtime status dashboard)
  - `tasks/` (authoritative task records)
  - `session-context/` (session memory notes)
  - `personas/` (custom project brand voices)
  - `.version` & `.manifest.json` (version hash and installed file tracking)

---

## 2. Core Operations & CLI Commands

All commands run via `.agents/skills/workforce-management/scripts/` (Fallback: `skills/...`):

| Operation | Command Pattern | Key Invariant |
| :--- | :--- | :--- |
| **Setup & Install** | `bash skills/workforce-management/scripts/setup.sh ./ --teams <team>` | Copies configured agents, rules, and skills from `teams/<team>/pack.json`. |
| **Toolkit Update** | `bash skills/workforce-management/scripts/update.sh ./ --non-interactive` | Prunes obsolete files via `.manifest.json` while protecting user files. |
| **Prune Team** | `python3 skills/workforce-management/scripts/prune-team.py <team>` | **Reference-Counted**: Shared dependencies used by active teams are preserved. |
| **Validate Refs** | `python3 skills/workforce-management/scripts/validate-references.py ./ --fix` | Verifies zero ghost references or broken paths across markdown and JSON files. |
