# Modular Workforces: Teams & Agent Roster

A modular architecture for AI agent workforces. Instead of dumping all agents, rules, skills, and workflows into a single bloated global prompt, capabilities are organized into **Core Leadership** and **Installable Domain Team Packs**.

---

## 🏛️ Architecture Overview

```
.
├── agents/                     # Standardized single-responsibility agents
│   ├── project-manager.md      # @project-manager (Backlog & Roadmap)
│   ├── programmer.md           # @programmer (Engineering & TDD)
│   ├── designer.md             # @designer (Visual Direction & UI/UX QA)
│   ├── marketer.md             # @marketer (Copywriting & Brand Strategy)
│   ├── sales.md                # @sales (Outbound & Deal Closing)
│   ├── social.md               # @social (Community & Content Triage)
│   ├── growth.md               # @growth (SEO & Generative Engine Optimization)
│   ├── operations.md           # @operations (Telemetry & Sprint Velocity)
│   ├── researcher.md           # @researcher (Feature Scoping & PRDs)
│   ├── scribe.md               # @scribe (Session Context Persistence)
│   ├── launcher.md             # @launcher (Fast Validation & Monetization)
│   ├── unbundler.md            # @unbundler (Atomic Micro-SaaS Deconstruction)
│   └── disruptor.md            # @disruptor (Macro Trend & Disruption Scouting)
│
├── teams/                      # Modular Domain Team Packs (Self-contained manifests)
│   ├── dev/                    # Engineering Pack (pack.json + pack.md)
│   ├── design/                 # Visual Design & UI/UX Pack
│   ├── marketing/              # Marketing & Copywriting Pack
│   ├── sales/                  # Sales & Outbound Pack
│   ├── operations/             # Operations & Metrics Pack
│   ├── social/                 # Social & Community Pack
│   ├── growth/                 # Growth & SEO/GEO Pack
│   ├── compliance/             # Compliance & Reference Lineage Pack
│   ├── launch/                 # Launch & Fast Validation Pack
│   └── advisor/                # Strategy, Advisory & Ideation Pack
│
├── rules/                      # Slim, non-duplicated domain & core rules
├── skills/                     # Centralized modular agent skill library
├── plugins/                    # Domain plugin bundles
└── hooks.json                  # Native lifecycle hooks
```

---

## 📋 Complete Agent Roster

| Agent Tag | Name | Team | Primary Mission & Capabilities | Trigger Keywords |
| :--- | :--- | :--- | :--- | :--- |
| [`@project-manager`](../agents/project-manager.md) | Project Manager | Core | Backlog prioritization, Value Stick scoring, SaaS unit economics, sprint syncs, and GitHub project sync. | `roadmap`, `backlog`, `planning`, `sprint`, `sync` |
| [`@scribe`](../agents/scribe.md) | Scribe | Core | Dense, zero-narrative session context recording and architectural decision persistence. | `context`, `session-context`, `save notes` |
| [`@programmer`](../agents/programmer.md) | Programmer | `dev` | Software development, TDD, symbol graph lookup, diff compression, and automated post-edit reviews. | `code`, `programmer`, `dev`, `developer`, `refactor`, `bug fix` |
| [`@designer`](../agents/designer.md) | Designer | `design` | Visual concept creation, design tokens, UI/UX architecture, layout specifications, and design QA reviews. | `designer`, `design`, `UI`, `UX`, `layout`, `visual`, `CSS` |
| [`@marketer`](../agents/marketer.md) | Marketer | `marketing` | JTBD positioning, Connected Strategy engagement, PAS copywriting, email cadences, and closed growth loops. | `marketing`, `marketer`, `copy`, `copywriting`, `campaign` |
| [`@sales`](../agents/sales.md) | Sales Specialist | `sales` | Prospect research, JTBD discovery, Customer Delight ROI framing, multi-touch outbound cadences, closing. | `sales`, `prospect`, `outreach`, `cold email`, `objection` |
| [`@social`](../agents/social.md) | Social Engager | `social` | Content discovery, cold-post triage, multi-tier conversation catalysts, and community cultivation. | `social`, `engage`, `x.com`, `skool`, `linkedin`, `community` |
| [`@growth`](../agents/growth.md) | Growth & SEO Lead | `growth` | Intent matching, programmatic SEO, self-reinforcing closed growth loops, GEO/AISO, platform network dynamics. | `growth`, `SEO`, `GEO`, `AISO`, `search volume`, `schema` |
| [`@operations`](../agents/operations.md) | Operations Lead | `operations` | Empirical metrics dashboards, telemetry tracking, sprint velocity, and workforce state. | `operations`, `ops`, `metrics`, `telemetry`, `velocity`, `KPIs` |
| [`@researcher`](../agents/researcher.md) | Feature Researcher | `growth` / `dev` | Research-first feature discovery, gap analysis, competitive teardowns, and structured PRD specs. | `researcher`, `feature`, `PRD`, `spec`, `requirement` |
| [`@launcher`](../agents/launcher.md) | Launch Specialist | `launch` | Zero-revenue monetization quarterback, Time to First Dollar (TTFD) sprints, pre-sale painted doors, concierge MVPs, and TTOU 100-user distribution scale. | `launch`, `pre-sale`, `first dollar`, `TTFD`, `TTOU`, `100 users` |
| [`@unbundler`](../agents/unbundler.md) | Micro-SaaS Architect | `advisor` | Incumbent software deconstruction, single-feature micro-SaaS opportunities, Spreadsheet Moat scorecards, and zero-bloat PRDs. | `unbundle`, `micro-saas`, `atomic saas`, `incumbent bloat`, `single-feature tool` |
| [`@disruptor`](../agents/disruptor.md) | Disruption Scout | `advisor` | Million-dollar market gaps, macro consulting trend synthesis (McKinsey/BCG/Bain), and lean validation tests. | `disrupt`, `disruption`, `market trends`, `billion dollar market`, `mckinsey`, `bcg` |

