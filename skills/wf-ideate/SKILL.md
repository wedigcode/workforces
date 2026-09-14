---
name: wf-ideate
description: Orchestrates dual-engine product ideation and concept incubation by unbundling bloated SaaS incumbents and scouting low-end market disruptions. Reach for this skill or trigger it when searching for high-margin software opportunities, evaluating unbundled single-purpose SaaS concepts, identifying under-served market segments, or stress-testing product ideas through viability scorecards before initiating site setup or PRD authoring.
---

# Dual-Engine Product Ideation & Incubation (/wf-ideate)

End-to-end ideation and opportunity incubation engine. Coordinates parallel research across two specialized engines led by `@advisor`.

---

## 1. Dual Discovery Engines

| Engine | Lead Agent | Methodology & Evaluation Filters |
| :--- | :--- | :--- |
| **Engine A: Atomic Micro-SaaS** | `@unbundler` | • Isolate 1-minute magic moment vs. modern bloat point.<br>• **Viability Scorecard (1–5)**: Frequency, WTP, Standalone Integrity, Spreadsheet Moat.<br>• Bottom-up TAM/SAM/SOM to \$10k–\$100k MRR. |
| **Engine B: Market Disruption** | `@disruptor` | • Macro industry shifts (consulting reports, VC trends).<br>• **\$1B Market Math**: $\text{Target Customers} \times \text{Product Price} > \$1\text{B}$.<br>• **4 Leverage Criteria**: Subscription, $\ge 70\%$ Margin, Pure Tech Scaled, 100% Owned IP. |

---

## 2. Executive Opportunity Matrix

Synthesize subagent discovery results into a comparative matrix:

| Opportunity | Engine | Extracted Angle | Target Sizing | Viability (1-5) | Primary Moat |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Concept 1** | `@unbundler` | [Atomic extracted feature] | [\$MRR Day 90 / Yr 1] | 4.8 / 5 | [Spreadsheet Moat] |
| **Concept 2** | `@disruptor` | [Macro trend disruption] | [>\$1B Market Math] | 4.9 / 5 | [Workflow Speed] |

---

## 3. Stress-Testing Gatekeeper

Before writing PRDs, test the winning concept against 3 strict filters:
1. **The "Why Not a Spreadsheet?" Test**: Validate the exact UX mechanism (drag-and-drop, email automation, keyboard flow) that makes this 10x faster than a free Google Sheet.
2. **The 3 Dangerous Trap Features**: Define the 3 non-goals that would re-bloat the tool.
3. **The 48-Hour Smoke Test**: Define the fake door or pre-sale offer to test purchasing intent before writing code.

---

## 4. PRD Generation & Inbox Registration

Compile output into `docs/prd-[concept-name].md` and register the concept into `workforces/issues/inbox/` via `report-issue.py`:

```bash
python3 .agents/skills/issue-tracker/scripts/report-issue.py \
    --title "Micro-SaaS Concept: [Name]" \
    --type idea \
    --severity P0 \
    --reporter advisor \
    --session-id "[seq]" \
    --session-file "workforces/session-context/<seq>_<date>_<slug>.md" \
    --file "docs/prd-[concept-name].md" \
    --description "[One-line thesis & 10x value breakthrough]" \
    --suggested-action "Validate demand via market-validation skill then scaffold with site-setup" \
    --sync-session
```
*(Fallback: `python3 skills/issue-tracker/scripts/report-issue.py ...`)*
