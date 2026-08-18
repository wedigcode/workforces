---
name: persona-management
description: Dynamic persona generation, storage, recommendation, and switching engine for Workforces. Manages case-by-case Author/Voice Personas and Target Audience Segment Personas stored in workforces/personas/ (or workforces/personas.json). Triggers on persona, voice, author persona, audience persona, tone of voice, perspective, voice switching.
---

# Skill: Persona Management & Dynamic Voice Switching

The `persona-management` skill manages project-specific, non-hardcoded personas. It enables agents (`@social`, `@marketer`, `@sales`, `@growth`, `@advisor`) to dynamically discover, create, recommend, and switch between **Author Voice Personas** (how the workforce speaks) and **Target Audience Personas** (who the workforce speaks to).

---

## 1. Core Philosophy: Zero Hardcoded Personas

- **No Static Hardcoding:** Agents (`@social`, `@marketer`, `@sales`, etc.) NEVER hardcode personas in their agent prompt files.
- **Dynamic Project Storage:** All personas are saved on a project-by-project basis in:
  - `workforces/personas/*.json` (individual persona cards)
  - `workforces/personas.json` (consolidated registry)
  - `docs/brand-context.md` (human-readable brand document)
- **Runtime Discovery:** When prompted to write, engage, or outreach, the agent inspects `workforces/personas/` (or executes `python3 skills/persona-management/scripts/manage_personas.py --export-context`) to discover what personas are available.

---

## 2. The Two Persona Types

### Type A: Author / Voice Personas (`type: author_voice`)
Defines the perspective, tone, and vocabulary of the person/brand writing the message.
- *Examples:*
  - **The CTO / Systems Thinker:** Architecture rigor, telemetry proof, scalability focus.
  - **The AI Enabler / Workflow Pragmatist:** Rapid prototyping, agentic workflows, automation playbooks.
  - **The Founder / Operator:** Unit economics, business leverage, vision.
  - **The Trusted Local Craftsman:** Reassuring, neighborly, transparent.

### Type B: Target Audience Personas (`type: target_audience`)
Defines the customer segment, their acute pain points, vocabulary, and decision triggers.
- *Examples:*
  - **Enterprise Engineering Leader:** Cares about security audits, SLAs, uptime guarantees.
  - **Growth Startup Founder:** Cares about time-to-market, cost efficiency, DIY velocity.
  - **Busy Homeowner:** Cares about same-day response, upfront pricing, 5-star reviews.

---

## 3. CLI & Script Commands

The helper script is located at `.agents/skills/persona-management/scripts/manage_personas.py`:

```bash
# 1. List active personas for the project
python3 .agents/skills/persona-management/scripts/manage_personas.py --list

# 2. Get AI recommendations based on project domain (SaaS, Local Service, Agency)
python3 .agents/skills/persona-management/scripts/manage_personas.py --recommend

# 3. Install a recommended persona template
python3 .agents/skills/persona-management/scripts/manage_personas.py --create-from-recommendation technical-architect

# 4. Export JSON context for agent prompt consumption
python3 .agents/skills/persona-management/scripts/manage_personas.py --export-context
```

---

## 4. Multi-Agent Persona Usage Matrix

| Agent | How They Use Personas | Example Prompt / Action |
| :--- | :--- | :--- |
| [`@social`](../agents/social.md) | Adopts active **Author Voice Persona** matching platform and thread context. | `@social reply to this architecture debate using the Technical Architect voice` |
| [`@marketer`](../agents/marketer.md) | Crafts copy tailored to a specific **Target Audience Persona** using the brand voice. | `@marketer write email nurture sequence for the Startup Founder segment` |
| [`@sales`](../agents/sales.md) | Maps outbound hooks and objections to the specific **Prospect Persona** being pitched. | `@sales draft cold LinkedIn sequence for Enterprise Decision Makers` |
| [`@growth`](../agents/growth.md) | Tailors keyword intent and content format to search intent persona cohorts. | `@growth map search queries for developer-focused personas` |
| [`@advisor`](../agents/advisor.md) | Calibrates coaching style (Strategic Challenger vs Empathetic Partner). | `@advisor audit our unit economics with the Pragmatic Operator perspective` |

---

## 5. Schema Specification (`workforces/personas/<id>.json`)

```json
{
  "id": "technical-architect",
  "name": "The Technical Architect / Systems Thinker",
  "type": "author_voice",
  "perspective": "Engineering rigor, scalability, reliability, telemetry metrics, and systems design.",
  "tone": "Authoritative, analytical, concise, data-backed",
  "platforms": ["x.com", "linkedin", "github", "hacker-news"],
  "keywords": ["architecture", "scale", "latency", "reliability", "infrastructure"],
  "rules": [
    "Lead with system trade-offs and latency considerations",
    "Avoid fluff or buzzwords; cite concrete benchmarks where possible",
    "End technical discussions with thoughtful architectural calibration questions"
  ]
}
```
