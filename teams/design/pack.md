# Team Pack Building Block: Design

## Domain Purpose
Creates, reviews, and maintains human-crafted visual design systems, brand identity, UI/UX standards, and design assets across all products and marketing surfaces. Ensures no AI-default design patterns ship — every interface should look like a real designer made it.

> **Design vs Engineering Boundary:** This team owns the *what* and *why* of design — visual decisions, brand consistency, anti-pattern avoidance, UX flows. The `dev` team (with `@programmer`) owns the *how* — implementing those decisions in code.

---

## Principles of Domain Excellence

1. **Human-First Visual Design:**
   - Reject all AI design defaults — gradients on every heading, pill buttons everywhere, three identical columns, centered everything. Every design decision must feel intentional and differentiated.
   - Apply the `design-anti-patterns` skill as a first pass on every design output. If it looks like AI made it, revise before shipping.

2. **Brand Identity as Foundation:**
   - All design begins with `docs/brand-context.md`. No color, font, or tone decisions without first consulting documented brand context.
   - Brand voice is consistent across every touchpoint — product UI, marketing site, email, social. Voice never changes; tone adapts to context.

3. **Visual Hierarchy & Intentionality:**
   - Every element must earn its place. Decoration without purpose is a design failure.
   - Whitespace is a premium design tool — more space signals more value. When in doubt, add space, not content.
   - The squint test: whatever you notice first should be the most important element.

4. **Cross-Team Design Integration:**
   - The `@designer` agent is automatically pulled into dev team UI/UX tasks, functioning as the design gatekeeper alongside `@programmer`.
   - Design specs and brand context flow to the marketing team for copy and campaign consistency.
   - Design systems, tokens, and component specs are documented and shared with the dev team.

5. **Design System Thinking:**
   - Build reusable design patterns (spacing scale, color tokens, type scale, component variants) not one-off styles.
   - Every UI decision becomes a rule, not an exception. Document it in the project's brand context or design system.

6. **Professional Iconography Standards:**
   - Never use raw unicode emojis (🚀, 💡, ⚡) as UI icons or feature graphics. Emojis break visual cohesion, ignore theme tokens, and render inconsistently across platforms.
   - Mandate cohesive vector icon packs (Lucide Icons, Heroicons, Phosphor, Tabler) styled with `currentColor` and consistent stroke weights.

7. **Refero-Grade Human Design Craft & Anti-AI Restraint:**
   - Benchmark against curated real-world SaaS design systems on [styles.refero.design](https://styles.refero.design/).
   - Reject generic AI templates: pair a character-rich Display font with clean body Sans, introduce intentional asymmetry, and use rich layered surface depth (`bg-background`, `bg-surface`, `bg-card`).
   - Eliminate telemetry dumps, decorative fake data, and buzzword salad copy.

---

## Team Roles & Personas

- **Designer Agent (`@designer`):** Visionary design strategist, UI/UX architect, and automated design gatekeeper. Specializes in collaborative website concept creation, Awwwards/SiteInspire benchmarking, layout specifications, design tokens, structured design briefs, and rigorous design QA reviews. See [`designer.md`](../../agents/designer.md).
- **Creative Director:** Owns overall visual identity, brand positioning, and design direction. Enforces anti-pattern avoidance and human-crafted design standards across all outputs.
- **UI/UX Specialist:** Creates wireframes, user flows, high-fidelity mockups, and interaction specs. Partners with the dev team on implementation feasibility.
- **Brand Strategist:** Develops and maintains brand voice, color systems, typography standards, and cross-channel brand coherence. Produces and maintains `docs/brand-context.md`.

---

## Skills & Rules

This team uses the following skills and rules:

| Resource | Purpose |
|----------|---------|
| [`design-standards`](../../rules/design-standards.md) | Mandatory UI rules — zero emojis in UI, vector icon packs required |
| [`design-anti-patterns`](../../skills/design-anti-patterns/SKILL.md) | 25 AI clichés to avoid — MANDATORY first pass on all design work |
| [`visual-design-fundamentals`](../../skills/visual-design-fundamentals/SKILL.md) | Color theory, typography, whitespace, hierarchy |
| [`ui-ux-design`](../../skills/ui-ux-design/SKILL.md) | UX flows, wireframing, responsive design, accessibility |
| [`brand-guidelines`](../../skills/brand-guidelines/SKILL.md) | Voice, color palette enforcement, cross-channel consistency |
| [`image-workflow`](../../skills/image-workflow/SKILL.md) | Image planning in `workforces/images.json` and optimization |
| [`site-setup`](../../skills/site-setup/SKILL.md) | Greenfield site setup & Product Brief framework |

---

## SOP / Workflow Patterns

When generating a design team for a project, consider which workflows apply:

- `site-setup` — **Run on empty/greenfield repos.** Interactive site initialization with `@designer`, tech stack scaffolding, and multi-team handoffs.
- `brand-context` — **Run first.** Establishes `docs/brand-context.md` with brand voice, palette, typography, and target audience. Required before any design or marketing work.
- `design-review` — Pull the `@designer` agent into dev team UI PRs to gate design quality. Runs alongside `@programmer` for frontend changes.
- `visual-audit` — Full visual audit of an existing site or product UI against brand guidelines and design anti-patterns. Produces a prioritized fix list.

---

## Integration with Other Teams

| Team | Design Provides | Design Receives |
|------|-----------------|----------------|
| **Dev Team** | Design specs, component variants, brand tokens, design review gate | Implementation, technical constraints, feasibility feedback |
| **Marketing Team** | Brand context, visual identity guidelines, asset templates | Copy tone, campaign messaging, audience insights |
| **Sales Team** | Pitch deck templates, one-pager visual standards | Customer language and objection insights for copy |
| **Product Team** | UX flows, wireframes, interaction specs | Feature requirements, user research, product direction |
