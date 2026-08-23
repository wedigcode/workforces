# Design Preferences & Anti-Preferences Memory

A persistent memory store of human design feedback, negative visual constraints (anti-preferences), approved aesthetic archetypes, and typography/palette rules. Loaded automatically by `@designer` and frontend workflows to enforce design taste and prevent repeating rejected patterns across sessions.

---

## 🚫 Negative Design Constraints (Strict Anti-Preferences)

Never use or generate these patterns in any mockup, design token, or frontend interface:

### 1. Unreadable & Low-Contrast Color Combinations
- **Yellow on Light/White:** Never use yellow, light gold, or bright amber text/icons directly over white, off-white, or light grey backgrounds (fails WCAG AA contrast).
- **Pure Black Clutter:** Avoid `#000000` pitch-black backgrounds with neon phosphor glows for standard SaaS/business interfaces. Use layered zinc/slate surfaces (`#090d16`, `#0f172a`, `#18181b`).
- **Low-Contrast Muted Copy:** Never use grey text lighter than `#71717a` (or `rgb(113, 113, 122)`) on white/light backgrounds.

### 2. Forbidden Layout & UI Clichés
- **No Emojis as UI Icons:** Zero raw unicode emojis in buttons, badges, navigation, or feature cards. Use vector SVGs (`lucide-react`, `heroicons`).
- **No Generic Gradient Text Headings:** Avoid diagonal blue-to-purple gradient text on primary h1/h2 headings. Use solid high-contrast display typography.
- **No Identical 3-Card Centered Columns:** Break layout monotony with asymmetric hero splits (60/40), staggered feature rows, or horizontal lists.
- **No Component Kitchen-Sink:** Avoid dumping 4 competing sidebars, latency telemetry chips, and search widgets on a single viewport.

---

## ✨ Positive Style Preferences & Approved Archetypes

### 1. Benchmark Archetypes ([Refero Styles](https://styles.refero.design/))
- **Primary Archetype:** Editorial & Product Focus (e.g. *Warm Parchment*, *Midnight Deep Slate*, *Alpine Precision*).
- **Surface Layering:** Intentional 3-tier hierarchy (`bg-background` -> `bg-surface` -> `bg-card` with subtle 1px border `border-border/40`).

### 2. Typography Standards
- **Display Font:** Character-rich Display font (e.g. Instrument Serif, Fraunces, Cal Sans, Syne, Cabinet Grotesk, Plus Jakarta Sans).
- **Body Font:** Clean, highly legible UI font (Inter, Geist, Plus Jakarta Sans, system-ui). Max 2 font families.

### 3. Iconography
- **Family:** Lucide Icons (or Heroicons). Single family, 1.5px/2px stroke, `currentColor` token inheritance.

---

## 📝 Human Feedback & Design Decision Journal

- **2026-08-23:** Initialized design preferences memory. Enforced strict prohibition on yellow over light/white backgrounds and reinforced Refero-grade aesthetic standards.
