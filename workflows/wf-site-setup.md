---
description: Interactive Site Setup & Product Brief pipeline — guides you through business model, consultative problem discovery with @advisor, audience extraction, visual concept & token specification, tech stack selection with scaffolding safeguards, and framework-aware AI search protocol setup.
---

# /wf-site-setup — Greenfield Site Setup & Product Brief Pipeline

The end-to-end conversational onboarding workflow for launching a new website, web app, or SaaS property in an empty codebase. 

Coordinated by the **Project Manager** (`@project-manager`) with specialized handoffs across the **Strategic Advisor** (`@advisor`), **Marketing** (`@marketer`), **Designer** (`@designer`), **Compliance/Sales** (`@compliance`/`@sales`), and **Engineering** (`@programmer`).

---

## 🧭 Workflow Overview

```mermaid
graph TD
    A0["Step -1: Pre-Flight Ideation (/wf-ideate)<br/>@unbundler & @disruptor Dual-Engine"] -.->|If idea needed| A["Step 0: @project-manager<br/>Discovery & Scope Intake"]
    A --> A2["Step 0b: @advisor<br/>Consultative Problem & Pain Point Discovery"]
    A2 --> B["Step 1: Marketing & SEO<br/>Audience, Keywords, Value Prop"]
    B --> C["Step 2: @designer<br/>Visual Concept & Tokens"]
    C --> D["Step 3: Compliance & Sales<br/>FTC Rules & Conversion Model"]
    D --> E["Step 4: @programmer (Dev)<br/>Tech Stack & AI Protocols"]
    E --> F["Step 5: PM Finalization<br/>Product Brief & Workstate Roadmap"]
```

---

## Step -1 — Pre-Flight Ideation & Unbundling Hook (Optional)

> 💡 **Need an idea or starting from scratch?**
> If the user does not have a defined product or business concept yet, run **`/wf-ideate`** first. 
> `/wf-ideate` dispatches the **Atomic SaaS Extractor** (`@unbundler`) and **Market Disruption Scout** (`@disruptor`) in parallel to evaluate spreadsheet moats, billion-dollar market formulas, and build-ready PRDs before initiating site setup.

---

## Step 0 — Strategy & Scope Intake (`@project-manager`)

Gather foundational business context from the user:

1. **What is the product or business name?**
2. **What type of site are we building?**
   - SaaS / Web App
   - Local Service Lead Generation (e.g. contractor/home services network)
   - Direct Service Business (e.g. agency, clinic, law firm)
   - E-commerce / D2C Store
   - Blog / Content / Media Hub
   - Developer Tool / Open Source
3. **What is the primary business model?**
   - **Lead Generation / Affiliate**: Requires legal disclaimers, contractor matching disclosures, no false guarantees. Handled by `@compliant-page-builder`.
   - **Direct Service / SaaS / E-commerce**: Business performs work directly. Reviews, pricing tables, and guarantees permitted. Handled by `@page-builder`.
4. **Primary Conversion Action**:
   - Free trial / app signup
   - Lead quote request / phone call
   - Direct checkout / purchase
   - Newsletter subscription

> **PM Action**: Ensure target teams (`design`, `marketing`, `dev`, `compliance`, `sales`) are registered in `workforces/workrules.md` and `workforces/teams/`.

---

## Step 0b — Consultative Discovery & Problem Extraction (`@advisor`)

The **Strategic Advisor** (`@advisor`) takes over to conduct an active, conversational discovery interview per [`consultant-discovery-framework.md`](../skills/site-setup/templates/consultant-discovery-framework.md):

> 💬 **Advisor Directives**:
> - Ask **1 to 2 questions per turn**; never dump a checklist.
> - Use the **"5 Whys"** to move past surface features to root causes.
> - Quantify friction (lost hours, lost revenue, drop-off rates).

### 🔍 5-Dimension Discovery Probes:
1. **The Root Problem & Catalyst**:
   - *"What is fundamentally broken or inefficient in your workflow or market today?"*
   - *"Why solve this right now? What event, metric, or friction triggered this priority?"*
2. **Acute Pain Points Breakdown**:
   - **Tier 1 (Critical Blockers):** What causes direct revenue loss, compliance risks, or customer churn?
   - **Tier 2 (Operational Drag):** What repetitive manual toil or wasted hours are dragging the team down?
   - **Tier 3 (UX Friction):** Where are users getting confused, frustrated, or abandoning?
3. **Target Persona & Raw Voice**:
   - *"Who feels this pain most acutely on a daily basis?"*
   - *"When they vent about this problem to a friend or coworker, what exact words do they use?"*
