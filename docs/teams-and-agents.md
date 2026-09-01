# Modular Workforces: Teams & Agent Roster

A modular architecture for AI agent workforces. Instead of dumping all agents, rules, skills, and workflows into a single bloated global prompt, capabilities are organized into **Core Leadership** and **Installable Domain Team Packs**.

---

## 🏛️ Architecture Overview

```
.
├── agents/                     # Standardized single-responsibility agents
│   ├── advisor.md              # @advisor (Strategy & Discovery)
│   ├── project-manager.md      # @project-manager (Backlog & Roadmap)
│   ├── programmer.md           # @programmer (Engineering & TDD)
│   ├── designer.md             # @designer (Visual Direction & UI/UX QA)
│   ├── marketer.md             # @marketer (Copywriting & Brand Strategy)
│   ├── sales.md                # @sales (Outbound & Deal Closing)
│   ├── social.md               # @social (Community & Content Triage)
│   ├── growth.md               # @growth (SEO & Generative Engine Optimization)
│   ├── operations.md           # @operations (Telemetry & Sprint Velocity)
│   ├── compliance.md           # @compliance (Integrity & Policy Auditing)
│   ├── researcher.md           # @researcher (Feature Scoping & PRDs)
│   └── scribe.md               # @scribe (Session Context Persistence)
│
├── teams/                      # Modular Domain Team Packs (Self-contained manifests)
│   ├── dev/                    # Engineering Pack (pack.json + pack.md)
│   ├── design/                 # Visual Design & UI/UX Pack
│   ├── marketing/              # Marketing & Copywriting Pack
│   ├── sales/                  # Sales & Outbound Pack
│   ├── operations/             # Operations & Metrics Pack
│   ├── social/                 # Social & Community Pack
│   ├── growth/                 # Growth & SEO/GEO Pack
│   └── compliance/             # Compliance & Reference Lineage Pack
│
├── rules/                      # Slim, non-duplicated domain & core rules
├── skills/                     # Centralized skill library
└── workflows/                  # Orchestrated team workflows
```

---

## 📋 Complete Agent Roster

| Agent Tag | Name | Team | Primary Mission & Capabilities | Trigger Keywords |
| :--- | :--- | :--- | :--- | :--- |
| [`@advisor`](../agents/advisor.md) | Strategic Advisor | Core | Consultative problem extraction, JTBD situational triggers, Value Stick audits, 5 Whys, value breakthrough coaching. | `advise`, `consultant`, `strategy`, `pain points`, `why` |
| [`@project-manager`](../agents/project-manager.md) | Project Manager | Core | Backlog prioritization, Value Stick scoring, SaaS unit economics, sprint syncs, and GitHub project sync. | `roadmap`, `backlog`, `planning`, `sprint`, `sync` |
| [`@scribe`](../agents/scribe.md) | Scribe | Core | Dense, zero-narrative session context recording and architectural decision persistence. | `context`, `session-context`, `save notes` |
| [`@programmer`](../agents/programmer.md) | Programmer | `dev` | Software development, TDD, symbol graph lookup, diff compression, and automated post-edit reviews. | `code`, `programmer`, `dev`, `developer`, `refactor`, `bug fix` |
| [`@designer`](../agents/designer.md) | Designer | `design` | Visual concept creation, design tokens, UI/UX architecture, layout specifications, and design QA reviews. | `designer`, `design`, `UI`, `UX`, `layout`, `visual`, `CSS` |
| [`@marketer`](../agents/marketer.md) | Marketer | `marketing` | JTBD positioning, Connected Strategy engagement, PAS copywriting, email cadences, and closed growth loops. | `marketing`, `marketer`, `copy`, `copywriting`, `campaign` |
| [`@sales`](../agents/sales.md) | Sales Specialist | `sales` | Prospect research, JTBD discovery, Customer Delight ROI framing, multi-touch outbound cadences, closing. | `sales`, `prospect`, `outreach`, `cold email`, `objection` |
| [`@social`](../agents/social.md) | Social Engager | `social` | Content discovery, cold-post triage, multi-tier conversation catalysts, and community cultivation. | `social`, `engage`, `x.com`, `skool`, `linkedin`, `community` |
| [`@growth`](../agents/growth.md) | Growth & SEO Lead | `growth` | Intent matching, programmatic SEO, self-reinforcing closed growth loops, GEO/AISO, platform network dynamics. | `growth`, `SEO`, `GEO`, `AISO`, `search volume`, `schema` |
| [`@operations`](../agents/operations.md) | Operations Lead | `operations` | Empirical metrics dashboards, telemetry tracking, sprint velocity, and workforce state. | `operations`, `ops`, `metrics`, `telemetry`, `velocity`, `KPIs` |
| [`@compliance`](../agents/compliance.md) | Compliance Auditor | `compliance` | Reference lineage enforcement, zero ghost references, data privacy governance, subtask tracking. | `compliance`, `integrity`, `broken links`, `audit` |
| [`@researcher`](../agents/researcher.md) | Feature Researcher | `growth` / `dev` | Research-first feature discovery, gap analysis, competitive teardowns, and structured PRD specs. | `researcher`, `feature`, `PRD`, `spec`, `requirement` |

