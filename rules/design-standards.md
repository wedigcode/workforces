---
trigger: always_on
---

# UI & Website Design Standards

These visual and UI/UX design rules govern all website, web application, landing page, and component design and implementation across workforce workflows.

---

## 1. Absolute Prohibition: No Emojis as UI Icons or Design Elements
- **Strict Rule**: Under NO circumstances should raw unicode emojis (e.g. 🚀, 🔥, ⚡, 💡, 🛠️, 📈, 🎨, 💻, 🎯, 🔒, ✨, 📱) be used as UI icons, button graphics, feature card icons, navigation symbols, or decorative visual elements in websites and web applications.
- **Rationale**:
  1. **Platform Fragmentation**: Emojis render radically differently across operating systems (Apple, Windows, Android, Linux), destroying visual consistency.
  2. **Palette & Theming Disconnect**: Emojis contain fixed multi-color pixels that cannot inherit CSS design tokens, `currentColor`, hover states, or dark/light theme variables.
  3. **Visual Quality & Brand Signal**: Emoji icons convey an amateurish, unpolished, AI-generated prototype feel rather than a bespoke, professional web product.
  4. **Accessibility (a11y)**: Screen readers announce emoji unicode descriptions aloud (e.g., "Rocket glowing star high voltage"), creating a confusing screen-reader experience when used as interface icons.

---

