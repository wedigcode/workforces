---
name: brand-guidelines
description: Defines, audits, and enforces brand voice, typography, color palettes, logo usage, and cross-channel consistency. Reach for this skill when bootstrapping brand standards for a new project (`docs/brand-context.md`), auditing marketing copy or UI designs for voice drift and off-brand visual elements, reviewing design tokens against brand rules, or onboarding designers and copywriters to ensure consistent identity.
---

# Brand Guidelines & Brand Context Pipeline

Enforces brand consistency across all touchpoints. Led by `@marketer` and `@designer`.

---

## 1. Voice & Tone Standards

- **Voice (Fixed)**: WHO the brand is. Remains identical across all platforms and communications.
- **Tone (Adaptive)**: HOW the brand speaks given situational context (empathetic in support, celebratory in launches).

| Dimension | Spectrum | Production Standard |
| :--- | :--- | :--- |
| **Formality** | Corporate ↔ Casual | Peer-to-peer; articulate, direct, zero corporate buzzwords. |
| **Attitude** | Serious ↔ Playful | Helpful, candid, lightly irreverent where appropriate. |
| **Perspective** | Academic ↔ Practitioner | Practitioner who has built and tested in production. |

---

## 2. Color System Tokens

> [!IMPORTANT]
> Always verify all color token choices against `workforces/memory/design-preferences.md` before generating palettes.

| Role | Token Usage | Rule |
| :--- | :--- | :--- |
| **Primary** | Core brand identity, key CTAs | Exact hex match across all assets. |
| **Secondary** | Structural cards, secondary buttons | Differentiates surfaces from background. |
| **Neutral** | Background canvas, body text, borders | Minimum **4.5:1** contrast ratio (WCAG AA). |
| **Accent** | Alerts, high-intent badges (<= 10% area)| Highlight action items (snaps to accent token). |
| **Feedback** | Success (green), warning (amber), error (red) | Accessible semantic status indicators. |

---

## 3. Typography & Logo Rules

- **Font Families**: Strictly **<= 2 font families** (1 character Display font + 1 clean UI Sans-Serif).
- **Type Scale**: Defined modular scale (`14px`, `16px`, `20px`, `24px`, `32px`, `48px`); line-height `1.5×` body, `1.2×` headings.
- **Logo Clearance**: Minimum clear space surrounding logo equals full logo height; SVG for web, PNG for social.

---

## 4. Pre-Flight Brand Audit Checklist

- [ ] **Voice Uniformity**: Tone adapts, but voice personality remains consistent across copy.
- [ ] **Hex Code Accuracy**: Palette uses exact design system tokens (no off-brand hex approximations).
- [ ] **Contrast Compliance**: Zero low-contrast text (e.g. yellow text over white is strictly banned).
- [ ] **Font Discipline**: Exactly <= 2 font families across all public surfaces.
- [ ] **Documentation**: Defined in `docs/brand-context.md` and adhered to by all subagents.
