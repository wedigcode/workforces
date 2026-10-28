# Modular Workforces: Teams & Agent Roster

A modular architecture for AI agent workforces. Instead of dumping all agents, rules, skills, and workflows into a single bloated global prompt, capabilities are organized into **Core Leadership** and **Installable Domain Team Packs**.

---

## 🏛️ Architecture Overview

```
.
├── agents/                        # Standardized single-responsibility agents (@wf-*)
│   ├── wf-project-manager.md      # @wf-project-manager (Backlog & Roadmap)
│   ├── wf-programmer.md           # @wf-programmer (Engineering & TDD)
│   ├── wf-designer.md             # @wf-designer (Visual Direction & UI/UX QA)
│   ├── wf-marketer.md             # @wf-marketer (Copywriting & Brand Strategy)
│   ├── wf-sales.md                # @wf-sales (Outbound & Deal Closing)
│   ├── wf-social.md               # @wf-social (Community & Content Triage)
│   ├── wf-growth.md               # @wf-growth (SEO & Generative Engine Optimization)
│   ├── wf-operations.md           # @wf-operations (Telemetry & Sprint Velocity)
│   ├── wf-researcher.md           # @wf-researcher (Feature Scoping & PRDs)
│   ├── wf-scribe.md               # @wf-scribe (Session Context Persistence)
│   ├── wf-launcher.md             # @wf-launcher (Fast Validation & Monetization)
│   ├── wf-unbundler.md            # @wf-unbundler (Atomic Micro-SaaS Deconstruction)
│   └── wf-disruptor.md            # @wf-disruptor (Macro Trend & Disruption Scouting)
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
| [`@wf-project-manager`](../agents/wf-project-manager.md) | Project Manager | Core | Backlog prioritization, Value Stick scoring, SaaS unit economics, sprint syncs, and GitHub project sync. | `roadmap`, `backlog`, `planning`, `sprint`, `sync` |
| [`@wf-scribe`](../agents/wf-scribe.md) | Scribe | Core | Dense, zero-narrative session context recording and architectural decision persistence. | `context`, `wf-session-context`, `save notes` |
| [`@wf-programmer`](../agents/wf-programmer.md) | Programmer | `dev` | Software development, TDD, symbol graph lookup, diff compression, and automated post-edit reviews. | `code`, `programmer`, `dev`, `developer`, `refactor`, `bug fix` |
| [`@wf-designer`](../agents/wf-designer.md) | Designer | `design` | Visual concept creation, design tokens, UI/UX architecture, layout specifications, and design QA reviews. | `designer`, `design`, `UI`, `UX`, `layout`, `visual`, `CSS` |
| [`@wf-marketer`](../agents/wf-marketer.md) | Marketer | `marketing` | JTBD positioning, Connected Strategy engagement, PAS copywriting, email cadences, and closed growth loops. | `marketing`, `marketer`, `copy`, `copywriting`, `campaign` |
| [`@wf-sales`](../agents/wf-sales.md) | Sales Specialist | `sales` | Prospect research, JTBD discovery, Customer Delight ROI framing, multi-touch outbound cadences, closing. | `sales`, `prospect`, `outreach`, `cold email`, `objection` |
| [`@wf-social`](../agents/wf-social.md) | Social Engager | `social` | Content discovery, cold-post triage, multi-tier conversation catalysts, and community cultivation. | `social`, `engage`, `x.com`, `skool`, `linkedin`, `community` |
| [`@wf-growth`](../agents/wf-growth.md) | Growth & SEO Lead | `growth` | Intent matching, programmatic SEO, self-reinforcing closed growth loops, GEO/AISO, platform network dynamics. | `growth`, `SEO`, `GEO`, `AISO`, `search volume`, `schema` |
| [`@wf-operations`](../agents/wf-operations.md) | Operations Lead | `operations` | Empirical metrics dashboards, telemetry tracking, sprint velocity, and workforce state. | `operations`, `ops`, `metrics`, `telemetry`, `velocity`, `KPIs` |
| [`@wf-researcher`](../agents/wf-researcher.md) | Feature Researcher | `growth` / `dev` | Research-first feature discovery, gap analysis, competitive teardowns, and structured PRD specs. | `researcher`, `feature`, `PRD`, `spec`, `requirement` |
| [`@wf-launcher`](../agents/wf-launcher.md) | Launch Specialist | `launch` | Zero-revenue monetization quarterback, Time to First Dollar (TTFD) sprints, pre-sale painted doors, concierge MVPs, and TTOU 100-user distribution scale. | `launch`, `pre-sale`, `first dollar`, `TTFD`, `TTOU`, `100 users` |
| [`@wf-unbundler`](../agents/wf-unbundler.md) | Micro-SaaS Architect | `advisor` | Incumbent software deconstruction, single-feature micro-SaaS opportunities, Spreadsheet Moat scorecards, and zero-bloat PRDs. | `unbundle`, `micro-saas`, `atomic saas`, `incumbent bloat`, `single-feature tool` |
| [`@wf-disruptor`](../agents/wf-disruptor.md) | Disruption Scout | `advisor` | Million-dollar market gaps, macro consulting trend synthesis (McKinsey/BCG/Bain), and lean validation tests. | `disrupt`, `disruption`, `market trends`, `billion dollar market`, `mckinsey`, `bcg` |

---

## 📦 Modular Team Packs

Each domain team is configured via a structured `pack.json` and comprehensive `pack.md`:

### 1. Development (`teams/dev/`)
- **Agents:** `@wf-programmer`
- **Rules:** `wf-clean-coder.md` (TDD, symbol deduplication, diff compression, error handling)
- **Skills:** `wf-clean-coder`, `wf-code-graph`, `wf-post-code-review`, `wf-codebase-improvement`, `wf-jules-integration`, `wf-pr-review`, `wf-doc-generator`, `wf-agent-parallelization`, `wf-investigate`
- **Interactive Commands:** `/wf-investigate` (also invoked via `wf-codebase-improvement` or autonomous coordinator)

### 2. Design (`teams/design/`)
- **Agents:** `@wf-designer`
- **Rules:** `wf-design-standards.md` (0 emojis as UI icons, vector packs, Refero styles, DESIGN.md spec, progressive disclosure)
- **Skills:** `wf-ui-ux-design`, `wf-visual-design-fundamentals`, `wf-design-anti-patterns`, `wf-brand-guidelines`, `wf-image-workflow`, `wf-site-setup`
- **Invocation:** Triggered via `wf-site-setup` (Step 2) and prompt requests (*"Generate DESIGN.md"*, *"Review UI for anti-patterns"*)

### 3. Marketing (`teams/marketing/`)
- **Agents:** `@wf-marketer`
- **Rules:** `wf-design-standards.md`
- **Skills:** `wf-persona-management`, `wf-brand-guidelines`, `wf-business-frameworks`, `wf-image-workflow`, `wf-ai-search-optimization`, `wf-memory-management`, `wf-hypothesis-tracker`, `wf-market-validation`
- **Invocation:** Triggered via `wf-site-setup` (Step 1) and prompt requests (*"Define brand context"*, *"Validate market demand"*)

### 4. Sales (`teams/sales/`)
- **Agents:** `@wf-sales`
- **Skills:** `wf-persona-management`, `wf-brand-guidelines`, `wf-memory-management`, `wf-advisor`
- **Interactive Commands:** `/wf-advisor` (strategic advisory & consultative discovery)

### 5. Social (`teams/social/`)
- **Agents:** `@wf-social`
- **Rules:** `wf-social-engagement.md` (Anti-bot safety, value-first comments, multi-tier threads, cold-post triage)
- **Skills:** `wf-social-engagement`, `wf-persona-management`, `wf-brand-guidelines`, `wf-memory-management`
- **Invocation:** Triggered via prompt requests (*"Evaluate social posts"*, *"Generate social dashboard"*) and scripts

### 6. Growth & SEO (`teams/growth/`)
- **Agents:** `@wf-growth`, `@wf-researcher`
- **Rules:** `wf-design-standards.md`
- **Skills:** `wf-persona-management`, `wf-ai-search-optimization`, `wf-business-frameworks`, `wf-feature-research`, `wf-doc-generator`, `wf-memory-management`, `wf-hypothesis-tracker`, `wf-market-validation`
- **Invocation:** Triggered via `wf-feature-research` and prompt requests (*"Research feature"*, *"Optimize AI search visibility"*)

### 7. Operations (`teams/operations/`)
- **Agents:** `@wf-operations`
- **Rules:** `wf-base.md`, `wf-session-context.md`
- **Skills:** `wf-usage-tracker`, `wf-session-context`, `wf-memory-management`, `wf-issue-tracker`, `wf-sync`, `wf-task-tracker`
- **Interactive Commands:** `/wf-sync` (daily standups, strategic reviews, personal sync `--me`)

### 8. Compliance (`teams/compliance/`)
- **Agents:** None (deterministic static analysis maintained by `wf-integrity-validator` skill)
- **Rules:** `wf-file-integrity.md`, `wf-mcp-protection.md`
- **Skills:** `wf-integrity-validator`, `wf-issue-tracker`, `wf-session-context`, `wf-usage-tracker`, `wf-task-tracker`
- **Invocation:** Triggered via pre-commit/standup quality gates and prompt requests (*"Verify link integrity"*, *"Check reference lineage"*)

### 9. Launch & Fast Validation (`teams/launch/`)
- **Agents:** `@wf-launcher`
- **Rules:** `wf-design-standards.md`, `wf-clean-coder.md`
- **Skills:** `wf-launch-playbook`, `wf-market-validation`, `wf-hypothesis-tracker`, `wf-business-frameworks`, `wf-brand-guidelines`, `wf-ui-ux-design`, `wf-persona-management`, `wf-ai-search-optimization`
- **Invocation:** Triggered via prompt requests (*"Launch validation playbook"*, *"Plan sprint to first dollar (TTFD)"*)

### 10. Strategy, Advisory & Ideation (`teams/advisor/`)
- **Agents:** `@wf-unbundler`, `@wf-disruptor`
- **Rules:** `wf-design-standards.md`
- **Skills:** `wf-site-setup`, `wf-feature-research`, `wf-brand-guidelines`, `wf-memory-management`, `wf-issue-tracker`, `wf-hypothesis-tracker`, `wf-market-validation`, `wf-advisor`, `wf-ideate`
- **Interactive Commands:** `/wf-advisor` (universal strategic advisory), `/wf-ideate` (dual-engine unbundling and disruption discovery)

---

## 🎭 Dynamic Personas vs. Agents

- **Agents (`agents/*.md`)** are the **functional operators** (tools, workflows, rules, coding, auditing).
- **Personas (`workforces/personas/*.json`)** are the **case-by-case voices and customer segments** managed dynamically via the `wf-persona-management` skill.
- **Zero Hard-Coding**: No personas are hard-coded in agent markdown files. They are created on a project-by-project basis in `workforces/personas/` with AI domain recommendations.
  - **Author Voice Personas**: e.g., *The Technical Architect* (deep tech, systems design), *The AI Enabler* (agentic workflows, builder energy), *The Trusted Local Craftsman* (approachable, reliable).
  - **Target Audience Personas**: e.g., *Enterprise Tech Decision-Maker*, *Growth Startup Founder*, *Busy Homeowner*.

---

## ⚡ Token Parsimony & Anti-Bloat Benefits

1. **Zero Duplicate Files:** Eliminated duplicate copies of skills and rules between root folders, `teams/skills/`, and `plugins/*/`.
2. **Context Efficiency:** Agents only load the rules, skills, and tools relevant to their specific domain.
3. **Selective Installation:** Projects only copy the files for their installed teams, eliminating prompt bloat.
4. **Transparent Role Discovery:** Users can inspect installed teams and instantly identify which agent handles their task.

