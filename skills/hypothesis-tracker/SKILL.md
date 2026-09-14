---
name: hypothesis-tracker
description: Formulates, monitors, and evaluates falsifiable business, product, and growth experiments using scientific hypothesis tracking (`workforces/hypotheses/`). Reach for this skill when proposing speculative marketing campaigns, testing growth bets, structuring validation experiments with concrete leading/lagging KPIs and kill thresholds, or reviewing experimental outcomes during strategic standups to decide whether to pivot, kill, or scale.
---

# Hypothesis Tracker

A structured, scientific experimentation framework for workforce teams. Turns growth bets, marketing campaigns, sales outreach, and product features into measurable, falsifiable hypotheses.

---

## 1. Falsifiable Hypothesis Formula

```
"We believe that [Doing Action X] for [Target Audience Y] will achieve [Quantified Outcome Z]
 within [Timeframe T], measured by [Telemetry Metric K].
 If [Kill Threshold Breach], we will [Contingency / Pivot Action]."
```

- **Leading Indicators**: Predictive engagement signals (outreach sends, reply rate %, search impressions, demo starts).
- **Lagging Indicators**: Commercial outcomes (ARR, paid customers acquired, 30-day retention %).

---

## 2. Experimental Lifecycle States

| State | Storage Directory | Lifecycle Meaning |
| :--- | :--- | :--- |
| `draft` | `workforces/hypotheses/draft/` | Proposed experiment, pending budget or telemetry setup. |
| `running` | `workforces/hypotheses/running/` | Active experiment in market with live telemetry logging. |
| `validated` | `workforces/hypotheses/validated/` | Target metrics achieved; proven playbook ready for scale. |
| `invalidated`| `workforces/hypotheses/invalidated/` | Target missed or kill threshold breached; stopped to prevent waste. |
| `pivoted` | `workforces/hypotheses/pivoted/` | Strategy adapted based on customer discovery findings. |

---

## 3. CLI Command Quick Reference

All scripts run via `.agents/skills/hypothesis-tracker/scripts/hypothesis.py` (Fallback: `skills/...`):

| Action | Command Pattern |
| :--- | :--- |
| **Create** | `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --create --title "<Title>" --owner <team> --goal-id "<ID>" --statement "<XYZ>" --timeframe-weeks <W> --kill-threshold "<Kill>" --pivot-plan "<Pivot>" --metrics '<JSON>' --sync-session` |
| **Update Telemetry** | `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --update "<ID>" --current-week <N> --metrics-data "<K1>=<V1>,<K2>=<V2>" --insight "<Learnings>" --sync-session` |
| **Review Queue** | `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --review` (or `--list --status running`) |
| **Kill / Invalidate**| `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --kill "<ID>" --rationale "<Reason>" --sync-session` |
| **Pivot Strategy** | `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --pivot "<ID>" --rationale "<Adjustment>" --sync-session` |
| **Validate & Scale** | `python3 .agents/skills/hypothesis-tracker/scripts/hypothesis.py --validate "<ID>" --rationale "<Success evidence>" --sync-session` |
