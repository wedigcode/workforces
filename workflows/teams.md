---
description: Dynamic Team Architect — lists, installs, prunes, and manages modular Team Packs (dev, design, marketing, sales, operations, social, growth, compliance) for your workspace.
---

# /teams — Modular Team Architect & Pack Manager

Lists installed teams, installs additional domain team packs on-demand from upstream `workforces`, prunes unneeded teams to eliminate prompt bloat while preserving shared dependencies, or generates custom project-specific teams.

---

## Commands & Usage

```
/teams                                       → List installed teams, active agents, and available upstream packs
/teams add <domain-name>                     → Install an upstream team pack (e.g. marketing, sales, social, dev, growth, compliance)
/teams remove <domain-name>                  → Safely prune a team pack, eliminating runtime bloat while keeping shared dependencies
/teams "I need a custom team for..."          → Dynamically synthesize a custom project team in workforces/teams/<team-name>/
```

---

## Installing an Upstream Team Pack (`/teams add <team>`)

When you need capabilities for a new domain (for example, adding `@marketer` and copywriting skills via `marketing`, or `@social` via `social`):

### Step 1 — Register in Configuration
Add the team name to `installed_teams` in `workforces/workrules.md`:
```yaml
## Installed Teams
- installed_teams:
  - dev
  - design
  - marketing
```

### Step 2 — Sync Team Assets
Run the workforce installer to sync only that team's specific agents, rules, skills, and workflows from upstream:
```bash
bash .agents/skills/workforce-management/scripts/setup.sh ./ --teams <team-name>
```
*(Or run `bash .agents/skills/workforce-management/scripts/update.sh ./` to re-sync all configured teams).*

The installer reads `teams/<team>/pack.json` and copies:
- **Agents:** (e.g. `agents/marketer.md`)
- **Rules:** Associated domain rules
- **Skills:** Associated domain skills
- **Workflows:** Associated domain workflows
- **Manifest:** `teams/<team>/pack.json` & `pack.md`

### Step 3 — Update Work State
Append the newly installed team under `## Active Teams` in `workforces/workstate.md` so `@project-manager` and orchestrators immediately recognize its agents and workflows.

---

## Uninstalling & Pruning a Team (`/teams remove <team>`)

When a domain team is no longer needed, uninstall it to eliminate runtime prompt bloat (unused skills and eager rules) from `.agents/`:

### Step 1 — Run the Pruner
Execute the reference-counting pruner:
```bash
python3 .agents/skills/workforce-management/scripts/prune-team.py <team-name>
```
*(Alternative: `python3 .agents/skills/workforce-management/scripts/prune-team.py <team-name> --dry` to preview changes without deleting files).*

### Step 2 — Programmatic Dependency Protection
The uninstaller dynamically scans all remaining installed teams and ensures:
1. **Shared Skills & Rules Preserved:** Any skill, rule, workflow, or plugin required by another active team (e.g. `brand-guidelines`, `image-workflow`, `doc-generator`) is automatically kept.
2. **Runtime Bloat Pruned:** Only unshared, orphaned skills, eager rules, workflows, and toolkit agents are deleted from `.agents/`.
3. **Workspace Personas & Data Retained:** All user business personas (`workforces/personas/`), voice profiles, and workspace configs (`workforces/teams/<team>/`) are **preserved by default**. Re-adding the team later restores your customized tone and history immediately.
4. **Hard Wipe (`--purge-data`):** Only if `--purge-data` is explicitly passed will workspace folders in `workforces/teams/<team>/` be deleted.
5. **Registry Synchronized:** Automatically unregisters the team from `workforces/workrules.md` and `workforces/workstate.md`.

---

## Listing Installed Teams (`/teams`)

When invoked without arguments, `/teams` reads `workforces/workrules.md` and displays:
1. **Active Installed Teams & Agents:**
   - `dev` → `@programmer` (TDD, clean code, code graph)
   - `design` → `@designer` (UI/UX, visual design, tokens)
2. **Available Upstream Packs:**
   - `marketing` (`@marketer`)
   - `sales` (`@sales`)
   - `social` (`@social`)
   - `growth` (`@growth`, `@researcher`)
   - `operations` (`@operations`)
   - `compliance` (`@compliance`)
3. **Action:** Prompts user: *"Run `/teams add <team>` to install an additional domain pack, or `/teams remove <team>` to prune an unneeded team."*