---

## 📦 Modular Team Packs

Each domain team is configured via a structured `pack.json` and comprehensive `pack.md`:

### 1. Development (`teams/dev/`)
- **Agents:** `@programmer`
- **Rules:** `clean-coder.md` (TDD, symbol deduplication, diff compression, error handling)
- **Skills:** `clean-coder`, `code-graph`, `post-code-review`, `codebase-improvement`, `jules-integration`, `pr-review`, `doc-generator`
- **Workflows:** `/wf-clean`, `/wf-improve`, `/wf-investigate`

### 2. Design (`teams/design/`)
- **Agents:** `@designer`
- **Rules:** `design-standards.md` (0 emojis as UI icons, vector packs, Refero styles, DESIGN.md spec, progressive disclosure)
- **Skills:** `ui-ux-design`, `visual-design-fundamentals`, `design-anti-patterns`, `brand-guidelines`, `image-workflow`
- **Workflows:** `/wf-brand-context`, `/wf-site-setup` (Step 2), `/wf-image-duplicate`

### 3. Marketing (`teams/marketing/`)
- **Agents:** `@marketer`
- **Rules:** `design-standards.md`
- **Skills:** `persona-management`, `brand-guidelines`, `business-frameworks`, `image-workflow`, `ai-search-optimization`, `memory-management`
- **Workflows:** `/wf-brand-context`, `/wf-validate-idea`

### 4. Sales (`teams/sales/`)
- **Agents:** `@sales`
- **Skills:** `persona-management`, `brand-guidelines`, `business-frameworks`, `memory-management`
- **Workflows:** `/wf-advisor`

### 5. Social (`teams/social/`)
- **Agents:** `@social`
- **Rules:** `social-engagement.md` (Anti-bot safety, value-first comments, multi-tier threads, cold-post triage)
- **Skills:** `social-engagement`, `persona-management`, `brand-guidelines`, `memory-management`
- **Workflows:** `/wf-social`

### 6. Growth & SEO (`teams/growth/`)
- **Agents:** `@growth`, `@researcher`
- **Rules:** `design-standards.md`
- **Skills:** `persona-management`, `ai-search-optimization`, `business-frameworks`, `feature-research`, `doc-generator`, `memory-management`
- **Workflows:** `/wf-feature`, `/wf-validate-idea`

### 7. Operations (`teams/operations/`)
- **Agents:** `@operations`
- **Rules:** `base.md`, `session-context.md`
- **Skills:** `usage-tracker`, `session-context`, `memory-management`, `issue-tracker`
- **Workflows:** `/wf-sync`, `/wf-context`, `/wf-task`

### 8. Compliance (`teams/compliance/`)
- **Agents:** `@compliance`
- **Rules:** `file-integrity.md`, `mcp-protection.md`
- **Skills:** `integrity-validator`, `issue-tracker`, `session-context`, `usage-tracker`
- **Workflows:** `/wf-verify-integrity`, `/wf-task`

---

## 🎭 Dynamic Personas vs. Agents

- **Agents (`agents/*.md`)** are the **functional operators** (tools, workflows, rules, coding, auditing).
- **Personas (`workforces/personas/*.json`)** are the **case-by-case voices and customer segments** managed dynamically via the `persona-management` skill.
- **Zero Hard-Coding**: No personas are hard-coded in agent markdown files. They are created on a project-by-project basis in `workforces/personas/` with AI domain recommendations.
  - **Author Voice Personas**: e.g., *The Technical Architect* (deep tech, systems design), *The AI Enabler* (agentic workflows, builder energy), *The Trusted Local Craftsman* (approachable, reliable).
  - **Target Audience Personas**: e.g., *Enterprise Tech Decision-Maker*, *Growth Startup Founder*, *Busy Homeowner*.

---

## ⚡ Token Parsimony & Anti-Bloat Benefits

1. **Zero Duplicate Files:** Eliminated duplicate copies of skills and rules between root folders, `teams/skills/`, and `plugins/*/`.
2. **Context Efficiency:** Agents only load the rules, skills, and tools relevant to their specific domain.
3. **Selective Installation:** Projects only copy the files for their installed teams, eliminating prompt bloat.
4. **Transparent Role Discovery:** Users can inspect installed teams and instantly identify which agent handles their task.

