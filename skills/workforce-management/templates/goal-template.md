---
year: "{{YEAR}}"
quarter: "{{QUARTER}}" # Q1, Q2, Q3, Q4
north_star_metric: "{{NORTH_STAR_METRIC}}"
target_value: "{{TARGET_VALUE}}"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
status: "active" # active | completed | archived
---

# Strategic Goals & Objectives: {{YEAR}} {{QUARTER}}

**North Star Metric:** {{NORTH_STAR_METRIC}} (Target: **{{TARGET_VALUE}}**)  
**Period:** {{YEAR}} {{QUARTER}} | **Status:** `active`

---

## 🎯 Strategic Objectives & Key Results (OKRs)

### Objective 1: {{OBJECTIVE_1_TITLE}}
> **Focus:** {{OBJECTIVE_1_THEME}} (Owner: `@{{OBJECTIVE_1_OWNER}}`)

| Key Result | Target | Baseline | Current | Pacing | Linked Team |
|:---|:---|:---|:---|:---|:---|
| **KR 1.1:** {{KR_1_1_DESCRIPTION}} | {{KR_1_1_TARGET}} | {{KR_1_1_BASELINE}} | {{KR_1_1_CURRENT}} | 🟢 On Track | `@{{KR_1_1_TEAM}}` |
| **KR 1.2:** {{KR_1_2_DESCRIPTION}} | {{KR_1_2_TARGET}} | {{KR_1_2_BASELINE}} | {{KR_1_2_CURRENT}} | 🟡 At Risk | `@{{KR_1_2_TEAM}}` |

---

### Objective 2: {{OBJECTIVE_2_TITLE}}
> **Focus:** {{OBJECTIVE_2_THEME}} (Owner: `@{{OBJECTIVE_2_OWNER}}`)

| Key Result | Target | Baseline | Current | Pacing | Linked Team |
|:---|:---|:---|:---|:---|:---|
| **KR 2.1:** {{KR_2_1_DESCRIPTION}} | {{KR_2_1_TARGET}} | {{KR_2_1_BASELINE}} | {{KR_2_1_CURRENT}} | 🟢 On Track | `@{{KR_2_1_TEAM}}` |
| **KR 2.2:** {{KR_2_2_DESCRIPTION}} | {{KR_2_2_TARGET}} | {{KR_2_2_BASELINE}} | {{KR_2_2_CURRENT}} | 🟢 On Track | `@{{KR_2_2_TEAM}}` |

---

## 🗓️ Monthly Milestones Breakdown

### Month 1: Foundation & Discovery
- [ ] **M1.1:** Deploy MVP customer discovery interviews and initial landing page.
- [ ] **M1.2:** Scaffolding of core data schemas and automated telemetry.

### Month 2: Acceleration & Funnel Optimization
- [ ] **M2.1:** Launch outbound sales sequence (Hypothesis 1) and SEO programmatic cluster.
- [ ] **M2.2:** Achieve initial target conversion on demo requests.

### Month 3: Scale & Retention
- [ ] **M3.1:** Validate product retention metrics (>40% Day 30).
- [ ] **M3.2:** Finalize enterprise pricing and compliance safeguards.

---

## 🧭 Goal Alignment & Coverage Rules

1. **Zero Orphaned Tasks:** Every P0 and P1 task in `workforces/workstate.md` must link directly to an active KR above.
2. **Zero Orphaned Goals:** Every KR above must have at least one active or scheduled sprint task in flight.
3. **Weekly Sync Review:** Progress and pacing are audited weekly during `/sync --strategy`.
