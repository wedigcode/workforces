---
name: design-anti-patterns
description: Identifies and replaces 25 ubiquitous AI design clichés (such as floating glow cards, generic purple-blue gradients, hollow metrics, and centered hero clichés) with human-crafted, production-grade alternatives anchored in benchmark systems like Refero, Linear, and Huly. Reach for this skill when designing or reviewing web interfaces, landing pages, and component styling to ensure layouts look intentional, authentic, and professionally crafted.
---
# Design Anti-Patterns

AI tools default to the same visual patterns. This skill identifies 25 overused AI design clichés and provides unique, human-crafted alternatives. The goal: designs that look **intentional and differentiated**, not templated.

> **Core Principle:** These aren't forbidden patterns — they're overused ones. Use them sparingly and intentionally, not by default.

---

## 💎 Refero Design Benchmark Anchor: Look at Real Products, Not AI Presets

Before designing or building, browse **[styles.refero.design](https://styles.refero.design/)** for real-world design systems (Huly, Mercury, Origin, Function Health, Monad, Cosmos, Mintlify, Dub). Study their typography pairings, asymmetric grids, layered surfaces, and micro-borders. Ground your designs in real human craft rather than AI memory defaults.

---

## When to Use

- Building any UI, landing page, or web page
- Reviewing AI-generated designs before shipping
- Self-checking output for "looks AI-generated" signals
- When the dev team's UI needs a design pass before delivery
- Creating component libraries or design systems

---

## Priority 1: Typography & Text

### 1. Gradient Text on Every Heading

**The cliché:** Heading with a blue-to-purple gradient applied as a `background-clip: text` effect on every hero.

```css
/* ❌ What AI defaults to */
.hero h1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; }
```

**Alternatives:**
- Solid color with high contrast (bold black on white, white on dark)
- Single accent color on ONE word only — the rest is solid
- Oversized display font in a muted tone with heavy weight
- Color contrast through background, not text gradient

### 2. Every Feature Has a Bullet-Point Description

**The cliché:** Every feature section uses a bulleted list with 3–4 generic benefit bullets.

**Alternatives:**
- One strong sentence per feature — no bullets
- A bold statistic followed by context (e.g. "3× faster — measured on production data")
- Pull-quote style: large quote from a user, no bullet at all
- Numbered steps for sequential benefits

### 3. "Simple. Powerful. Flexible." Taglines

**The cliché:** Three-word hero taglines that describe nothing specific.

**Alternatives:**
- Specific outcomes: "Invoices paid in 48 hours — not 30 days"
- Customer language: Use the exact words your target audience uses to describe the problem
- Comparative: "Replaces your Slack + Notion + Jira — one tab"
- Bold one-word declaratives with visual emphasis

---

## Priority 2: Visual & Color

### 4. Purple-to-Blue Gradient Backgrounds

**The cliché:** Entire page hero section with a diagonal purple→blue gradient.

**Alternatives:**
- Deep solid color (near-black, dark navy, forest, charcoal)
- Muted earthy tone (warm sand, slate, olive)
- Off-white with a bold typographic treatment
- One-color background with subtle texture (noise, grain, minimal line pattern)

### 5. Glassmorphism Cards

**The cliché:** Cards with `backdrop-filter: blur()` and semi-transparent white backgrounds on everything.

**Alternatives:**
- Solid cards with subtle shadows
- Cards differentiated by background color, not transparency
- Outlined cards (border only, no fill)
- Elevated cards using only box-shadow

### 6. Heavy Box Shadows

**The cliché:** Large, dramatic shadows on every card and element.

```css
/* ❌ AVOID */
.card { box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
```

**Alternatives:**
- Subtle, tight shadows: `0 1px 3px rgba(0,0,0,0.1)`
- No shadow — use borders or background contrast instead
- One shadow level site-wide (consistent, not per-element)
- Bottom-border illusion: thicker bottom border instead of shadow

### 7. Decorative Blobs/Circles

**The cliché:** Random gradient blobs positioned absolute in the background.

**Alternatives:**
- No decorative shapes at all — let content and whitespace work
- Geometric patterns (diagonal lines, grids, dots) if texture is needed
- Photographic elements positioned for visual interest
- Subtle CSS patterns (stripes, checkerboard at low opacity)

---

## Priority 3: Components & Cards

### 8. Card-Based Everything (3-Column Grid)

**The cliché:** Three identical cards in a row for every feature section.

**Alternatives:**
- 2-column layout with one larger feature card
- Horizontal list with icons inline
- Single-column with large illustrations alternating sides
- Numbered list without cards at all
- 4-column grid with smaller, simpler items

### 9. Icon-Above-Heading Pattern

**The cliché:** Every feature card has an icon, then heading, then paragraph — identical layout.

**Alternatives:**
- Icon inline with heading (side by side, not stacked)
- No icons — use numbers, colored bullets, or nothing
- Large illustration spanning the full card instead of small icon
- Leading with a statistic or metric instead of an icon

### 10. Badge/Tag Overuse

**The cliché:** Small colored badges above every section heading ("NEW", "POPULAR", "BETA").

**Alternatives:**
- No badge — just a strong heading with good hierarchy
- A subtle label in smaller, muted text
- Timeline-style marker with a date
- Context communicated through the heading itself

### 11. Accent Left-Border on Cards

**The cliché:** Colored left border on cards or blockquotes.

```css
/* ❌ Common AI default */
.card { border-left: 4px solid #3b82f6; }
```

**Alternatives:**
- Top border instead of left
- Colored background strip at the top of the card
- No accent border at all — use background color or subtle shadow
- Full border with hover accent instead of always-on accent

### 12. Rounded-Everything

**The cliché:** Every element has `border-radius: 1rem` or more. Buttons, cards, images — all super rounded.

**Alternatives:**
- Mix sharp and rounded: sharp cards with rounded buttons, or vice versa
- Subtle rounding only: `4px` not `16px`
- Fully sharp corners for a more editorial, magazine feel
- Rounded only on interactive elements (buttons, inputs)

### 13. Pill-Shaped Buttons Everywhere

**The cliché:** Every button uses full-radius rounding.

```css
/* ❌ What AI defaults to */
.button { border-radius: 9999px; }
```

**Alternatives:**
- Subtle rounding: `border-radius: 6px`
- Square buttons with bold text
- Ghost buttons (border only, no fill) for secondary actions
- Underlined text links instead of buttons for tertiary actions

---

## Priority 4: Layout & Structure

### 14. Perfectly Centered Everything

**The cliché:** Every hero, every section: centered text, centered button, centered paragraph.

**Alternatives:**
- Left-aligned sections (natural reading flow)
- Off-center: 60/40 split instead of 50/50
- Mixed alignment: hero centered, features left-aligned, testimonials right
- Asymmetric grids: one column wider than the other

### 15. Dark Hero → White Content Alternation

**The cliché:** Dark hero section, then alternating white/gray sections down the page.

**Alternatives:**
- Single background color throughout with spacing separating sections
- Color accent on ONE section only (not alternating)
- Full background image with content overlaid for variety
- Break the rhythm: two white sections in a row, then one dark

### 16. "Bento Box" Grids

**The cliché:** Mismatched card sizes creating Mondrian-style layout (popularized by Apple, now everywhere).

**Alternatives:**
- Uniform grid with hierarchy through content/color, not size
- Horizontal scrolling row instead of complex grid
- Vertical stacked cards with consistent spacing
- One featured item + uniform grid of supporting items

### 17. Mega Footers (5-Column Overkill)

**The cliché:** Footer with 4–5 columns of links, social icons, newsletter, logo, legal — even on small sites.

**Alternatives:**
- Minimal: single row with essential links
- Two-column: logo/social left, grouped links right
- Contextual: footer content changes per page type
- Only create columns if you have actual distinct content categories

### 18. Sticky CTAs on Mobile

**The cliché:** Fixed CTA button covering the bottom of every mobile viewport.

**Alternatives:**
- Selective use: only on high-intent pages, not blog posts
- Dismissible: include close button
- Small floating action button in corner instead of full-width bar
- Scroll-triggered: appears only after user scrolls past main CTA

---

## Priority 5: Interactive & Hover

### 19. Hover Scale Transforms Everywhere

**The cliché:** Every card, button, and image gets `transform: scale(1.05)` on hover.

**Alternatives:**
- Selective scaling on primary interactive elements only
- Subtle vertical lift: `transform: translateY(-4px)` instead of scale
- Color/shadow transitions instead of size changes
- Content reveals: show additional info on hover instead of enlarging
- Simple: underline for links, shadow change for buttons

### 20. Feature Grid with Generic Icons

**The cliché:** 3×2 grid of features, each with a generic outline icon (check, shield, lightning bolt, globe).

**Alternatives:**
- Custom illustrations or hand-drawn doodles
- Descriptive headings that don't need icons
- Screenshots or real product images
- Numbered list with brief descriptions
- Single large image with annotation labels

### 21. Emojis as UI Icons or Feature Graphics

**The cliché:** Using raw unicode emojis (🚀, 💡, ⚡, 📈, 🔥, 🛠️, 🎯, 🔒) as icons on feature cards, buttons, navigation items, badges, or headers.

**Why it fails:**
- Inconsistent rendering across operating systems (Apple, Windows, Android, Linux)
- Fixed multi-color emoji pixels clash with custom brand color palettes
- Cannot style or transition with CSS `currentColor`, dark/light theme tokens, or stroke widths
- Screen readers announce literal unicode descriptions (e.g., "Rocket high voltage"), degrading accessibility
- Instantly signals an amateur, low-effort, AI-generated prototype

**Alternatives:**
- Cohesive SVG vector icon pack: **Lucide Icons** (`lucide-react`, `lucide-vue-next`, `lucide-svelte`), **Heroicons**, **Phosphor**, **Tabler**
- Minimalist custom inline SVGs with `stroke="currentColor"` and unified `viewBox="0 0 24 24"`
- Semantic step numbers (01, 02, 03) or bold typographic indicators
- Clean typography and whitespace with no decorative icons needed

---

## Priority 6: Developer Tools & SaaS Feeds

### 22. The "Hollywood Hacker" Developer Cliché

**The cliché:** Designing developer tools or SaaS feeds to look like a cyberpunk movie terminal with pure pitch-black (`#000000`) backgrounds, high-contrast neon green/cyan hairline borders, phosphor text glow shaders, and monospace fonts used for all headings, body copy, chips, and navigation.

**Why it fails:**
- Monospace body text creates severe reading fatigue and slows comprehension.
- High-contrast neon glows on pure black strain the eyes and look like an amateur movie prop or AI caricature rather than a modern, serious developer product.

**Alternatives:**
- Layered, sophisticated dark-mode surfaces such as slate or zinc (`#090d16`, `#0f172a`, `#18181b`, `#27272a`).
- High-readability Sans-Serif typography (Inter, Geist, Plus Jakarta Sans, Roboto, or `system-ui`) for all UI labels, headings, badges, and descriptions.
- Monospace font strictly reserved for actual code snippets, commit hashes, or terminal commands.
- Subtle 1px borders (`border-zinc-800` or `rgba(255, 255, 255, 0.08)`) with focused, purposeful accent colors.

### 23. The Metadata & Telemetry Dump (Lack of Hierarchy)

**The cliché:** Cramming every backend metric, protocol tag, latency counter, UUID, branch name, and commit hash into top-level headers and feed cards.

**Why it fails:**
- When everything is screaming for attention, nothing stands out.
- Decorative, non-actionable data (e.g., "0.04s latency", "ENGINE PROTOCOL: AMPLIFY_GEN2_REALTIME", raw hashes) clutters the UI and obscures the core value proposition.

**Alternatives:**
- Aggressive whitespace and generous padding (`p-6`, `gap-6` or `gap-8`). Space signals premium quality.
- Progressive disclosure: primary cards display clear title, human description, author, and primary action.
- Secondary technical metadata (commit hash, branch name, diff stats) collapsed into subtle secondary rows, tooltips, or expandable drawers.

### 24. The Component Kitchen Sink

**The cliché:** Jamming every possible UI component onto a single viewport (Cmd+K global search, multi-tier tag clouds, leaderboard widgets, trending stacks sidebars, protocol link cards, deploy CTAs, terminal snippets) just to show feature density.

**Why it fails:**
- Overwhelms users with competing focal points and visual noise.
- Fragmented page flow with no clear primary user journey.

**Alternatives:**
- Purpose-driven minimalism: keep the primary feed or workflow centered and uncluttered.
- Only include search, filters, or sidebars when directly required by actual user workflows.
- Dedicated secondary pages or modals rather than cramming 4 competing sidebars onto one screen.

### 25. "Buzzword Salad" Copywriting & Default AI Datasets

**The cliché:** Writing hyper-inflated, pseudo-academic titles (e.g. "Autonomous Code-Graph Symbol Indexer & Analyzer", "Neural Agent Memory Layer & Vector Cache") and using default AI placeholder datasets (Alex Chen, Marcus Brody, Sophia Vance with Unsplash URLs).

**Why it fails:**
- Instantly flags the site as an AI-generated prototype.
- Obscures the real utility of the product behind technical jargon.

**Alternatives:**
- Plain-English, outcome-focused copy (e.g., "Fast AST Codebase Search", "Multi-Agent Context Cache").
- Domain-realistic sample data tailored to the product's actual use cases.

---

## Self-Check Checklist

Before finalizing any design, verify:

| # | Check | Action if Triggered |
|---|-------|-------------------|
| 1 | Count accent borders | More than 1 on the page? Remove extras |
| 2 | Count gradient elements | More than 2? Switch to solid colors |
| 3 | Count 3-column grids | Multiple identical grids? Vary layout |
| 4 | Alignment audit | Everything centered? Add left-aligned sections |
| 5 | Shadow inventory | Heavy shadows on 3+ elements? Reduce |
| 6 | Background pattern | Alternating gray every section? Break rhythm |
| 7 | Icon check | Generic icons everywhere? Replace or remove |
| 8 | Hover audit | Everything scales on hover? Vary the effects |
| 9 | Color palette | All pastels? Add contrast |
| 10 | Border-radius | Everything max-rounded? Mix sharp and subtle |
| 11 | Emoji check | Unicode emojis used as UI icons? Replace with SVG icon pack (Lucide/Heroicons) |
| 12 | Monospace audit | Monospace used for body/headings? Switch to Sans-Serif (Inter/Geist) |
| 13 | Surface contrast | Pure `#000000` black or neon phosphor glows? Switch to slate/zinc surfaces with subtle borders |
| 14 | Telemetry clutter | Fake latency or protocol tags in header? Remove decorative metadata |
| 15 | Component density | 3+ competing sidebar/widget boxes on one screen? Remove kitchen-sink clutter |
| 16 | Copy realism | Buzzword salad titles or default AI names? Rewrite for human clarity |


---

## Industry Exceptions

Some industries embrace certain patterns:

| Industry | Acceptable | Still Avoid |
|----------|-----------|-------------|
| **SaaS/Tech** | Gradient backgrounds, glassmorphism (expected) | Still vary layout and avoid uniformity |
| **Creative/Agency** | Asymmetric layouts, bold typography | Avoid becoming chaotic |
| **Corporate/Legal** | Centered layouts, conservative colors | Avoid becoming boring |
| **E-commerce** | Card grids, uniform layouts | Vary hero treatments |

---

## The Core Principle

> The meta-pattern to avoid: **applying formulaic solutions to every element.**

Real, human-designed interfaces have rhythm, variation, and intentional pattern-breaking:

1. **Vary your approaches** — don't use the same pattern twice
2. **Question defaults** — if it feels like the obvious choice, it probably is for AI too
3. **Embrace asymmetry** — perfect balance is boring
4. **Use restraint** — one bold choice per section, not three
5. **Let content breathe** — whitespace beats decoration
6. **Be selective** — not every element needs a hover effect, shadow, or icon
