---
description: Establishes brand identity, voice, visual system, and audience context for any new project. Produces docs/brand-context.md — required before design, marketing, or UI work begins.
---

# /brand-context — Brand Identity Foundation

Captures and documents the brand identity for a project before any design, marketing, or UI work begins. Run this at the start of any new project — or when a brand refresh is needed.

This workflow produces `docs/brand-context.md` — the single source of truth for brand decisions shared across the **design team**, **marketing team**, **dev team** (for UI tokens), and **content team**.

---

## Before You Start

Check if brand context already exists:
```
docs/brand-context.md
```

If it exists, read it and ask the user: _"This project already has brand context. Do you want to update it or start fresh?"_

---

## Step 1 — Discovery Interview

Gather the following from the user. Ask conversationally — don't fire all questions at once:

### Business Context
- What does this product/business do? (One sentence — the elevator pitch)
- What problem does it solve, and for whom?
- What's the business model? (SaaS, e-commerce, local service, agency, etc.)
- Who are the top 2–3 competitors? What do they do well, and where do they look generic?

### Audience
- Who is the target customer? (Demographics, role, experience level)
- What pain points are they experiencing right now?
- How do they describe the problem in their own words? (Use their language)
- Where do they hang out? (Search, social, communities, forums)

### Brand Vibe & Voice
- 3–5 adjectives that describe the brand personality (e.g. bold, approachable, technical, playful)
- 3 brands (any industry) whose aesthetic you admire and why
- What should the brand never feel like? (Cheap, corporate, cluttered, boring?)
- What's the brand's tone? Formal → casual spectrum?

### Visual Identity
- Do existing colors, logos, or fonts already exist? (Gather hex codes if yes)
- Any visual mood words? (e.g. dark & editorial, warm & earthy, clean & minimal, vibrant & energetic)
- What imagery style fits? (Photography, illustration, flat icons, none)

---

## Step 2 — Generate Brand Context File

Create `docs/brand-context.md` with all sections filled — **no placeholders remaining**.

Use the gathered information plus your design expertise to make specific, opinionated recommendations where the user hasn't decided.

```markdown
# Brand Context: [Project Name]

_Last updated: [date]_

---

## 1. Business Identity

**Elevator pitch:** [One sentence]

**Business model:** [SaaS / Local Service / E-commerce / Agency / etc.]

**Core problem solved:**
> [The specific problem, in customer language]

**Target outcome for the customer:**
> [What does success look like for them after using this?]

---

## 2. Target Audience Personas (Customer Segments)

### Persona 1: [Primary Segment Name / Role — e.g. "Enterprise Engineering Leader"]
- **Role & Profile:** [e.g. VP Eng, CTO, Senior Architect at 100+ person company]
- **Core Frustrations & Bottlenecks:** [e.g. Technical debt, delivery delays, compliance risk]
- **Value Proposition Trigger:** [e.g. Enterprise SLA, security audits, provable ROI metrics]
- **How They Search & Speak:** [Keywords, terminology, verbatim phrases]

### Persona 2: [Secondary Segment Name / Role — e.g. "Growth Startup Founder"]
- **Role & Profile:** [e.g. Seed/Series A Founder, Solopreneur, Product Lead]
- **Core Frustrations & Bottlenecks:** [e.g. Hiring cost, slow time to market, bandwidth limits]
- **Value Proposition Trigger:** [e.g. Speed, DIY ease, self-serve setup, transparent pricing]
- **How They Search & Speak:** [Keywords, terminology, verbatim phrases]

### Persona 3: [Optional Niche Segment — e.g. "Agency / Workflow Integrator"]
- **Role & Profile:** [e.g. Consultant, agency operator managing multiple client brands]
- **Core Frustrations & Bottlenecks:** [e.g. Client handoff friction, tool fragmentation]
- **Value Proposition Trigger:** [e.g. Multi-tenancy, modular team packaging, white-labeling]

---

## 3. Brand Voice & Author Personas

**Core Brand Personality:** [3–5 adjectives — e.g. Authoritative, pragmatic, crisp, forward-looking]

### Author / Voice Personas (For Social Media & Thought Leadership)
- **Persona A: "The CTO / Systems Thinker"**
  - **Tone & Perspective:** Architectural rigor, scalability, empirical data, engineering ROI.
  - **Best For:** Technical teardowns, infrastructure debates, GitHub/dev community discussions.
- **Persona B: "The AI Enabler / Workflow Pragmatist"**
  - **Tone & Perspective:** Fast iteration, agentic leverage, practical automation tips, builder energy.
  - **Best For:** Social engagement (X.com/LinkedIn), founder communities, tactical "how-to" playbooks.

| Dimension | Where We Land |
|-----------|--------------|
| Formal ↔ Casual | [e.g. "Casual but competent"] |
| Serious ↔ Playful | [e.g. "Primarily helpful, dry humor ok"] |
| Expert ↔ Peer | [e.g. "Peer who's 2 steps ahead"] |

**Voice rules:**
- ✅ Do: [Specific voice guidance — lead with frameworks, share raw metrics, ask catalytic questions]
- ❌ Never: [Words, phrases, or tones to avoid — generic fluff, corporate jargon, sycophancy]


---

## 4. Visual Identity

### Color Palette

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Primary | [e.g. Brand Blue] | `#[hex]` | CTAs, logo, key accents |
| Secondary | [e.g. Dark Navy] | `#[hex]` | Backgrounds, nav |
| Neutral Light | [e.g. Off-White] | `#[hex]` | Page background |
| Neutral Dark | [e.g. Charcoal] | `#[hex]` | Body text |
| Accent | [e.g. Warm Amber] | `#[hex]` | Highlights, badges |
| Success | [Green] | `#[hex]` | Form validation, success states |
| Error | [Red] | `#[hex]` | Error states |

