---
description: Multi-mode meeting orchestrator — daily standups (--daily), strategic & hypothesis reviews (--strategy), and goal scaffolding (--goals). Logs to workforces/team-sync/YYYY-MM-DD.md.
---

# /work sync — Multi-Mode Team Sync & Strategic Alignment

A unified meeting engine for daily execution, strategic course-correction, goal scaffolding, and hypothesis tracking. Led dynamically by `@project-manager` (for execution standups) or `@advisor` (for strategic reviews and diagnostics).

---

## 🧭 Meeting Modes & Usage

```bash
/work sync                # Default: Daily Execution Standup (Led by @project-manager)
/work sync --daily        # Explicit: 5-min tactical standup on 24h wins, blockers & "The One Thing"
/work sync --strategy     # Strategic Review: OKRs, KPIs, Hypothesis Pacing, SME Round-Table (Led by @advisor)
/work sync --goals        # Goal & Milestone Scaffolding: Setup/reset Annual North Star & Q1-Q4 OKRs
```

---

## 🚦 Meeting Router & Leadership Matrix

```mermaid
graph TD
    Trigger["/work sync [flag]"] --> Router{"Inspect Mode"}
    
    Router -->|"--daily (Default)"| ModeDaily["Mode 1: Daily Standup<br/><b>Leader: @project-manager</b><br/>Focus: 24h Velocity & Blockers"]
    Router -->|"--strategy"| ModeStrat["Mode 2: Strategic Review<br/><b>Leader: @advisor</b><br/>Focus: OKRs, Hypotheses & Bottlenecks"]
    Router -->|"--goals"| ModeGoals["Mode 3: Goal Scaffolding<br/><b>Co-Leaders: @advisor + @project-manager</b><br/>Focus: North Star & OKR Hierarchy"]
    
    ModeDaily --> StandupExec["• Yesterday's Wins & Losses<br/>• The 'One Thing' (P0)<br/>• Blocker Escalation<br/>• Issue Inbox Triage"]
    ModeStrat --> StratExec["• Cross-Functional SME Round-Table<br/>• OKR & Milestone Pacing<br/>• Hypothesis Telemetry & Kill Criteria<br/>• 5 Strategic Multipliers<br/>• 5-Dimension Root-Cause Diagnostic"]
    ModeGoals --> GoalExec["• North Star Metric Formulation<br/>• Q1-Q4 Strategic Objectives<br/>• Monthly Milestones Breakdown<br/>• Goal-to-Sprint Task Alignment"]
    
    StandupExec --> ScribeLog["@scribe: Logs to workforces/team-sync/YYYY-MM-DD.md"]
    StratExec --> ScribeLog
    GoalExec --> ScribeLog
```

---

# Mode 1: Daily Execution Standup (`/sync --daily`)

**Meeting Leader:** `@project-manager`  
**Duration Target:** 2–5 minutes  
**Primary Goal:** Unblock the team, lock in today's single most critical commitment, and triage incoming issues.

### Step D1 — Ingest Daily State
1. Read `workforces/workstate.md` for active, pending, and completed sprint tasks.
2. Read `workforces/issues/inbox/` for new bugs, tech debt, or spontaneous ideas logged by agents or user.
3. Check GitHub queue (`gh pr list`, `gh issue list`) for external PR review requests.

### Step D2 — Review 24h Wins & Roadblocks
- **🏆 Wins:** What was marked completed in `workstate.md` since the last standup?
- **⚠️ Roadblocks:** What tasks are currently stalled, waiting on credentials, or blocked by API dependencies?

### Step D3 — Lock In "The One Thing"
- Identify the single highest-leverage task for today (**P0 Priority**).
- Verify that every active team has exactly one primary focus.

### Step D4 — Triage Issue Inbox
- Review pending files in `workforces/issues/inbox/*.md`.
- Promote P0/P1 items to `workstate.md` and GitHub Issues.
- Move triaged files to `workforces/issues/triaged/` or `workforces/issues/completed/` (if rejected).

### Step D5 — Present Standup Report
```markdown
## 🔄 Daily Standup — YYYY-MM-DD

### 🏆 24h Wins
- [x] Task A — Description of achievement.

### ⚠️ Roadblocks & Immediate Blockers
- [ ] Task B — Blocked on staging OAuth domain verification (@programmer).

### 🎯 The One Thing Today
> **[Task C Title]** (Priority P0 — Owner: `@programmer`)
> *Why:* Critical path item blocking revenue milestone.

### 📬 Inbox Triage
- Triaged 2 items (1 promoted to P1, 1 logged to backlog).

### 🙋 Help Needed from User
- Approval for staging API key configuration.
```

---

# Mode 2: Strategic Review, Brainstorming & Hypothesis Discovery (`/sync --strategy`)

**Meeting Leader:** `@advisor` (Co-pilot: `@project-manager`)  
**Duration Target:** 10–15 minutes  
**Primary Goal:** Brainstorm high-leverage opportunities for the next cycle, extract winning ideas into falsifiable hypotheses, enforce factual telemetry grounding, explore tool & subagent delegation (Jules, Copilot, Stitch, Flow/Vids/Slides), audit OKR pacing, and enforce kill/pivot criteria.

