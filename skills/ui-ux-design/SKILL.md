---
name: ui-ux-design
description: Guides user interface and user experience design, wireframing, interaction flows, responsive layout architecture, and WCAG accessibility standards. Reach for this skill when designing web or mobile application interfaces, mapping user onboarding journeys, diagnosing usability friction and navigation drop-off, establishing responsive breakpoints, or auditing design systems for accessibility and interaction clarity.
---

# UI/UX Design Standards

Design interfaces that are intuitive, accessible, and conversion-optimized. For anti-pattern prevention, refer to [`design-anti-patterns`](../design-anti-patterns/SKILL.md).

---

## 1. Usability Heuristics & User Flows

| Heuristic | Core Requirement | Implementation Pattern |
|-----------|------------------|------------------------|
| **Visibility of Status** | Users always know current system state | Active navigation state, progress steps, skeleton loaders. |
| **Real-World Match** | Plain-English domain terms users already know | Familiar labels ("Cart" not "Order Aggregator"). |
| **User Control & Exit** | Easy to undo, cancel, or step backward | Prominent back buttons, modal dismissal, undo toasts. |
| **Consistency** | Identical actions produce identical outcomes | Unified button variants, predictable layout placement. |
| **Error Prevention** | Prevent invalid inputs before submission | Inline field validation, destructive action confirmations. |
| **Recognition > Recall** | Visible choices rather than memory load | Search autocomplete, visible option chips, clear icons. |
| **Progressive Disclosure** | Layer complexity from simple to detailed | Summary view with expandable detail drawers or tooltips. |

**User Flow Topologies:**
- **Linear**: Step 1 → Step 2 → Step 3 → Complete (Checkout, Onboarding).
- **Hub & Spoke**: Central dashboard → Detail view → Return to hub (Settings, File Manager).
- **Funnel**: Wide landing → Focused pricing → Conversion.

---

## 2. Responsive Breakpoints & Mobile-First Standards

| Breakpoint | Target Device | Layout Strategy |
|------------|---------------|-----------------|
| **320–480px** | Mobile phones | Single column, full-width cards, bottom thumb-zone CTAs. |
| **481–768px** | Tablets / Foldables | 2-column grid, collapsible secondary sidebar. |
| **769–1024px** | Laptops | Full horizontal navigation, 60/40 asymmetric content split. |
| **1025px+** | Desktop monitors | Max-width container (`max-w-7xl` / 1280–1440px), multi-column layout. |

- **Touch Targets**: Minimum **44×44px** tappable hit area for all buttons and interactive controls on mobile.
- **Thumb Zone**: Primary actions positioned within natural reach in the lower half of mobile screens.
- **Zero Hover Dependency**: Never hide critical actions or information behind hover states on touch viewports.

---

## 3. Interaction Design & Latency Budgets

- **Visual Feedback Budget**: Every user interaction (click, tap, toggle) MUST provide visible visual feedback within **< 100ms** (active state, spinner, ripple, or optimistic update).
- **Perceived Speed**: Use skeleton screens matching content geometry rather than generic center spinners for async data loading.
- **Destructive Confirmations**: High-risk actions (deletion, revocation) require an explicit confirmation modal or 5-second undo toast.

---

## 4. Accessibility (a11y) & WCAG AA Standards

| Category | Requirement | Verification Method |
|----------|-------------|---------------------|
| **Color Contrast** | Minimum **4.5:1** for body text, **3:1** for large headings | Audit against WCAG AA color tokens; zero yellow on white. |
| **Keyboard Navigation** | All interactive elements reachable via `Tab` | Visible `:focus-visible` focus ring on all interactive components. |
| **Form Labels** | Every form control has an associated `<label>` | Explicit `htmlFor` / `id` pairing, not bare placeholder text. |
| **Semantic Hierarchy** | Exactly one `<h1>` per page; sequential `<h2>` / `<h3>` | Screen-reader outline audit; no skipped heading levels. |
| **Motion Safety** | Respect OS reduced-motion preferences | Disable or shorten motion/transitions inside `@media (prefers-reduced-motion: reduce)`. |

---

## Pre-Handoff UI/UX Checklist

- [ ] **Flow Efficiency**: User can reach and complete the primary action in <= 3 clicks.
- [ ] **Responsive Integrity**: Tested at 320px, 768px, and 1280px without horizontal scrollbars.
- [ ] **Touch Targets**: All mobile buttons and links satisfy >= 44×44px hit boundaries.
- [ ] **Loading & Empty States**: Clean skeleton placeholder when loading; actionable guidance when data is empty.
- [ ] **Error Handling**: Clear, actionable error messages with recovery options on failed actions or invalid input.
- [ ] **Contrast Compliance**: Body text satisfies WCAG AA >= 4.5:1 contrast ratio.
- [ ] **Focus Rings**: All interactive controls display high-contrast focus rings on keyboard tab navigation.
