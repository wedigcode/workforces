---
name: ui-ux-design
description: Guides user interface and user experience design, wireframing, interaction flows, responsive layout architecture, and WCAG accessibility standards. Reach for this skill when designing web or mobile application interfaces, mapping user onboarding journeys, diagnosing usability friction and navigation drop-off, establishing responsive breakpoints, or auditing design systems for accessibility and interaction clarity.
---
# UI/UX Design

Design interfaces that are intuitive, accessible, and conversion-optimized. Understand how users think, flow through pages, and make decisions — then design for that reality.

## When to Use

- Designing a website, landing page, or app interface
- Creating wireframes or user flow diagrams
- Reviewing a page for usability problems
- Ensuring responsive design across devices
- Auditing accessibility compliance

---

## Core Principles

### 1. User Experience Foundations

**Heuristic Checklist (adapted from Nielsen):**

| Heuristic | What it Means | Example |
|-----------|---------------|---------|
| **Visibility** | Users always know where they are and what's happening | Active nav state, progress bars, loading indicators |
| **Match real world** | Use words and concepts users already know | "Shopping cart" not "order aggregation module" |
| **User control** | Easy to undo, go back, and exit | Back buttons, cancel options, undo actions |
| **Consistency** | Same action = same result everywhere | All CTAs look the same, navigation stays put |
| **Error prevention** | Design to prevent mistakes before they happen | Disable submit until form is valid, confirm before delete |
| **Recognition > recall** | Show options, don't make users remember | Dropdown menus, auto-suggestions, visible labels |
| **Flexibility** | Support both novice and expert users | Shortcuts for power users, onboarding for new ones |
| **Minimal design** | Every element must earn its place | Remove decorative noise, focus on the task |

### 2. User Flow Design

**Map the happy path first:**
```
Entry point → Key action → Confirmation → Next step
```

| Flow Type | Pattern | Example |
|-----------|---------|---------|
| **Linear** | Step 1 → Step 2 → Step 3 → Done | Checkout flow, onboarding wizard |
| **Hub & Spoke** | Central hub → Branch out → Return | Dashboard → Settings → Back to dashboard |
| **Funnel** | Wide → Narrow → Convert | Landing page → Pricing → Checkout |
| **Loop** | Discover → Use → Share → Return | Social media feed, content platform |

**Design for drop-off:** At every step, ask "Why would someone leave here?" and design against it.

### 3. Wireframing

**Low-fidelity wireframe rules:**
- Boxes for images, lines for text, rectangles for buttons
- No colors, no fonts — structure only
- Label every section with its purpose (Hero, Social Proof, CTA)
- Mobile first, then expand to desktop

**Wireframe to production flow:**
```
Sketch (paper) → Low-fi wireframe → High-fi mockup → Prototype → Build
```

### 4. Responsive Design

| Breakpoint | Target | Layout Strategy |
|------------|--------|-----------------|
| **320–480px** | Mobile phones | Single column, stacked sections, hamburger nav |
| **481–768px** | Tablets | 2-column where appropriate, collapsible sidebar |
| **769–1024px** | Small laptops | Full navigation, side-by-side layouts |
| **1025px+** | Desktops | Max-width container (1200–1440px), multi-column |

**Mobile-first rules:**
- Design for the smallest screen first, enhance upward
- Touch targets: minimum 44×44px
- Thumb zone: critical actions in bottom half of screen
- No hover-dependent interactions on mobile

### 5. Interaction Design

| Pattern | Use | Example |
|---------|-----|---------|
| **Micro-animations** | Feedback + delight | Button press effect, form success check |
| **Progressive disclosure** | Reduce cognitive load | "Show more" links, accordion sections |
| **Skeleton screens** | Perceived speed | Gray placeholder blocks while content loads |
| **Toast notifications** | Non-blocking feedback | "Saved successfully" fading in/out |
| **Modal dialogs** | Focused decisions | Confirm delete, payment confirmation |