4. **Current Workarounds & Why Existing Tools Fail**:
   - *"How are you or your users coping right now? (Messy spreadsheets, manual emails, Zapier hacks?)"*
   - *"Why haven't existing market competitors or off-the-shelf tools solved this for you?"*
5. **Value Breakthrough & Quantified Stakes**:
   - *"What does a 10x breakthrough solution look like compared to an incremental fix?"*
   - *"What is the cost if this problem remains unsolved for the next 6 months?"*

> **Action**: Formulate the **Core Problem Statement**, **Pain Point Tiers**, and **Problem-to-Solution Lineage Matrix** for inclusion in `docs/product-brief.md`.

---

## Step 1 — Marketing & Positioning Handoff (`marketing` / `@seo-architect`)

Define the market position and audience resonance informed by the advisor's problem discovery:

1. **Target Customer Persona**:
   - Ideal customer profile (demographics, job title, company size, experience level).
   - Document raw pain point verbatims.
2. **Core Value Proposition**:
   - Elevator pitch (1 punchy sentence).
   - Key differentiators vs top 2–3 competitors (what makes competitors look generic or outdated).
3. **SEO & Search Intent**:
   - Primary transactional keyword (e.g., *"emergency roof repair dallas"* or *"real-time auth sdk"*).
   - 2–3 secondary long-tail keywords.
4. **Copywriting Script & Hook**:
   - Hook formula: Problem agitate → Differentiated solution → Proof → Single clear CTA.

> **Action**: Populate Section 1 (Business Identity & Problem Space) and Section 2 (Audience) in `docs/brand-context.md`.

---

## Step 2 — Visual Design, Refero Benchmarking & `DESIGN.md` (`@designer`)

The **Designer Agent** (`@designer`) explicitly leads this stage to establish a bespoke, human-crafted visual identity and eliminate generic AI templates:

