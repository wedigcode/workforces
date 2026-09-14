---
name: design-anti-patterns
description: Identifies and replaces 25 ubiquitous AI design clichés (such as floating glow cards, generic purple-blue gradients, hollow metrics, and centered hero clichés) with human-crafted, production-grade alternatives anchored in benchmark systems like Refero, Linear, and Huly. Reach for this skill when designing or reviewing web interfaces, landing pages, and component styling to ensure layouts look intentional, authentic, and professionally crafted.
---

# Design Anti-Patterns & AI Cliché Defense

AI tools reflexively default to predictable visual clichés. This skill provides a high-density reference of **25 overused AI patterns** and their production-grade alternatives. Ground designs in real-world human craft systems cataloged at **[styles.refero.design](https://styles.refero.design/)** (Huly, Mercury, Origin, Function Health, Mintlify).

---

## 25 AI Design Clichés & Production Alternatives

| # | Area | Cliché / AI Default | Failure Mode | Human-Craft Alternative |
|---|------|---------------------|--------------|-------------------------|
| 1 | Typography | **Gradient Headings**: `background-clip: text` on every hero | Visual monotony, poor legibility | Solid high-contrast text; single accent word; oversized display font. |
| 2 | Typography | **Bulleted Features**: 3–4 generic bullet points per card | Low engagement wall of text | One strong sentence; bold metric stat ("3× faster"); user pull-quote. |
| 3 | Typography | **"Simple. Powerful. Flexible."**: 3-word buzzword taglines | Vague, zero informational value | Specific outcome ("Invoices paid in 48h"); customer's exact words. |
| 4 | Visual | **Purple-to-Blue Gradients**: Diagonal hero background gradient | Generic AI prototype signature | Deep solid slate/zinc tones; warm muted earth tones; subtle texture/grain. |
| 5 | Visual | **Glassmorphism Cards**: `backdrop-filter: blur()` everywhere | Low contrast, illegible text | Solid surface cards (`bg-surface`); 1px subtle borders (`border-border/40`). |
| 6 | Visual | **Heavy Box Shadows**: `0 25px 50px -12px rgba(0,0,0,0.25)` | Muddy, dated elevation | Tight subtle shadow (`0 1px 3px rgba(0,0,0,0.08)`); 1px border; surface contrast. |
| 7 | Visual | **Decorative Blobs**: Random blurred gradient circles | Aimless visual clutter | Clean whitespace; subtle geometric dot/line grid; authentic UI screenshot. |
| 8 | Components | **3-Card Column Grid**: 3 identical cards in every section | Formulaic rhythm, layout fatigue | Asymmetric 60/40 layout; horizontal icon rows; alternating illustrations. |
| 9 | Components | **Icon-Above-Heading**: Centered icon stacked over title + text | Cookie-cutter repetition | Icon inline with heading; bold step number (01, 02); metric hero stat. |
| 10 | Components | **Badge Overuse**: "NEW", "POPULAR", "BETA" on every header | Tag clutter, desensitization | Clean typography hierarchy; subtle muted timestamp; self-evident copy. |
| 11 | Components | **Accent Left-Border**: `border-left: 4px solid #3b82f6` | Clunky alert-box feel | Subtle top border; surface color contrast; full border with hover accent. |
| 12 | Components | **Rounded-Everything**: `border-radius: 1rem+` on all elements | Childish, bubbly aesthetic | Mix sharp and subtle (4–6px); sharp cards with rounded buttons; editorial corners. |
| 13 | Components | **Pill-Shaped Buttons**: `rounded-full` (`9999px`) on all buttons | Cliché mobile-app feel | Subtle rounding (`rounded-md` / 6px); ghost buttons for secondary actions. |
| 14 | Layout | **Perfect Centering**: Centered heading, centered text, centered CTA | Weak visual flow, lazy balance | Left-aligned flow; asymmetric 60/40 grid; alternating visual anchors. |
| 15 | Layout | **Zebra Stripe Alternation**: Dark hero → white section → gray section | Jarring visual whiplash | Unified canvas tone with whitespace separation; single accent breakout section. |
| 16 | Layout | **Bento Box Grids**: Arbitrary mismatched card boxes everywhere | Visual chaos, novelty fatigue | Uniform grid with content hierarchy; horizontal scroll row; hero + supporting list. |
| 17 | Layout | **Mega Footers**: 5-column links on small utility sites | Premature corporate bloat | Minimal single-row footer or clean 2-column layout with essential links only. |
| 18 | Layout | **Sticky Mobile CTAs**: Full-width bar fixed to bottom of screen | Obscures mobile viewport | Scroll-triggered CTA; subtle floating action button; dismissible banner. |
| 19 | Interactive | **Universal Hover Scale**: `transform: scale(1.05)` on everything | Jittery, nauseating UI | Subtle vertical lift (`translateY(-2px)`); smooth border/shadow color transition. |
| 20 | Interactive | **Generic Icon Grids**: Outline check/shield/globe in 3×2 grid | Generic clip-art feel | Annotated product screenshots; numbered sequence; typography without icons. |
| 21 | Icons | **Emojis as UI Icons**: Unicode emojis (🚀, 💡, ⚡) in cards/buttons | OS fragmentation, no CSS styling | Cohesive SVG vector pack (**Lucide**, **Heroicons**, **Phosphor**) via `currentColor`. |
| 22 | Dev UI | **"Hollywood Hacker"**: Neon green on pitch black `#000000` | Severe eye strain, parody feel | Layered slate/zinc surfaces (`#090d16`, `#0f172a`); Sans-Serif UI fonts (Inter, Geist). |
| 23 | Dev UI | **Telemetry Dump**: Fake latency counters, engine tags, raw UUIDs | Obscures core value proposition | Aggressive whitespace (`p-6`, `gap-6`+); progressive disclosure via drawers/tooltips. |
| 24 | Dev UI | **Kitchen Sink Layout**: Search, tags, sidebars, widgets all-in-one | Fragmented attention, no journey | Purpose-driven focus: center primary task; eliminate gratuitous sidebars. |
| 25 | Copy | **Buzzword Salad & Fake Data**: Pseudo-academic titles & generic users | Signals fake AI prototype | Direct human-outcome copy ("Fast AST Code Search"); domain-authentic datasets. |

---

## Pre-Flight Self-Check Audit

Verify these 16 checkpoints before finalizing any design:

| # | Checkpoint | Failure Trigger | Corrective Action |
|---|------------|-----------------|-------------------|
| 1 | **Accent Borders** | More than 1 card with colored left accent border | Remove extra accent borders; use surface depth or subtle top border. |
| 2 | **Gradient Elements** | More than 2 gradient text or background elements | Switch to solid high-contrast colors or deep slate surfaces. |
| 3 | **Column Grids** | Multiple identical 3-column feature card rows | Vary layout rhythm with 60/40 splits, horizontal rows, or alternating sides. |
| 4 | **Alignment Audit** | Every section and heading centered | Left-align body copy and feature sections for natural reading flow. |
| 5 | **Shadow Inventory** | Heavy, blurry drop-shadows on 3+ elements | Reduce to subtle `0 1px 3px rgba(0,0,0,0.08)` or clean 1px border. |
| 6 | **Background Rhythm** | Alternating harsh white/gray zebra striping every section | Unify background tone; separate sections with generous whitespace. |
| 7 | **Icon Genericness** | Generic check/shield/globe outline icons in 3×2 grid | Replace with real UI screenshots, numbered steps, or bold typography. |
| 8 | **Hover Scale** | Cards, buttons, and badges all scale on hover | Restrict hover lift to primary interactive cards (`translateY(-2px)`). |
| 9 | **Color Palette** | All-pastel or low-contrast combinations | Ensure WCAG AA contrast (>= 4.5:1); check `design-preferences.md`. |
| 10 | **Border Radius** | All elements max-rounded (`rounded-full` / `1rem+`) | Mix sharp and subtle radii (4–6px); reserve pills for badges. |
| 11 | **Emoji Scan** | Unicode emojis in UI buttons, badges, cards, or nav | Replace with Lucide, Heroicons, or Phosphor SVG vector icons. |
| 12 | **Monospace Audit** | Monospace font used for headings or body copy | Switch to Sans-Serif (Inter, Geist); reserve monospace for code/hashes. |
| 13 | **Surface Contrast** | Pure `#000000` pitch black with neon phosphor glows | Use layered slate/zinc dark surfaces (`#090d16`, `#0f172a`) with subtle borders. |
| 14 | **Telemetry Clutter** | Fake ping latency, engine protocol tags, or raw UUIDs | Eliminate decorative counters; collapse technical details into drawers. |
| 15 | **Component Density** | 3+ competing sidebars/widgets on one screen | Remove kitchen-sink elements; center the primary user workflow. |
| 16 | **Copy & Data Realism**| Buzzword salad titles or default AI names (Alex Chen) | Write direct outcome-based copy and use authentic domain datasets. |
