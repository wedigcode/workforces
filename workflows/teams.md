---
description: Dynamic Team Architect — lists, installs, and manages modular Team Packs (dev, design, marketing, sales, operations, social, growth, compliance) for your workspace.
---

# /teams — Modular Team Architect & Pack Manager

Lists installed teams, installs additional domain team packs on-demand from upstream `workforces`, or generates custom project-specific teams.

---

## Commands & Usage

```
/teams                                       → List installed teams, active agents, and available upstream packs
/teams add <domain-name>                     → Install an upstream team pack (e.g. marketing, sales, social, dev, growth, compliance)
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

## Listing Installed Teams (`/teams`)

When invoked without arguments, `/teams` reads `workforces/workrules.md` and displays:
1. **Active Installed Teams & Agents:**
   - `dev` → `@programmer` (TDD, clean code, code graph)
   - `design` → `@designer` (UI/UX, visual mockups, tokens)
2. **Available Upstream Packs:**
   - `marketing` (`@marketer`)
   - `sales` (`@sales`)
   - `social` (`@social`)
   - `growth` (`@growth`, `@researcher`)
   - `operations` (`@operations`)
   - `compliance` (`@compliance`)
3. **Action:** Prompts user: *"Run `/teams add <team>` to install an additional domain pack."*
