---
name: persona-management
description: Generates, catalogs, and dynamically switches between Author Voice Personas (brand tone and perspective) and Target Audience Personas (customer segment profiles) without hardcoding voices in prompts. Reach for this skill when tailoring copy, marketing assets, sales outreach, or social replies to specific personas, resolving audience segments from `workforces/personas/`, or adapting tone of voice across channels.
---

# Persona Management & Dynamic Voice Switching

Manages project-specific personas dynamically without hardcoded voices in agent prompts.

---

## 1. Zero-Hardcoding Persona Model

- **No Static Hardcoding**: Subagents (`@social`, `@marketer`, `@sales`, `@growth`) never embed static voices in system instructions.
- **Storage Locations**:
  - `workforces/personas/*.json` (individual persona profiles)
  - `workforces/personas.json` (consolidated registry)
  - `docs/brand-context.md` (human-readable guidelines)
- **Runtime Discovery**: Run `.agents/skills/persona-management/scripts/manage_personas.py --export-context` (fallback: `skills/...`) to dynamically hydrate personas into agent context.

---

## 2. Persona Archetypes & Schema

```json
{
  "id": "technical-architect",
  "name": "The Technical Architect / Systems Thinker",
  "type": "author_voice",
  "perspective": "Engineering rigor, scalability, reliability, telemetry metrics, and systems design.",
  "tone": "Authoritative, analytical, concise, data-backed",
  "platforms": ["x.com", "linkedin", "github"],
  "keywords": ["architecture", "scale", "latency", "reliability", "infrastructure"],
  "rules": [
    "Lead with system trade-offs and latency considerations",
    "Avoid fluff or buzzwords; cite concrete benchmarks where possible"
  ]
}
```

| Type | Purpose | Consumers |
| :--- | :--- | :--- |
| `author_voice` | Defines WHO is speaking (perspective, tone, phrasing rules). | `@social` (replies), `@marketer` (blogs/newsletters), `@sales` (emails). |
| `target_audience` | Defines WHO is being addressed (pains, triggers, objections). | `@sales` (prospecting), `@growth` (SEO intent), `@marketer` (landing pages). |

---

## 3. CLI Helper Commands

```bash
# List all active project personas
python3 .agents/skills/persona-management/scripts/manage_personas.py --list

# Get domain recommendations (SaaS, Agency, Local)
python3 .agents/skills/persona-management/scripts/manage_personas.py --recommend

# Create a persona from recommendation template
python3 .agents/skills/persona-management/scripts/manage_personas.py --create-from-recommendation technical-architect

# Export JSON context for LLM prompt injection
python3 .agents/skills/persona-management/scripts/manage_personas.py --export-context
```
*(Fallback: `python3 skills/persona-management/scripts/manage_personas.py ...`)*