**Palette rationale:** [Why these colors — what feeling do they evoke?]

### Typography

| Element | Family | Weight | Size |
|---------|--------|--------|------|
| Display/H1 | [Font] | 700 | 48–64px |
| Heading/H2 | [Font] | 600 | 32–40px |
| Subheading/H3 | [Font] | 600 | 24–28px |
| Body | [Font] | 400 | 16–18px |
| Caption/Small | [Font] | 400 | 13–14px |

**Font rationale:** [Why these fonts — personality and technical fit]

### Imagery Style

- **Photography:** [e.g. "Real people, candid shots, warm tone. No stock-photo smiles."]
- **Illustration:** [e.g. "None" or "Minimal line illustrations for empty states only"]
- **Icons:** [e.g. "Lucide icons at 20px, 1.5px stroke" or "No icons — use text and numbers"]
- **Mood keywords:** [e.g. "Warm, editorial, high-contrast, intentional whitespace"]

---

## 5. Design Principles (Project-Specific)

Based on the brand and competitive landscape, these design rules apply to this project:

1. [e.g. "Never alternate dark/light sections — use one background throughout"]
2. [e.g. "Left-align all body content — centered text only in hero"]
3. [e.g. "No glassmorphism — solid cards with 1px borders"]
4. [e.g. "Buttons use 6px border-radius, never pill-shaped"]
5. [e.g. "One accent color per page — no rainbow highlights"]

---

## 6. Competitors & Differentiation

| Competitor | What They Do Well | What Looks Generic |
|------------|-------------------|--------------------|
| [Competitor 1] | [Strength] | [Weakness] |
| [Competitor 2] | [Strength] | [Weakness] |

**Our visual differentiation strategy:**
> [How we stand apart from competitors in design and voice]

---

## 7. SEO & Content Keywords

**Primary keyword:** [Main term]
**Secondary keywords:** [2–3 supporting terms]
**Long-tail keywords:** [3–5 specific phrases]
**Geo modifiers (if local):** [City, region]

---

## 8. Usage Notes

- **Generated:** [date]
- **Last reviewed:** [date]
- **Owner:** Design Team
- **Shared with:** Dev team (for UI tokens), Marketing team (for copy voice)
```

---

## Step 3 — Extract Design Tokens (Optional)

If the project has a frontend codebase, output CSS custom properties from the brand context:

```css
/* Extracted from docs/brand-context.md */
:root {
  /* Colors */
  --color-primary: #[hex];
  --color-secondary: #[hex];
  --color-neutral-light: #[hex];
  --color-neutral-dark: #[hex];
  --color-accent: #[hex];
  --color-success: #[hex];
  --color-error: #[hex];

  /* Typography */
  --font-heading: '[Font Family]', sans-serif;
  --font-body: '[Font Family]', sans-serif;

  /* Type scale */
  --text-xs: 0.8125rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;

  /* Spacing scale (4px base) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
}
```

Save to `src/styles/tokens.css` or equivalent.

---

## Step 4 — Update Workflow Memory

Log brand decisions in `workforces/workstate.md` under `## Brand & Design Decisions`.

---

## Completion Checklist

- [ ] Discovery interview complete — all gaps filled
- [ ] `docs/brand-context.md` created — no placeholders remaining
- [ ] Color palette documented with hex codes and usage roles
- [ ] Typography documented with families, weights, and scale
- [ ] Brand voice rules documented (do/never)
- [ ] Project-specific design principles listed (what to avoid in this project)
- [ ] CSS tokens extracted (if frontend project)
- [ ] Workstate updated with brand decisions
- [ ] Shared with dev team and marketing team

---

## Notes for the Design Team

- This document is **living** — update it when brand decisions evolve
- `docs/brand-context.md` is the **authority** — any design or copy that conflicts with it needs discussion, not silent deviation
- The `@designer` agent reads this file first before every design review
- The `marketing` team (`@marketer`) should reference Section 3 (Voice) for all copy

