---
description: Fast-track idea-to-revenue market validation pipeline. Formulates Alberto Savoia XYZ Hypotheses, generates smoke test landing pages or Mom Test outreach scripts, registers bets with hypothesis-tracker, and enforces PM Go/Pivot/Kill gatekeeping within 7 days.
---

# /validate-idea — Rapid Idea-to-Revenue Market Validation Pipeline

The prescriptive, step-by-step market validation pipeline for Workforces. Takes speculative software or business ideas and proves market interest and willingness to pay **before** writing code or investing heavy engineering time.

Coordinated by the **Strategic Advisor** (`@advisor`) and governed by the **Project Manager** (`@project-manager`) with specialized asset generation by `@marketer` and `@growth`.

---

## 🧭 Workflow Overview

```mermaid
graph TD
    A["Step 0: Intake & Opportunity Framing<br/>Seed idea, problem space & target persona"] --> B["Step 1: The XYZ Hypothesis & Kill Gate<br/>At least X% of Y will do Z + Kill Threshold"]
    B --> C["Step 2: Rapid Asset Generation<br/>Landing Page Copy / Micro-Ad Specs / Mom Test Outreach"]
    C --> D["Step 3: Automated Experiment Registration<br/>Register with hypothesis.py & report-task.py"]
    D --> E["Step 4: 72-96h Market Signal Injection<br/>Micro-Ads ($50-$100) | Community | Cold Outreach | Build in Public"]
    E --> F["Step 5: PM Skin-in-the-Game Audit & Gatekeeping<br/>Scoring Currency > Compliments (Go / Pivot / Kill)"]
    F -->|Validated (Level 3-4)| G["Handoff to /site-setup & /work (Build MVP)"]
    F -->|Pivot Signal| H["Refine Value Prop / Re-test 72h"]
    F -->|Invalidated / Missed| I["Kill Project & Archive in Knowledge Catalog"]
```

---

## 💬 Usage

```bash
/validate-idea [idea]        # Run the full 5-step rapid market validation pipeline
/validate-idea --smoke-test  # Focus specifically on smoke test landing page + micro-ad specs
/validate-idea --mom-test    # Focus specifically on B2B cold outreach & past behavior discovery
/validate-idea --audit       # PM review of running validation experiments against kill thresholds
```

---

## 🛠️ Required Skills

Before starting, the following skills are loaded:
1. **`market-validation`** — Pretotyping principles, the Skin-in-the-Game ladder, and playbook rules.
2. **`hypothesis-tracker`** — CLI and tracking engine for scientific business experiments.
3. **`business-frameworks`** — Jobs-to-be-Done (JTBD) situational triggers and Value Stick mechanics.
4. **`task-tracker`** — Deferred task lifecycle and session lineage recording.

---

## 📋 The 5-Step Validation Pipeline

---

### Step 0 — Intake & Opportunity Framing (`@advisor`)

The user provides a concept seed or selects an idea from `/ideate`. `@advisor` clarifies 3 essential pillars:
1. **Target Persona:** Who suffers from this pain most acutely? What is their exact job role and company profile?
2. **Situational Trigger:** What specific event triggers them to search for a solution today?
3. **Primary Validation Channel:**
   - **Smoke Test Landing Page + Micro-Ads** (B2C / Self-serve SMB)
   - **Direct Cold Outreach & The Mom Test** (B2B SaaS / High-ticket services)
   - **Community Infiltration** (Vertical niches, Discord, Reddit, Slack)
   - **Build in Public** (DevTools, open source, creators)

---

### Step 1 — Formulate the Falsifiable XYZ Hypothesis & Kill Threshold

`@advisor` structures the experiment following the **Alberto Savoia XYZ Formula**:

$$\text{At least } X\% \text{ of } [Target\ Audience\ Y] \text{ will perform } [Skin\text{-}in\text{-}the\text{-}Game\ Action\ Z]$$

```markdown
### 🔬 Falsifiable Validation Bet
- **Hypothesis Code:** HYP-[YYYYMMDD]-[SEQ]
- **Target Persona:** [Specific role, industry, trigger]
- **Core Value Proposition:** [Outcome-driven hook]
- **XYZ Statement:** "We believe that at least **[X]%** of **[Target Audience Y]** will perform **[Action Z: Pre-Order / Book Call / Submit Workflow Data]** within **[Timeframe: 7 Days]**."
- **Leading Indicator:** [e.g. 200 Ad clicks / 50 Cold sends / 500 Community views]
- **Lagging Indicator:** [e.g. 15 Waitlist signups + 3 Pre-orders / 5 Booked calls]
- **Kill Threshold:** [e.g. Click-to-signup conversion < 4% after 200 visitors, or 0 calls booked after 50 sends]
- **Pivot Contingency:** [Pre-committed alternate angle if threshold is breached]
```

