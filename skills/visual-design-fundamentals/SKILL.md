---
name: visual-design-fundamentals
description: Establishes foundational visual design rules covering typography scales, harmonic color theory, whitespace balancing, responsive 8pt layout grids, and visual hierarchy. Reach for this skill before authoring UI components, styling landing pages, selecting typography and color palettes, or evaluating graphic assets to ensure professional polish, legibility, and aesthetic coherence.
---

# Visual Design Fundamentals

Core mathematical principles and spatial standards that produce clean, professional, and cohesive digital interfaces. For anti-pattern prevention, refer to [`design-anti-patterns`](../design-anti-patterns/SKILL.md).

---

## 1. Visual Hierarchy & The Squint Test

Guide user attention through deliberate contrast, sizing, and breathing room:
- **Primary Anchor**: Highest visual weight reserved strictly for the core action or primary value prop.
- **Squint Test**: Squint at the screen; the first element noticed MUST be the primary intended action.
- **Scanning Rhythm**: Align primary anchors along the natural F/Z reading path (top-left to bottom-right).

---

## 2. Typography Token Scale

| Rule | Technical Parameter | Purpose |
|------|---------------------|---------|
| **Font Count** | **Max 2 font families** | 1 character Display font + 1 clean UI Sans-Serif (Inter, Geist). |
| **Font Scale Ladder** | **Reference Type Ladder** (based on 16px base) | `12px` (caption), `14px` (sub), `16px` (body), `20px` (h4), `24px` (h3), `32px` (h2), `48px` (h1). |
| **Line Height** | **1.4×–1.6×** for body; **1.1×–1.2×** for headings | Tight headings prevent line drifting; spacious body enhances legibility. |
| **Line Length** | **45–75 characters** (`max-w-prose` / ~65ch) | Prevents eye fatigue from over-extended reading lines. |

---

## 3. Color Token System & The 60-30-10 Rule

Build palettes using functional surface layers rather than arbitrary color picking:
- **60% Dominant Surface**: Neutral background canvas (`bg-background`, `bg-surface`, deep slate `#090d16` or warm off-white).
- **30% Structural Secondary**: Card surfaces, sidebars, borders (`border-border/40`), and secondary text (`text-muted`).
- **10% High-Intent Accent**: Reserved strictly for primary interactive CTAs, active status indicators, and key focus rings.
- **User Preference Adherence**: Always verify selections against `workforces/memory/design-preferences.md`.

---

## 4. 8pt Spatial Grid & Whitespace Hierarchy

All spacing, padding, margins, and component dimensions snap strictly to multiples of **8px** (with **4px** half-step for micro-details):
- **Micro Spacing (`4px`, `8px`, `12px`)**: Space between an icon and its label, padding within tight input chips.
- **Component Spacing (`16px`, `24px`, `32px`)**: Card interior padding (`p-6`), gap between form inputs (`gap-4`).
- **Macro Spacing (`48px`, `64px`, `96px`)**: Padding between page sections, margin between hero and feature grid.
- **Rule of Restraint**: When an interface feels cluttered, increase whitespace before reducing font sizes.

---

## Pre-Handoff Visual Polish Checklist

- [ ] **Dual-Font Discipline**: Strictly <= 2 font families loaded and utilized.
- [ ] **Modular Line Heights**: Headings have tight line-heights (1.1–1.2x); body copy is relaxed (1.4–1.6x).
- [ ] **Color Budget**: Accent color covers <= 10% of total visual surface.
- [ ] **8pt Grid Compliance**: All padding, margins, and gaps snap to the 8pt scale (no magic numbers like 13px or 27px).
- [ ] **Layered Depth**: Surfaces show clear hierarchy through background tonal shifts or 1px micro-borders.
