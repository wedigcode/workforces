---
id: "{{ID}}"
title: "{{TITLE}}"
status: "{{STATUS}}"
owner: "{{OWNER}}"
supporting_teams:
{{SUPPORTING_TEAMS}}
goal_id: "{{GOAL_ID}}"
goal_title: "{{GOAL_TITLE}}"
timeframe_weeks: {{TIMEFRAME_WEEKS}}
current_week: {{CURRENT_WEEK}}
started_at: "{{STARTED_AT}}"
updated_at: "{{UPDATED_AT}}"
target_completion: "{{TARGET_COMPLETION}}"
session_id: "{{SESSION_ID}}"
session_file: "{{SESSION_FILE}}"
recommended_tools: {{RECOMMENDED_TOOLS}}
delegated_to: "{{DELEGATED_TO}}"
github_labels: {{GITHUB_LABELS}}
kill_threshold: "{{KILL_THRESHOLD}}"
pivot_plan: "{{PIVOT_PLAN}}"
metrics:
{{METRICS_YAML}}
---

# {{ID}}: {{TITLE}}

**Owner:** `@{{OWNER}}` | **Status:** `{{STATUS}}` (Week {{CURRENT_WEEK}} of {{TIMEFRAME_WEEKS}})  
**Related Goal:** `{{GOAL_ID}}` — {{GOAL_TITLE}}  
**Timeframe:** {{TIMEFRAME_WEEKS}} weeks (Target: {{TARGET_COMPLETION}})  
**Origin Session:** [{{SESSION_FILE_BASENAME}}]({{SESSION_FILE_LINK}})  
{{TOOL_DELEGATION_LINE}}
---

## 🔬 Scientific Hypothesis Statement

> {{STATEMENT}}

---

## 📊 Progress & Pacing Telemetry

| Metric | Type | Baseline | Target | Current | Progress | Pacing |
|:---|:---|:---|:---|:---|:---|:---|
{{METRICS_TABLE}}

---

## 🛑 Kill Criteria & Pivot Contingency

- **Kill Threshold:** {{KILL_THRESHOLD}}
- **Contingency / Pivot Plan:** {{PIVOT_PLAN}}

---

## 💡 Emerging Insights, Adjustments & Decisions

- **{{STARTED_AT_SHORT}}:** Hypothesis initialized and set to `{{STATUS}}`.
{{DECISIONS_LOG}}