---

### Step 2 — Rapid Asset Generation (`@marketer` & `@growth`)

Based on the chosen channel, the agents generate ready-to-deploy copy and specs:

#### For Smoke Test Pages:
- **Hero Copy:** Outcome headline, mechanism sub-headline, and risk-reversal microcopy.
- **3 Transformation Bullets:** Pain eliminated, speed advantage, and ROI outcome.
- **"Fake Door" Intent Modal:** 2-step capture form (Work Email + Role + #1 Pain Point).
- **Micro-Ad Creative:** 2 Google Search Ad copy variants (Headline + Description) or 2 Meta/Reddit ad copy hooks.

#### For Mom Test Outreach:
- **Subject Lines & Initial Problem Inquiries:** 50-word curiosity-first messages validating past behavior and existing workarounds without pitching software prematurely.
- **15-Minute Discovery Call Guide:** 4 non-leading questions focusing on current spend and manual toil.

---

### Step 3 — Automated Experiment Registration (`hypothesis.py`)

> 🚨 **Mandatory Tool Call**: The agent MUST register the experiment in `hypothesis-tracker` and link it to active session context:

```bash
python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py \
    --create \
    --title "[Idea Name] Rapid Market Validation" \
    --owner growth \
    --supporting-teams marketing advisor \
    --statement "At least [X]% of [Y] will perform [Action Z] when presented with [Offer] within 7 days." \
    --timeframe-weeks 1 \
    --kill-threshold "[Specific numerical kill condition]" \
    --pivot-plan "[Contingency pivot strategy]" \
    --metrics '[{"name":"[Leading Metric]","type":"leading","baseline":0,"target":[TargetNum],"current":0,"unit":"count"},{"name":"[Lagging Metric]","type":"lagging","baseline":0,"target":[TargetNum],"current":0,"unit":"count"}]' \
    --session-id "[seq]" \
    --session-file "workforces/session-context/<seq>_<date>_<slug>.md" \
    --sync-session
```
*(Fallback: `python3 skills/hypothesis-tracker/scripts/hypothesis.py ...`)*

---

### Step 4 — 7-Day Live Traffic & Signal Injection Execution

The human user or growth team runs the validation test in market for 72–96 hours:
- **Micro-Ads Spend Cap:** Strict \$50–\$100 budget limit.
- **Cold Sends:** 30–50 personalized sends.
- **Daily Telemetry Logging:** Update progress daily via `hypothesis.py --update [HYP-ID] --metrics-data "[Key]=[Val]"`.

---

### Step 5 — Day 7 PM Skin-in-the-Game Audit & Decision Gate

The Project Manager (`@project-manager`) reviews the telemetry against the **Skin-in-the-Game Commitment Ladder**:

```markdown
# 📊 PM Market Validation Scorecard

| Metric Category | Target Hurdle | Actual Result | Status |
| :--- | :--- | :--- | :---: |
| **Traffic / Reach** | [Target Reach] | [Actual Reach] | 🟢 / 🔴 |
| **Budget Incurred** | $\le \$100$ | $\$[Actual]$ | 🟢 / 🔴 |
| **Skin-in-the-Game Level** | Level 3 (Time/Calls) or Level 4 (Cash/Pre-Orders) | Level [0-4] | 🟢 / 🔴 |
| **Primary Conversion Rate** | $\ge [Target]\%$ | $[Actual]\%$ | 🟢 / 🔴 |

### Gatekeeper Decision:
- 🟢 **VALIDATE & BUILD MVP:** Proceed immediately to `/site-setup` (Step 1 Marketing & Step 2 `@designer`) followed by `/work` to build the functional MVP for early adopters.
- 🔄 **PIVOT VALUE PROP:** Moderate engagement (Level 1/2) but low commercial commitment. Pivot copy, pricing tier, or ICP and run a 72-hour re-test.
- 💀 **KILL EXPERIMENT:** Kill threshold breached. Sunset experiment via `hypothesis.py --kill` to prevent zombie project drag.
```

---

## 🌟 Integration with Other Workflows

- **Triggered from `/ideate`:** Winning unbundled micro-SaaS concepts pass directly into `/validate-idea` for pre-build demand testing.
- **Reviewed in `/sync --strategy`:** Active validation bets appear in the weekly strategic sync review.
- **Graduated to `/site-setup` & `/work`:** Validated ideas with Level 3–4 commitments graduate straight into frontend scaffolding and sprint development.