### Step S1 — Ingest Factual Business State & Grounding
1. **Factual Telemetry Grounding:** Enforce the zero-hallucination rule. Check verified outreach logs, commit history, and analytics. If no customer outreach or ad campaigns have run, record the factual baseline (`0 outreach calls / 0 live ads; pre-launch stage`).
2. **Strategic Goals:** Read `workforces/goals/` for current quarter objectives and key results.
3. **Active Hypotheses:** Query `skills/hypothesis-tracker/scripts/hypothesis.py --review` for active experiments in `workforces/hypotheses/running/`.
4. **Velocity & Backlog:** Read `workforces/workstate.md` for completed vs backlog tasks and async worker statuses.
5. **Design Feedback Memory:** Read `workforces/memory/design-preferences.md` for negative constraints and approved aesthetic preferences.

### Step S2 — Factual Team Status & Advisor Strategic Inquiry
Domain agents report ONLY verified historical data. `@advisor` then actively queries each department with sharp consultative probes:

```markdown
### 🎙️ Factual Status & Strategic Inquiry Round-Table
- **💼 Sales (`@sales`):**
  - *Factual Telemetry:* 0 prospect outreach calls completed to date (pre-launch / baseline stage).
  - *Advisor Probe:* "Who is the single most desperate buyer archetype in our target market, and what specific pain hook will get an immediate reply once we launch outbound?"
- **📈 Marketing & Growth (`@marketer` / `@growth`):**
  - *Factual Telemetry:* Organic search protocols live; 0 ad spend deployed.
  - *Advisor Probe:* "What high-converting content formats (e.g. interactive ROI calculators, short-form video teardowns) can we test next cycle to drive organic acquisition?"
- **💻 Engineering (`@programmer`):**
  - *Factual Telemetry:* Core MVP build passing 100% tests; auth service refactor complete.
  - *Advisor Probe:* "What parts of the upcoming feature backlog can be offloaded to async coding workers like Google Jules or GitHub Copilot to accelerate delivery?"
- **🎨 Design (`@designer`):**
  - *Factual Telemetry:* Tokens aligned with `design-preferences.md` (0 yellow on light/white).
  - *Advisor Probe:* "What interactive visual prototypes or design variations should we iterate internally before presenting to human review?"
```

### Step S3 — Cross-Functional Brainstorming & Idea Extraction (Loop Process)
The team engages in a structured brainstorming loop to extract winning ideas for the next cycle:
1. **Unpack Market Assumptions:** Identify speculative ideas (e.g. *"Solo agents want 1-touch mobile checkout"* or *"Brokers want audit compliance dashboards"*).
2. **Convert to Falsifiable Hypotheses:** Convert every speculative assumption into a structured experiment using `hypothesis.py --create`:
   - Define Owner (`@sales`, `@marketer`, `@growth`, `@programmer`, `@designer`)
   - Define Falsifiable Statement
   - Define Leading Indicators (e.g. discovery calls booked, prototype signups) and Lagging Indicators (e.g. paid conversions)
   - Define Kill / Pivot Thresholds
   - Attach Recommended Tools (e.g. `google-vids`, `google-stitch`, `jules`) and GitHub labels (`tool:...`, `type:hypothesis`)
3. **Capture Product / Technical Ideas:** Log technical or UX feature ideas into `workforces/issues/inbox/` using `report-issue.py --title "..." --type idea --tools "..." --sync-session`.

### Step S4 — Dynamic Tool Enablement & Delegation Inquiry
`@advisor` probes the team on tool acceleration opportunities:
> *"What tools, async subagents, or external systems (e.g. Google Jules / GitHub Copilot for dev, Google Stitch for UI, Google Flow/Vids/Slides for marketing, ad/analytics MCPs) could take work off your plate or 10x your throughput next cycle?"*

- **Identified Tooling & Delegation Requests:**
  - **Dev:** Delegate async refactoring tasks to Google Jules (`jules remote list --session`) or GitHub Copilot PRs (`delegated_to: jules`, label: `tool:jules`).
  - **Marketing:** Leverage Google Flow / Google Vids / Google Slides for autonomous video script and presentation drafting (`tool:google-vids`).
  - **Design:** Leverage Google Stitch or Figma MCP for rapid token and component scaffolding (`tool:google-stitch`).

### Step S5 — Scientific Hypothesis & Experiment Review (Kill / Pivot Enforcer)
Run `python3 skills/hypothesis-tracker/scripts/hypothesis.py --review`:
- Audit weekly pacing on leading and lagging indicators for all running experiments.
- **Kill Criteria Enforcement:** If an experiment elapsed time is up and metrics breached the kill threshold:
  > *"🚨 **Kill Criteria Triggered:** Experiment `HYP-20260823-01` achieved 2.1% reply rate vs. 3% kill threshold. Recommending immediate sunset and pivoting resources."*