**Rule:** Every interaction should have visible feedback within 100ms.

### 6. Accessibility (a11y)

| Requirement | How |
|-------------|-----|
| Keyboard navigation | All interactive elements focusable, visible focus ring |
| Color contrast | 4.5:1 for normal text, 3:1 for large text (WCAG AA) |
| Alt text | Every `<img>` has descriptive alt (or `alt=""` for decorative) |
| Form labels | Every input has an associated `<label>` |
| Heading structure | Logical h1 → h2 → h3, one h1 per page |
| ARIA | Only when native HTML semantics don't cover it |
| Reduced motion | Respect `prefers-reduced-motion` media query |
| Screen reader testing | Test with VoiceOver (Mac) or NVDA (Windows) |

### 7. Iconography Standards

| Rule | Requirement |
|------|-------------|
| **No Emojis** | NEVER use raw unicode emojis (🚀, 💡, ⚡, 🔥, 🛠️) as UI icons, button graphics, or feature symbols. |
| **Vector Icon Packs** | Use a single, cohesive SVG icon pack: **Lucide**, **Heroicons**, **Phosphor**, or **Tabler**. |
| **Sizing Scale** | Inline/buttons: 16px; Menus/nav: 18–20px; Feature cards: 20–24px; Hero highlights: 32–48px. |
| **Token Styling** | Style with `currentColor` to inherit CSS tokens, themes, and hover states cleanly. |

---

## UI Checklist

| Check | Description |
|-------|-------------|
| ✅ Clear user flow | User can complete primary task in < 3 clicks |
| ✅ Mobile-friendly | Works on 320px width without horizontal scroll |
| ✅ Touch targets | All tappable elements ≥ 44×44px |
| ✅ Loading states | Skeleton screens or spinners for async content |
| ✅ Error states | Clear error messages with recovery actions |
| ✅ Empty states | Helpful messaging when lists/data are empty |
| ✅ Accessible | Keyboard nav, contrast, alt text, labels |
| ✅ Consistent patterns | Same component looks and behaves the same everywhere |
| ✅ Professional Icons | Cohesive vector icon pack used — zero unicode emojis in UI |
| ✅ Typography Hierarchy | Clean Sans-Serif for body/UI — monospace strictly for code/hashes |
| ✅ Generous Whitespace | Generous padding (`p-6`, `gap-6`+), avoiding cramped data dumps |
| ✅ Purposeful Layout | No decorative fake telemetry (e.g. latency/protocol) or kitchen-sink widgets |

---

## Anti-Patterns

| Pattern | Problem | Instead |
|---------|---------|---------|
| Mystery navigation | Users can't find what they need | Clear labels, visible nav |
| Infinite scroll without anchors | Users lose position, can't bookmark | Pagination or "load more" |
| Auto-play video with sound | Immediate bounce | Muted autoplay or click-to-play |
| Form without validation feedback | Users submit bad data | Inline validation, clear error messages |
| Hover-only interactions on mobile | Mobile users can't trigger them | Use taps, long-press, or visible toggles |
| Modal on page load | Feels aggressive, high bounce rate | Trigger modals on intent (scroll, exit, time delay) |
| Using emojis as UI icons | Inconsistent OS rendering, non-themeable, amateur look | Cohesive vector icon pack (Lucide, Heroicons, Phosphor) |
| "Hollywood Hacker" aesthetic | Monospace body copy, neon glows on pure black cause eye strain | Sans-Serif typography, layered slate/zinc dark surfaces |
| Metadata / Telemetry dump | Cramming ping latency, protocols, and hashes everywhere destroys hierarchy | Progressive disclosure: clean cards with collapsible details |
| Component kitchen sink | Jamming search, tags, sidebars, leaderboards into one screen | Focused, purpose-driven layout centered on the primary task |
| "Buzzword salad" copywriting | AI-generated technical jargon obscures product utility | Plain-English, outcome-focused titles and descriptions |
