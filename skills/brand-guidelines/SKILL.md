---
name: brand-guidelines
description: Brand voice enforcement, color palette consistency, typography standards, logo usage rules, and cross-channel brand coherence. Use when creating or reviewing any branded output.
---

# Brand Guidelines

Protect and enforce brand consistency across every touchpoint. A strong brand means every piece of content — from an Instagram caption to a product UI screen — feels like it came from the same person.

## When to Use

- Reviewing any content or design for brand consistency
- Creating new assets that must match existing brand identity
- Defining brand standards for a new project
- After running `/brand-context` to capture project brand identity
- Auditing content across channels for drift

---

## Core Principles

### 1. Brand Voice

| Dimension | Spectrum | Where We Land |
|-----------|----------|---------------|
| **Formal ↔ Casual** | Corporate ↔ Texting a friend | Casual but not sloppy — like a smart friend giving advice |
| **Serious ↔ Playful** | All business ↔ All jokes | Primarily helpful with occasional humor |
| **Respectful ↔ Irreverent** | Diplomatic ↔ Provocative | Direct and honest, not rude |
| **Expert ↔ Peer** | Professor ↔ Study buddy | Peer who's a few steps ahead |

**Voice consistency rules:**
- Same vocabulary across all channels
- Same abbreviation style (don't use "DM" in one post and "direct message" in another)
- Same level of formality in emails as in captions
- Same emoji usage patterns (if any)

### 2. Tone vs Voice

| Concept | Definition | Example |
|---------|------------|---------|
| **Voice** | WHO you are (consistent) | Confident, direct, empathetic |
| **Tone** | HOW you say it (context-dependent) | Celebratory in a win post, empathetic in a struggle post |

Voice never changes. Tone adapts to the situation.

### 3. Color Palette

Define and enforce a strict color system:

| Role | Purpose | Usage |
|------|---------|-------|
| **Primary** | Main brand color | Logo, CTAs, key accents |
| **Secondary** | Supporting color | Backgrounds, secondary buttons |
| **Neutral** | Text, borders, backgrounds | Body copy, dividers, cards |
| **Accent** | Highlights, alerts | Sale badges, notifications |
| **Feedback** | Success/warning/error states | Form validation, status indicators |

**Rules:**
- Every color must have a hex code and defined usage
- No "similar" colors — exact hex match always
- Document both light and dark mode variants
- Test all colors for accessibility contrast (WCAG AA)

### 4. Typography

| Element | Standard |
|---------|----------|
| **Heading font** | Defined style (e.g., Bold, 600+ weight) |
| **Body font** | Defined style (e.g., Regular, 400 weight) |
| **Font pairing** | Max 2 families across all materials |
| **Sizes** | Define a type scale (e.g., 14, 16, 20, 24, 32, 48) |
| **Line height** | Body: 1.5×, Headings: 1.2× |

### 5. Logo Usage

| Rule | Guideline |
|------|-----------|
| **Clear space** | Minimum padding around logo = logo height |
| **Minimum size** | Define smallest acceptable rendering size |
| **Color variants** | Full color, monochrome, reversed (on dark bg) |
| **Don'ts** | No stretching, rotating, recoloring, or adding effects |
| **File formats** | SVG for web, PNG for social, PDF for print |

### 6. Cross-Channel Consistency

| Channel | Brand Check |
|---------|-------------|
| **Website** | Colors, fonts, imagery style, voice |
| **Instagram** | Feed aesthetic, caption voice, story templates |
| **Email** | Header design, button colors, sign-off voice |
| **Ads** | Creative style matches organic content feel |
| **Product UI** | Color tokens, component style, copy voice |

---

## Brand Audit Checklist

| Check | Description |
|-------|-------------|
| ✅ Voice consistent | Same personality across all content |
| ✅ Colors exact | Hex codes match, no approximations |
| ✅ Typography consistent | Same fonts, same sizes, same hierarchy |
| ✅ Logo correct | Proper variant, clear space, no distortion |
| ✅ Imagery style | Photo style/filters consistent |
| ✅ Cross-channel | Website, social, email all feel unified |

---

## Anti-Patterns

| Pattern | Problem | Instead |
|---------|---------|---------|
| Different colors per platform | Brand becomes unrecognizable | Same hex codes everywhere |
| Voice shifts by channel | "Professional" on web, "lol" on socials | Same voice, adapted tone |
| No logo guidelines | Logo used inconsistently or distorted | Define clear space, min size, variants |
| Multiple font families | Cluttered, unprofessional look | Max 2 families, defined hierarchy |
| Undocumented standards | New content drifts from brand | Write it down in `docs/brand-context.md` |