### Step S6 — Goal & OKR Pacing Analysis
Compare progress against quarterly key results and calculate the **Goal Alignment & Coverage Index**:

| Goal / Key Result | Target | Current | Pacing | Goal Coverage | Linked Tasks / Hypotheses |
|:---|:---|:---|:---|:---|:---|
| **KR 1:** Acquire 25 pilot accounts | 25 | 0 (Pre-launch) | 🟡 In Setup | ✅ Covered | HYP-01 (Outbound Test), 2 sprint tasks |
| **KR 2:** Launch core MVP platform | 100% | 85% | 🟢 On Track | ✅ Covered | 3 sprint tasks |

### Step S7 — The 5 Strategic Multipliers
1. **Leading vs. Lagging Indicator Scrutiny:** Scrutinize leading telemetry (discovery calls, search impressions, commit velocity) weeks before revenue is impacted.
2. **Kill Criteria & Anti-Zombie Discipline:** Formally archive failed hypotheses to prevent half-dead initiatives from draining attention.
3. **Capacity & Bottleneck Heatmap (Theory of Constraints):** Identify the single system bottleneck across Dev, Design, Sales, Marketing, or Operations.
4. **Voice of Customer (VoC) & Objection Pulse:** Surface top 2 raw buyer objections heard by `@sales` and UX friction points heard by `@advisor`.
5. **Decision Log & Disagree-and-Commit Lineage:** Explicitly record strategic pivots, killed experiments, and rationale in `workforces/team-sync/` and active session notes.

### Step S8 — Autonomous AI Execution Roadmap with Human Approval Gates
Clearly demarcate what AI will execute autonomously next cycle vs. what requires human direction:

```markdown
## 🧭 Strategic Review & Next-Cycle Action Plan — YYYY-MM-DD

### 💡 Brainstormed Hypotheses & Experiments for Next Cycle
- [ ] **HYP-01 (@sales):** Test 50 personalized problem-first emails to solo agents. [Tools: email-crm, Label: `tool:sales-outreach`]
- [ ] **HYP-02 (@marketer):** Test 3 video problem teasers for Instagram/TikTok. [Tools: google-vids, Label: `tool:google-vids`]

### 🧰 Tool Enablement & Async Delegation Requests
- **Dev:** Assign auth token cache refactor to Google Jules (`jules remote list --session`, Label: `tool:jules`, `delegated:jules`).
- **Marketing:** Enable Google Vids / Slides integration for automated video generation.

### 🤖 Autonomous AI Next-Cycle Execution (No Human Intervention Needed)
1. `@programmer`: Execute sprint tasks #12–#14, run test suites, and review Jules patch for auth refactor.
2. `@designer`: Run multi-pass self-iterations on mobile checkout layout against `design-preferences.md`.
3. `@marketer`: Draft 3 video scripts and prepare social distribution schedule.

### 🙋 Human Approval & Direction Gates (Your Decision Needed)
1. Approve launching Hypothesis HYP-01 and HYP-02.
2. Review final UI design options once `@designer` completes internal iteration passes.
```

---

# Mode 3: Goal & Milestone Scaffolding (`/sync --goals`)

**Meeting Leaders:** `@advisor` (Strategic Discovery) + `@project-manager` (Scaffolding & Milestone Sequencing)  
**Primary Goal:** Establish or reset company goals, annual North Star, quarterly OKRs, and monthly milestones when `workforces/goals/` is empty or at quarter boundaries.

### Step G1 — North Star Discovery
`@advisor` asks 2 targeted consultative questions:
1. *"What is the single North Star metric that defines company success for the next 12 months? (e.g. $50k MRR, 10,000 active users, 50 enterprise pilots)"*
2. *"What are the 2–3 core pillars required to hit that number? (e.g. Acquisition engine, Product retention, Enterprise compliance)"*

### Step G2 — Scaffold Quarterly OKRs
Generate `workforces/goals/YYYY_QX_goals.md` using `skills/workforce-management/templates/goal-template.md`:
- 2–3 Objectives with 2–3 quantifiable Key Results each.
- Assign an owning team (`@sales`, `@growth`, `@programmer`, etc.) to each KR.

### Step G3 — Break Down Monthly Milestones
Structure the quarter into 3 monthly milestone gates (Month 1 Foundation, Month 2 Funnel Acceleration, Month 3 Scale).

### Step G4 — Seed Initial Sprint Backlog
`@project-manager` turns Month 1 milestones into initial P0/P1 tasks in `workforces/workstate.md` with full goal lineage.

---

## 📝 Logging & State Preservation

After the user approves the sync summary:
1. **Save Log:** `@scribe` writes the approved record to `workforces/team-sync/YYYY-MM-DD.md` (or `YYYY-MM-DD-strategy.md`).
2. **Update Workstate:** Synchronize `workforces/workstate.md` task priorities and statuses.
3. **Update Hypotheses:** Transition any killed, validated, or updated hypotheses via `hypothesis.py`.
4. **Preserve Lineage:** Update active session context note in `workforces/session-context/`.
