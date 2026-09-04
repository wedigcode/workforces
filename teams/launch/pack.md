# Team Pack Building Block: Launch & Fast Validation

## Domain Purpose
Specialized strike team designed for **empty projects**, **pre-revenue apps**, or **stalled initiatives with zero paying customers**. Relentlessly optimizes for two foundational velocity metrics: **Time to First Dollar (TTFD)** and **Time to 100 Users (TTOU)**.

---

## Principles of Domain Excellence

1. **TTFD as North Star (Purchase Intent > Casual Compliments):**
   - Free signups, likes, and waitlist counts measure casual curiosity. True market validation requires financial skin-in-the-game.
   - If an empty project has made \$0, all complex backend engineering, auth migrations, and admin dashboards are blocked until the first dollar is secured.

2. **Funnel Friction Elimination (Killing the Waitlist Trap):**
   - **Micro-Budget ROAS Self-Funding:** Avoid spending \$100 on ads to collect 3–5 free emails. Route ad traffic directly to a low-ticket pre-order to recoup spend immediately.
   - **Confirmation Page Cash Offer:** Free email leads decay by >80% within 7 days. Present an immediate founder pass offer or card hold while user excitement is peak.
   - **Single Early-Adopter Offer:** Eliminate 3-tier pricing paralysis ($10 / $99 / $500) for unreleased software. Standardize on one irresistible Founder Lifetime Deal ($29–$49) capped at 25–50 seats.

3. **High-Velocity Validation Rails:**
   - **The Pre-Sale "Painted Door":** Validate purchase intent using Stripe Payment Links (Direct Payment or SetupIntent card holds) or honest cohort capacity modals before coding.
   - **The Concierge MVP (Wizard of Oz):** Fulfill the software outcome manually (LLM prompts via email, spreadsheet scraping, manual audits) to generate immediate revenue and raw customer feedback.

4. **The 7-Day TTFD Sprint Cadence:**
   - Day 1: Outcome positioning + 1-page landing page (Carrd/Framer/HTML).
   - Day 2: Payment rails & single founder offer ($49 Founder Lifetime Access).
   - Day 3–4: 50 personalized outreach DMs on X, Reddit, or LinkedIn (Zero ad spend).
   - Day 5: $50–$100 micro ad test on niche subreddits or Meta interests.
   - Day 6–7: Manual outcome fulfillment + 15-minute onboarding calls with every buyer.

5. **TTOU Distribution Scale (Reaching 100 Users):**
   - Once TTFD is achieved, scale distribution through directory launches (Product Hunt, Betalist, MicroLaunch, 1000Tools, IndieHackers), founder-led build-in-public content, incentivized referral loops (Rewardful/Tolt), and Apollo/Clay cold outreach.

---

## Team Roles & Cross-Functional Alignment

- **Launch Specialist (`@launcher`):** Strike team quarterback and fast validation orchestrator. Directs the sprint, audits funnel friction, and enforces monetization-first discipline. See [`launcher.md`](../../agents/launcher.md).
- **Marketing Lead (`@marketer`):** Crafts outcome-driven hero copy (`Achieve [Outcome] without [Pain] in [Timeframe]`), thank-you page upsells, and 30-day risk reversal guarantees.
- **Growth Lead (`@growth`):** Manages $50–$100 micro ad tests, directory launch submissions (Product Hunt, Betalist), and 20% referral loops.
- **Programmer (`@programmer`):** Configures lightweight Stripe Payment Links, SetupIntent pre-auth, or painted door modals with zero premature backend bloat.
- **Sales Specialist (`@sales`):** Executes 1-on-1 problem-first community outreach and schedules 15-minute onboarding feedback calls.

---

## SOP / Workflow Patterns

When activating the launch team on a project, select the appropriate execution pattern:
- **`wf-launch --audit`:** Audit funnel friction, lead decay, and pricing complexity in empty or pre-revenue projects.
- **`wf-launch --ttfd`:** Execute the prescriptive 7-Day Sprint to First Dollar.
- **`wf-launch --presale`:** Configure Pre-Sale Painted Door rails (Stripe Payment Links or SetupIntent holds).
- **`wf-launch --concierge`:** Blueprint and deliver a Concierge MVP (manual fulfillment).
- **`wf-launch --copy`:** Generate high-converting hero copy, confirmation upsells, and DM scripts.
- **`wf-launch --ttou`:** Execute the 4-channel distribution engine to reach 100 active users.