---

## 📦 Modular Team Packs

Each domain team is configured via a structured `pack.json` and comprehensive `pack.md`:

### 1. Development (`teams/dev/`)
- **Agents:** `@programmer`
- **Rules:** `clean-coder.md` (TDD, symbol deduplication, diff compression, error handling)
- **Skills:** `clean-coder`, `code-graph`, `post-code-review`, `codebase-improvement`, `jules-integration`, `pr-review`, `doc-generator`, `agent-parallelization`, `wf-investigate`
- **Interactive Commands:** `/wf-investigate` (also invoked via `codebase-improvement` or autonomous coordinator)

### 2. Design (`teams/design/`)
- **Agents:** `@designer`
- **Rules:** `design-standards.md` (0 emojis as UI icons, vector packs, Refero styles, DESIGN.md spec, progressive disclosure)
- **Skills:** `ui-ux-design`, `visual-design-fundamentals`, `design-anti-patterns`, `brand-guidelines`, `image-workflow`, `site-setup`
- **Invocation:** Triggered via `site-setup` (Step 2) and prompt requests (*"Generate DESIGN.md"*, *"Review UI for anti-patterns"*)

### 3. Marketing (`teams/marketing/`)
- **Agents:** `@marketer`
- **Rules:** `design-standards.md`
- **Skills:** `persona-management`, `brand-guidelines`, `business-frameworks`, `image-workflow`, `ai-search-optimization`, `memory-management`, `hypothesis-tracker`, `market-validation`
- **Invocation:** Triggered via `site-setup` (Step 1) and prompt requests (*"Define brand context"*, *"Validate market demand"*)

### 4. Sales (`teams/sales/`)
- **Agents:** `@sales`
- **Skills:** `persona-management`, `brand-guidelines`, `memory-management`, `wf-advisor`
- **Interactive Commands:** `/wf-advisor` (strategic advisory & consultative discovery)

### 5. Social (`teams/social/`)
- **Agents:** `@social`
- **Rules:** `social-engagement.md` (Anti-bot safety, value-first comments, multi-tier threads, cold-post triage)
- **Skills:** `social-engagement`, `persona-management`, `brand-guidelines`, `memory-management`
- **Invocation:** Triggered via prompt requests (*"Evaluate social posts"*, *"Generate social dashboard"*) and scripts

### 6. Growth & SEO (`teams/growth/`)
- **Agents:** `@growth`, `@researcher`
- **Rules:** `design-standards.md`
- **Skills:** `persona-management`, `ai-search-optimization`, `business-frameworks`, `feature-research`, `doc-generator`, `memory-management`, `hypothesis-tracker`, `market-validation`
- **Invocation:** Triggered via `feature-research` and prompt requests (*"Research feature"*, *"Optimize AI search visibility"*)

### 7. Operations (`teams/operations/`)
- **Agents:** `@operations`
- **Rules:** `base.md`, `session-context.md`
- **Skills:** `usage-tracker`, `session-context`, `memory-management`, `issue-tracker`, `wf-sync`, `task-tracker`
- **Interactive Commands:** `/wf-sync` (daily standups, strategic reviews, personal sync `--me`)

### 8. Compliance (`teams/compliance/`)
- **Agents:** None (deterministic static analysis maintained by `integrity-validator` skill)
- **Rules:** `file-integrity.md`, `mcp-protection.md`
- **Skills:** `integrity-validator`, `issue-tracker`, `session-context`, `usage-tracker`, `task-tracker`
- **Invocation:** Triggered via pre-commit/standup quality gates and prompt requests (*"Verify link integrity"*, *"Check reference lineage"*)

### 9. Launch & Fast Validation (`teams/launch/`)
- **Agents:** `@launcher`
- **Rules:** `design-standards.md`, `clean-coder.md`
- **Skills:** `launch-playbook`, `market-validation`, `hypothesis-tracker`, `business-frameworks`, `brand-guidelines`, `ui-ux-design`, `persona-management`, `ai-search-optimization`
- **Invocation:** Triggered via prompt requests (*"Launch validation playbook"*, *"Plan sprint to first dollar (TTFD)"*)

### 10. Strategy, Advisory & Ideation (`teams/advisor/`)
- **Agents:** `@unbundler`, `@disruptor`
- **Rules:** `design-standards.md`
- **Skills:** `site-setup`, `feature-research`, `brand-guidelines`, `memory-management`, `issue-tracker`, `hypothesis-tracker`, `market-validation`, `wf-advisor`, `wf-ideate`
- **Interactive Commands:** `/wf-advisor` (universal strategic advisory), `/wf-ideate` (dual-engine unbundling and disruption discovery)

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