## 2. Mandatory Vector Icon Packs
- **Strict Requirement**: All UI iconography must use cohesive, scalable, professional SVG vector icon packs.
- **Recommended Icon Packs**:
  - **Lucide Icons** (`lucide-react`, `lucide-vue-next`, `lucide-svelte`, `lucide-solid`, or inline SVG) — *Default / Primary recommendation*
  - **Heroicons** (`@heroicons/react`, `@heroicons/vue`, or inline SVG)
  - **Phosphor Icons** (`@phosphor-icons/react`, etc.)
  - **Tabler Icons** (`@tabler/icons-react`, etc.)
  - **Radix UI Icons** / **Feather Icons**
  - **Custom Handcrafted SVGs**: Clean SVG markup with unified `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, and consistent `stroke-width` (typically `1.5px` or `2px`).

---

## 3. Cohesive Icon Styling & Sizing Standards
- **Single Icon Family**: Do NOT mix multiple icon packs on the same project (e.g., mixing Material filled icons with Lucide linear icons). Use a single icon family and consistent style (line/outline vs. solid).
- **Size Scale Consistency**:
  - **Inline / Button Icons**: 16px × 16px (`size={16}` / `w-4 h-4`)
  - **Navigation / Menu Icons**: 18px–20px (`size={18}` / `size={20}`)
  - **Card / List Item Icons**: 20px–24px (`size={20}` / `size={24}`)
  - **Hero / Highlight Feature Icons**: 32px–48px (`size={32}` / `size={48}`)
- **Token Color Inheritance**: All vector icons MUST use `currentColor` or design system color tokens (`text-primary`, `text-muted`, `var(--color-primary)`) to ensure dynamic theme switching and hover state compatibility.

---

## 4. Mandatory Refero-Grade Design Benchmarking & Anti-AI Aesthetics
- **Strict Requirement**: All site and application designs MUST benchmark against curated, real-world, high-craft design systems (such as those cataloged on **Refero Styles**: [styles.refero.design](https://styles.refero.design/), **Land-book**, and **SiteInspire**).
- **Prohibition of Generic AI Design Clichés**:
  - **No Centered 3-Card Columns**: Never default to three identical feature cards in a row with centered icons in little colored circles.
  - **No Heading Gradient Text**: Avoid generic diagonal blue-to-purple gradient text headings (`background-clip: text`).
  - **No Flat Un-layered Boxes**: Avoid flat grey boxes on harsh backgrounds. Use rich, layered surface hierarchy (`bg-background`, `bg-surface`, `bg-card`, `border-border/40`).
- **Human-Craft Design Standards**:
  - **Distinct Typography Pairings**: Pair a character-rich Display font (e.g. Instrument Serif, Cal Sans, Syne, Cabinet Grotesk, Plus Jakarta Sans, Outfit, General Sans, Fraunces) with a clean UI body font (Inter, Geist, Plus Jakarta Sans, system-ui).
  - **Intentional Asymmetry & Rhythm**: Break layout monotony with 60/40 splits, staggered feature rows, hero product previews, and alternating visual anchors.
  - **Refined Color Palette Tokens**: Define an intentional 60-30-10 palette with surface contrast (e.g. warm parchment, midnight deep slate, alpine off-white, editorial darkroom).

---

## 5. Anti-Data Dump & Progressive Information Hierarchy
- **Strict Rule**: Do NOT cram every available metadata point, backend telemetry counter, and debug attribute onto primary screens.
- **Constraints**:
  - **No Decorative Telemetry**: Eliminate fake or non-actionable decorative data from headers and main feeds (e.g. "0.04s latency", "ENGINE PROTOCOL: AMPLIFY_GEN2", raw UUIDs, cold-start metrics) unless the application is a dedicated low-level infrastructure dashboard.
  - **Aggressive Whitespace**: Give cards, sections, and containers generous padding (`p-6`, `gap-6` or `gap-8`). Space signals quality.
  - **Progressive Disclosure**: Primary views should display only the title, clean human description, author/date, and primary action. Secondary technical details (git branch, commit diff, source hash, tags) should be collapsed into subtle secondary rows, tooltips, or expandable drawers.

---

## 6. Component Restraint (Anti-Kitchen Sink Layouts)
- **Strict Rule**: Avoid dumping every UI component in existence onto a single screen to prove feature completeness.
- **Constraints**:
  - **Purpose-Driven Components**: Only include search bars (Cmd+K), multi-tier filter dropdowns, trending sidebars, and terminal command snippets when specifically required by user workflows.
  - **Focused Page Journeys**: Keep the primary content feed or core task center-stage. Avoid surrounding the primary feed with 3–4 competing widget boxes (Leaderboards, Trending Stacks, Protocol links, Quick Deploy cards) on a single viewport.

---

## 7. Pragmatic Copywriting & Realistic Domain Data
- **Strict Rule**: Reject pseudo-academic, hyper-inflated AI buzzword titles and generic LLM placeholder datasets.
- **Constraints**:
  - **No "Buzzword Salad"**: Write clear, direct, human-friendly feature names and descriptions focused on user outcomes (e.g. "Fast AST Codebase Search" instead of "Autonomous Code-Graph Symbol Indexer & Analyzer").
  - **Realistic Domain Context**: Avoid default AI placeholder datasets (e.g., standard Alex Chen / Sophia Vance combinations paired with generic stock photos) when domain-tailored sample data communicates real product value.

---

## 8. Mandatory Visible Designer Agent Handoff & `DESIGN.md` Specification
- **Strict Rule**: When designing or scaffolding any new web property, the Designer Agent (`@designer`) must explicitly lead Step 2 of `/site-setup` and generate a concrete `DESIGN.md` specification (and `src/styles/tokens.css`).
- **Required `DESIGN.md` Content**:
  1. **Refero Style Archetype**: Named aesthetic benchmark from [styles.refero.design](https://styles.refero.design/).
  2. **Typography System**: Display font + Body font with Google Fonts / Fontshare import links, weight scale, and line-heights.
  3. **Color System Tokens**: Primary, Secondary, Background, Surface, Card, Border, Muted, and Accent hex values.
  4. **Layout & Component Rules**: Corner radius scale, button variants, card styling, and asymmetric section blueprints.
- **Engineering Directive**: Developers and coding agents MUST build strictly against `DESIGN.md` rather than writing ad-hoc styles or default AI templates.

---

## 9. Mandatory Design QA Review Gatekeeper
- **Strict Rule**: After the dev team completes frontend UI components or pages, `@designer` must perform an explicit Design QA review.
- **QA Verification**: Check the implementation against [`design-anti-patterns`](../skills/design-anti-patterns/SKILL.md) (verifying 0 emojis in UI, proper font pairings, layered surface depth, and layout asymmetry) before declaring the build task complete.
