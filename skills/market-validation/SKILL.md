---
name: market-validation
description: Validates market demand and customer willingness-to-pay before writing code using pretotyping techniques (Alberto Savoia's XYZ hypotheses, fake door smoke tests, pre-sale commitments) and The Mom Test interview protocols. Reach for this skill when evaluating a speculative business concept, designing low-budget validation experiments, testing customer commitment tiers, or formulating unbiased customer discovery interviews.
---

# Rapid Market Validation & Revenue Pretotyping

Low-budget, high-velocity market validation system for testing demand before writing production code.

---

## 1. Core Validation Laws

1. **"Make sure you are building the right *it* before you build it right."** (Alberto Savoia) — Preprototype before writing software.
2. **"Currency over Compliments."** — Disregard polite praise; require skin in the game (cash, data, or time).
3. **"Past Behavior over Hypothetical Intent."** (The Mom Test) — Ask what prospects already do and spend, never what they *would* do.
4. **"Kill Early to Scale Winners."** — Pre-commit to kill thresholds; sunset stalled ideas within 7 days.

---

## 2. Skin in the Game Commitment Hierarchy

| Level | Currency Type | Weight | Interpretation & Gatekeeper Action |
| :---: | :--- | :---: | :--- |
| **0** | **Compliments** | **0 / 10** | ⚠️ **False Signal**: Polite social praise ("great idea!"). Completely disregard. |
| **1** | **Contact Info** | **2 / 10** | **Low Commitment**: Email/phone. Only actionable at high volume (>10% conversion). |
| **2** | **Work Effort / Data** | **5 / 10** | **Moderate Commitment**: Uploaded sample file, completed workflow audit questionnaire. |
| **3** | **Time Investment** | **7 / 10** | **High Commitment**: Attended 20–30 min problem discovery or prototype walkthrough call. |
| **4** | **Financial Currency** | **10 / 10** | 🏆 **Gold Standard**: Cash pre-order, deposit, or signed LOI. Validates true WTP. |

---

## 3. Falsifiable XYZ Hypothesis Formula

```
"We believe that at least [X]% of [Target Audience Y] will perform [Skin-in-the-Game Action Z]
 when presented with [Offer / Value Prop] within [Timeframe T]."
```

- **Leading Indicator**: Ad clicks, landing page visits, cold outbound sends, inbound DMs.
- **Lagging Indicator**: Pre-orders ($), deposit captures, discovery calls booked, LOIs signed.
- **Kill Threshold**: Pre-determined failure point (e.g. `< 3%` conversion after 200 visits; `0` calls from 50 sends).

---

## 4. Rapid Validation Channels

| Channel | Model | Ideal Use Case | Success Hurdle |
| :--- | :--- | :--- | :--- |
| **Smoke Test Page + Ads** | 1-page site + \$50–\$100 micro-ads | B2C, Self-Serve SaaS | Click-to-intent rate > 8–12%; CPL < \$3.00. |
| **The Mom Test Outreach** | 50 problem-first DMs/emails (no pitch) | B2B, High-Ticket SaaS | > 15% response rate; >= 5 calls; >= 2 pilot LOIs. |
| **Community Infiltration** | Value breakdown post in Reddit/Discord | Vertical Niche SaaS | >= 15 inbound requests for workflow automation. |
| **Build in Public** | Architecture choice polls on X/LinkedIn | DevTools, Open Source | > 5% engagement ratio + organic waitlist signups. |

---

## 5. Gatekeeper Validation Scorecard

- 🟢 **VALIDATE & SCALE**: Target metrics achieved; proven willingness to pay $\rightarrow$ Hand off to `/wf-plan`.
- 🔄 **PIVOT OFFER**: High engagement but low skin-in-the-game $\rightarrow$ Adjust pricing/positioning; re-test for 72h.
- 💀 **KILL EXPERIMENT**: Kill threshold breached $\rightarrow$ Terminate idea; log in `workforces/hypotheses/invalidated/`.
