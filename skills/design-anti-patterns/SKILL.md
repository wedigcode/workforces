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

Verify these 16 checkpoints before handing off any UI implementation:

| # | Checkpoint | Failure Trigger | Corrective Action |
|---|------------|-----------------|-------------------|
| 1 | **Emoji Scan** | Unicode emojis in buttons, badges, cards | Replace with Lucide/Heroicons SVG vector icon. |
| 2 | **Icon Consistency** | Mixed icon families or missing `currentColor` | Standardize on one icon family; use `stroke="currentColor"`. |
| 3 | **Typography Pairing** | Generic font or monospace used for UI body | Display font + clean Sans-Serif body (Inter, Geist, Plus Jakarta). |
| 4 | **Heading Gradients** | Multi-color gradient text on headings | Replace with high-contrast solid color or single accent word. |
| 5 | **Surface Depth** | Flat un-layered boxes or pitch-black background | Use layered surfaces (`bg-background`, `bg-surface`, `border-border/40`). |
| 6 | **Color Contrast** | Low contrast or user-rejected combinations | Enforce WCAG AA (>= 4.5:1); check `workforces/memory/design-preferences.md`. |
| 7 | **Layout Rhythm** | Three identical cards in a centered row | Break symmetry with 60/40 split or horizontal list. |
| 8 | **Whitespace Scale** | Cramped sections or padding < 16px | Expand to generous padding (`p-6`, `gap-6` or `gap-8`). |
| 9 | **Telemetry Clutter** | Decorative latency, protocol tags, raw UUIDs | Remove fake data; move secondary metrics to expandable drawers. |
| 10 | **Widget Density** | 3+ competing sidebars/widgets on one screen | Remove kitchen-sink elements; focus on primary user journey. |
| 11 | **Border Radius** | Everything set to `rounded-full` or `1rem+` | Use subtle 4–6px radii for cards/inputs; reserve pills for badges. |
| 12 | **Shadow Budget** | Heavy dark shadows across all cards | Tighten to subtle `0 1px 3px rgba(0,0,0,0.08)` or 1px border. |
| 13 | **Hover Restraint** | Everything scales or bounces on hover | Restrict hover lift to primary interactive cards (`translateY(-2px)`). |
| 14 | **Tagline Clarity** | Vague "Simple. Powerful." taglines | Rewrite to state concrete user outcome and causal trigger. |
| 15 | **Touch Targets** | Mobile tap targets smaller than 44×44px | Expand touch target sizing and spacing on mobile breakpoints. |
| 16 | **Design Memory** | Uses pattern rejected in `design-preferences.md` | Audit against recorded user anti-preferences; replace immediately. |