> 🎨 **Designer Directives**:
> - Introduce yourself clearly as `@designer`.
> - Actively explore **Refero Styles** ([styles.refero.design](https://styles.refero.design/)), **Land-book**, and **SiteInspire** for the product category.
> - Present 2–3 named, concrete design style directions with real visual character.

1. **Refero Styles & Archetype Exploration**:
   - Browse curated real-world SaaS design systems on **[styles.refero.design](https://styles.refero.design/)**:
     - *Editorial Warm Parchment*: Warm putty/sand background (`#fbfaf7`), dark olive/charcoal text, serif display heading (Instrument Serif / Fraunces), clean Sans body, generous line-heights, subtle tactile borders.
     - *Midnight Deep Slate & Frosted Layering*: Slate-950 base (`#090d16`), subtle 1px border contrast (`border-white/8`), Cal Sans / Syne display font, Geist body, high-contrast crisp cards, micro-glow badge.
     - *Alpine Clean Precision*: Off-white clean surface (`#f8fafc`), high-contrast black typography (Cabinet Grotesk / Plus Jakarta Sans), asymmetric 60/40 hero, sharp corners (`rounded-lg`), bold minimalist actions.
     - *Darkroom Product Editorial*: Deep charcoal canvas (`#121316`), warm amber/terracotta accent, dramatic full-bleed product showcase, generous whitespace.
2. **Anti-Pattern Defense**:
   - Check against [`design-anti-patterns`](../skills/design-anti-patterns/SKILL.md) and [`design-standards`](../rules/design-standards.md) (strictly prohibit generic centered 3-card columns, gradient heading text, raw emojis, and flat single-layer gray boxes).
3. **Deliver `DESIGN.md` & CSS Design Tokens (`src/styles/tokens.css`)**:
   - Deliver a concrete `DESIGN.md` specification file containing:
     - Chosen Refero Style Archetype & Visual Mood
     - Typography Pairing: Display font + Body font with Google Fonts / Fontshare import links
     - Color Tokens: Primary, Secondary, Background, Surface, Card, Border, Muted, and Accent hex values
     - Layout Blueprint: Hero asymmetry (e.g. 60/40), staggered feature rows, testimonial treatments, single-row footer
     - Component Rules: Button variants, card surface layering, badge styling, vector icon family (`lucide-react`)
   - Write corresponding CSS custom properties to `src/styles/tokens.css`.
4. **Image Queue Initialization (Optional Asset Specs)**:
   - Populate planned image slots in `workforces/images.json` (Hero, Features, Testimonial, Preview) if custom photography or illustration assets are needed later.

> **Action**: Create `DESIGN.md`, populate `src/styles/tokens.css`, update `docs/brand-context.md`, and optionally specify required assets in `workforces/images.json`.

---

## Step 3 — Sales & Compliance Review Handoff (`compliance` / `sales`)

Verify trust signals, legal disclosures, and conversion mechanics:

1. **For Lead Generation Sites**:
   - Inject mandatory FTC / affiliate disclaimer:
     > *"Disclaimer: [Domain] is a free referral service connecting homeowners with independent contractors. We do not perform contractor services directly. All contractors are independently licensed."*
   - Verify zero false claims (*"100% guaranteed"*, *"Our licensed crew"*).
2. **For SaaS / Direct Service Sites**:
   - Formulate pricing tiers (Free / Pro / Enterprise or Standard / Premium).
   - Guarantee statements and refund policies.

---

## Step 4 — Dev & Technology Scaffolding Handoff (`dev` / `@programmer`)


Select framework, cloud hosting, and configure framework-aware AI protocols:

1. **Tech Stack Selection**:
   - **Frontend**: Next.js (App Router), Vite / React, Astro, Plain HTML/CSS, Python (FastAPI/Django).
   - **Styling**: Vanilla CSS / CSS Modules / Tailwind (confirm version) / Design Tokens.
   - **Iconography**: Lucide Icons / Heroicons / Phosphor / Tabler (`lucide-react`, `@heroicons/react`, etc. — zero raw emojis).
   - **Cloud Hosting**: Cloudflare Pages / Workers, AWS Amplify, Google Firebase / Cloud Run, Docker.
2. **Scaffolding Execution (Under Safeguard Rule)**:
   - Run the scaffolding command in non-interactive mode.
   - 🛑 **Safeguard**: If the command fails, blocks, or requires interactive terminal answers:
     - **DO NOT hand-code framework boilerplate from scratch.**
     - **STOP execution**, output the command for the user to run in their terminal, and wait for confirmation.
3. **Design Tokens Integration**:
   - Write CSS custom properties to `src/styles/tokens.css` based on brand context colors and typography.
4. **AI Protocol Files Generation**:
   - Generate language-specific `public/robots.txt`, `public/llms.txt`, `public/ai.txt`, `public/.well-known/ai-plugin.json`, and dynamic/static `sitemap` (e.g. `src/app/sitemap.ts` with `force-static` for Next.js).

---

## Step 5 — Brief Compilation & Workstate Promotion (`@project-manager`)

1. **Compile `docs/product-brief.md`**:
   Ensure all **7 Mandatory Sections** plus the **Problem-to-Solution Lineage Matrix** are documented with zero remaining placeholders:
   - 1. Core Problem Statement & Pain Points (Root cause, Tier 1–3 pain points, workarounds, cost of inaction)
   - 2. Problem-to-Solution Lineage Matrix (Mapping pain points to features and success metrics)
   - 3. Creative Concept & Narrative (Visual archetype & mood)
   - 4. Layout Specification (Header, Hero, Feature Grid, Social Proof, CTA/Pricing, Footer)
   - 5. Visual Style Guide & Tokens (Colors, fonts, vector icons)
   - 6. Content Direction & Headlines (Value prop, hooks, copy)
   - 7. Technical Stack & AI Protocols (Framework, hosting, protocols, compliance)
2. **Update `workforces/workstate.md`**:
   - Mark task 1 (`Complete /site-setup`) complete.
   - Unblock P0 tasks:
     - Task 2: Build Homepage Component Structure (per `DESIGN.md`)
     - Task 3: `@designer` Design QA Review & Anti-AI Audit
     - Task 4: SEO & Schema Validation

---

## Completion Checklist

- [ ] Project category & business model confirmed (Lead Gen vs Direct Service/SaaS)
- [ ] Consultative problem discovery completed with `@advisor` (root cause, pain points, workarounds, cost of inaction)
- [ ] Problem-to-Solution Lineage Matrix generated
- [ ] Target audience & value proposition documented in `docs/brand-context.md`
- [ ] Design archetype & Refero style benchmark ([styles.refero.design](https://styles.refero.design/)) confirmed
- [ ] `DESIGN.md` generated with typography pairing, color tokens, and layout blueprints
- [ ] CSS design tokens written to `src/styles/tokens.css`
- [ ] Cohesive vector icon pack selected (Lucide / Heroicons) — zero emojis in UI
- [ ] `workforces/images.json` populated with required assets (if needed)
- [ ] Framework scaffolded (under installer safeguard rule)
- [ ] Framework-aware AI protocol files generated (`robots.txt`, `llms.txt`, `ai.txt`, `sitemap`)
- [ ] `docs/product-brief.md` completed with all mandatory sections and lineage matrix
- [ ] `workforces/workstate.md` updated with unblocked build and Design QA tasks
