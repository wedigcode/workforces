---
description: Dynamic Team Architect — generates customized, minimalist teams in workforces/teams/<team-name>/ based on user prompt and project needs.
---

# /teams — Dynamic Team Architect

Constructs, lists, or updates customized Team Packs for your active project workforce.

---

## Commands & Usage

```
/teams                                       → List installed teams and available upstream building blocks
/teams "I need a team for marketing..."       → Dynamically build a custom team in workforces/teams/<team-name>/
/teams add <domain-name>                     → Bootstrap a team based on an upstream building block (e.g., sales, marketing, dev, growth)
```

---

## Step 1 — Parse Project Context & Request

1. Read `workforces/workrules.md` to identify the project type (e.g., SaaS, Local Service, Enterprise) and active settings.
2. Read `workforces/workstate.md` to check currently registered teams.
3. Parse the user's request prompt (e.g., *"I need a team that will help with marketing for a local service business"*).

## Step 2 — Query Building Blocks & Principles

1. Inspect available building blocks in upstream `workforces` repository under `teams/*/pack.md` (e.g., `teams/marketing/pack.md`, `teams/sales/pack.md`, `teams/dev/pack.md`, `teams/growth/pack.md`).
2. Extract the relevant **Principles of Domain Excellence** (e.g. for marketing: customer-centric positioning, visual & copy consistency; for sales: active listening, objection handling).

## Step 3 — Synthesize Minimalist Team Pack

Generate a **custom, minimalist team pack** inside `workforces/teams/<team-name>/` in the active workspace:

1. **Manifest (`workforces/teams/<team-name>/team.json`):**
   ```json
   {
     "id": "<team-name>",
     "name": "<Human Readable Team Name>",
     "version": "1.0.0",
     "description": "<Brief purpose statement>",
     "personas": ["personas/<role-1>.md"],
     "rules": ["rules/<domain-rule>.md"],
     "workflows": ["workflows/<sop-name>.md"]
   }
   ```

2. **Personas (`workforces/teams/<team-name>/personas/`):**
   Generate minimal persona files incorporating the domain principles of excellence.

3. **Rules & SOPs (`workforces/teams/<team-name>/rules/` & `workflows/`):**
   Generate targeted SOP workflows specifically required for the project (e.g. `launch-campaign.md`, `outreach-sequence.md`).

## Step 4 — Register Active Team

1. **Register in `workforces/workstate.md`:**
   Append the new team under `## Active Teams` (ID, name, and folder path `workforces/teams/<team-name>/`) so the AI Project Manager (`project-manager.md`) and orchestrators immediately recognize its capabilities.
