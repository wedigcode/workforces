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

## 2. Target Audience

**Primary persona:** [Name + role]
- **Demographics:** [Age range, location, role]
- **Pain points:** [Specific frustrations]
- **How they search:** [Keywords, queries, phrases they use]
- **What convinces them:** [Social proof, specs, pricing clarity, demos]

**Secondary persona (if applicable):** [Name + role]

---

## 3. Brand Voice

**Core personality:** [3–5 adjectives]

| Dimension | Where We Land |
|-----------|--------------|
| Formal ↔ Casual | [e.g. "Casual but competent"] |
| Serious ↔ Playful | [e.g. "Primarily helpful, dry humor ok"] |
| Expert ↔ Peer | [e.g. "Peer who's 2 steps ahead"] |

**Voice rules:**
- ✅ Do: [Specific voice guidance]
- ❌ Never: [Words, phrases, or tones to avoid]

**Tone in specific contexts:**
- Success/wins: [e.g. Celebratory but not over-the-top]
- Errors/problems: [e.g. Direct and reassuring, no corporate speak]
- Marketing copy: [e.g. Punchy, benefit-first, short sentences]

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
- The `design-reviewer` agent reads this file first before every design review
- The `marketing` team should reference Section 3 (Voice) for all copy
