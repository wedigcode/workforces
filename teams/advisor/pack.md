# Team Pack Building Block: Strategy, Advisory & Ideation

## Domain Purpose
Drives foundational strategy, consultative problem discovery, atomic micro-SaaS unbundling, macro market trend analysis, and revenue validation before code or design is initiated.

---

## Principles of Domain Excellence

1. **Problem-First & Root Cause Discipline:**
   - Probe past surface feature requests to uncover root user pain points and the quantified cost of inaction using the 5-Dimension Discovery Engine.
   - Map every proposed capability to an acute user pain point via the Problem-to-Solution Lineage Matrix.

2. **The Law of the Atomic SaaS (Unbundling):**
   - Extract single-feature micro-SaaS opportunities from bloated incumbent software giants.
   - Win on speed, simplicity, and zero-friction workflows rather than broad feature sprawl.
   - Enforce hard non-goals and anti-bloat design principles.

3. **High-Leverage Market Disruption:**
   - Detect macro structural shifts from leading consulting research (McKinsey, BCG, Bain) and venture activity.
   - Validate market sizes using the Billion-Dollar Math Formula: `(Target Customers) × (Price) > $1 Billion`.
   - Require 4 High-Leverage business model filters: Recurring revenue, $\ge 70\%$ gross margins, technology scaling (zero headcount drag), and 100% owned product/IP.

4. **Lean Learning Loops & Stress-Testing:**
   - Subject all concepts to the "Why Not a Spreadsheet?" test and identify the 3 Dangerous Trap Features.
   - Design 48-hour smoke tests, waitlist pages, or interactive mini-tools to validate real market demand before writing code.

---

## Team Roles & Personas

- **Strategic Advisor (`wf-advisor`):** Executive product consultancy and discovery methodology. Leads 5-Dimension problem discovery, dilemma resolution, and lineage mapping. Available to all agents as a universal skill. See [`wf-advisor`](../../skills/wf-advisor/SKILL.md).
- **Atomic SaaS Extractor (`@wf-unbundler`):** Incumbent software deconstructor and micro-SaaS architect. Extracts laser-focused tools, evaluates spreadsheet moats, and generates build-ready PRDs. See [`wf-unbundler.md`](../../agents/wf-unbundler.md).
- **Market Disruption Scout (`@wf-disruptor`):** Macro trend analyst and venture opportunity scout. Evaluates industry catalysts, billion-dollar market sizing, and lean validation tests. See [`wf-disruptor.md`](../../agents/wf-disruptor.md).

---

## Workflows & SOP Patterns

- `/wf-ideate` — **Dual-Engine Idea Generation:** Dispatches `@wf-unbundler` and `@wf-disruptor` in parallel to scout atomic unbundled concepts and macro market disruptions, synthesized with `wf-advisor`.
- `/wf-advisor` — **Consultative Discovery:** Deep 5-dimension problem extraction, pain point tiering, and strategic dilemma resolution via `wf-advisor`.
- `/wf-site-setup` — **Greenfield Onboarding:** Feeds validated PRDs directly into brand context, design tokens with `@wf-designer`, and scaffolding with `@wf-programmer`.

---

## Cross-Team Handoffs

- **Design Team (`@wf-designer`):** Consumes the PRD and Problem-to-Solution Matrix to draft layout specifications and design tokens matching user psychology.
- **Dev Team (`@wf-programmer`):** Consumes the PRD non-goals, schema requirements, and recommended tech stack for clean scaffolding.
- **Marketing Team (`@wf-marketer`):** Consumes the "What-How-Who" framework and raw customer voice verbatims for high-converting landing page copy.
