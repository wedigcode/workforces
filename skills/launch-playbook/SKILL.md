---
name: launch-playbook
description: Accelerates product launches by relentlessly optimizing for Time to First Dollar and Time to 100 Users. Reach for this skill when preparing to launch a pre-revenue product, structuring high-velocity 7-day pre-sale offers with live payment rails, executing concierge MVPs, diagnosing waitlist decay, or rolling out direct acquisition tactics to secure the first 100 active customers.
---

# App Launch & Fast Validation Playbook

High-velocity playbook for pre-revenue apps and zero-traction initiatives. Led by `@launcher`, relentlessly optimizing for two core velocity metrics: **Time to First Dollar (TTFD)** and **Time to 100 Users (TTOU)**.

---

## 1. Core Velocity Metrics

| Metric | Definition | Threshold / Rule |
| :--- | :--- | :--- |
| **TTFD** (Time to First Dollar) | Elapsed calendar days from idea inception to first financial transaction. | **Max 14 days.** If TTFD > 14 days, kill or strip all code down to a concierge MVP or pre-sale painted door. |
| **TTOU** (Time to 100 Users) | Calendar days to reach 100 active, paying, or retained users. | Never build complex multi-tier billing or microservice infrastructure until TTOU is achieved. |

---

## 2. The 7-Day Sprint to First Dollar (TTFD)

```
Day 1: Positioning   ──> Define acute pain point + 1-page offer (Carrd/Framer/HTML).
Day 2: Payment Rails ──> Set up Stripe Payment Link ($29–$49 Founder Pass / LTD).
Day 3–4: Direct DMs  ──> 50 targeted problem DMs on X/Reddit/LinkedIn (0 ad spend).
Day 5: Micro-Ad Test ──> $50–$100 niche ad test to benchmark CPC and checkout rate.
Day 6–7: Delivery    ──> Fulfill manually (Concierge MVP) + 15-min onboarding calls.
```

---

## 3. High-Velocity Validation Archetypes

| Framework | Implementation | Actionable Pattern |
| :--- | :--- | :--- |
| **Pre-Sale Painted Door** | Test purchasing intent before backend code exists. | 1. **Direct Payment**: Stripe Payment Link with 100% money-back guarantee.<br>2. **Card Authorization**: Authorize payment hold (`capture_method: manual` on `PaymentIntent`) or save card via `SetupIntent` with explicit customer consent to charge upon feature delivery.<br>3. **Capacity Modal**: Honest early-bird cap reserving priority discount. |
| **Concierge MVP (Wizard of Oz)** | Deliver product output manually before automating. | Fulfill data scraping, prompt outputs, or audits manually via spreadsheet or email within 2 hours to learn real customer edge cases. |

---

## 4. TTOU Distribution Channels (1 to 100 Users)

1. **Structured Directory Launches**: Post to Product Hunt, Betalist, MicroLaunch, and niche subreddits (`r/SideProject`, `r/SaaS`).
2. **Founder-Led Build in Public**: Share transparent conversion metrics and customer case studies on X and LinkedIn.
3. **Incentivized Referral Loops**: Offer paying customers 1 month free or 20% recurring commission (via Tolt/Rewardful) per referral.
4. **Targeted Cold Sequences**: Run problem-first cold emails offering manual mini-audits to laser-targeted prospects.
