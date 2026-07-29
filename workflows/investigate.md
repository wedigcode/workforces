---
description: Investigate a performance or error incident on any cloud service. Discovers the service automatically, pulls logs and metrics, classifies the root cause, and outputs a prioritized fix list.
---

# /investigate — Incident Investigation

A general-purpose incident triage workflow. Works with any cloud service that has observable logs and metrics (AWS App Runner, ECS, Lambda, GCP Cloud Run, etc.).

Investigation only. **Do NOT change any configuration, code, or infrastructure.**

---

## Usage

```
/investigate [service-name]            → Investigate recent incident for a service
/investigate --service [arn/url]       → Target a specific service identifier
/investigate --window [30m|1h|6h|24h]  → Set explicit time window (default: auto-detect)
/investigate --push-to-work            → Sync P0/P1 fixes into workstate.md & GH issues
/investigate --postmortem              → Save formal report to workforces/incidents/
```

---

## Steps

### Step 1 — Load stack memory

Read `workforces/memory/incident-investigate.md`.

If it exists, extract any known context for the named service:
- Platform limits (hard timeouts, max concurrency)
- DB scaling behavior
- Known slow endpoints or recurring patterns
- Architecture quirks (workers, crons in web tier, etc.)

Use this context to skip re-discovery steps you already know and to prime your hypothesis before pulling logs.

If the file doesn't exist, create it at the end of the investigation (Step 6).

---

### Step 2 — Load the skill

Read the skill at `skills/incident-investigate/SKILL.md` (or `.agents/skills/incident-investigate/SKILL.md`).

Follow all phases in order:
1. Self-Discovery
2. Time Window
3. Error Investigation
4. Slow Request Analysis
5. Infrastructure Metrics
6. Diagnosis & Report

---

### Step 3 — Self-discovery

Run Phase 1 of the skill. Discover:
- The service ARN / identifier / URL
- Instance config and scaling limits
- Log group names
- Associated database (if any)

---

### Step 4 — Set the time window

Based on any time hint the user provided, set the investigation window per Phase 2.
State the window explicitly before running any queries.

---

### Step 5 — Pull logs and metrics (Log to File Strategy)

Run Phases 3, 4, and 5.

To analyze large volumes of logs without exhausting context window memory:
1. **Redirect raw logs to local scratch storage**: Stream full CLI logs/queries into a workspace temporary file:
   ```bash
   # Example: redirect CloudWatch / GCP / Docker logs to temp file
   aws logs filter-log-events --log-group-name /aws/apprunner/service --start-time 1700000000 > workforces/tmp/incident-[service]-[timestamp].log
   ```
2. **Query and grep the local file**: Use local tools (`grep`, `awk`, `head`, `tail -n 20`, or count patterns) on `workforces/tmp/incident-[service]-[timestamp].log` to isolate specific HTTP 50x status codes, exceptions, stack traces, and peak latency logs.
3. **Present synthesized output**: Show key log evidence snippets and statistical summaries in chat rather than dumping raw multi-hundred line streams.

---

### Step 6 — Diagnose and report

Run Phase 6 of the skill:
1. Output the Summary Table and Root Cause classification (🟥 Bug / 🟧 Config / 🟨 Scale / 🟦 External).
2. List 2–4 prioritized recommendations (P0, P1, P2).
3. **Save Postmortem Artifact**: Save full report to `workforces/incidents/YYYY-MM-DD-[service-name].md`.
4. **Update Memory**: Append new learnings to `workforces/memory/incident-investigate.md` so the next investigation on this service is faster.

---

## Output Format & Handoff

```markdown
## 🔍 Incident Investigation — [service-name]

**Window:** [START] → [END] UTC
**Investigated:** [timestamp]
**Artifact:** workforces/incidents/YYYY-MM-DD-[service-name].md

### Summary
| Field | Finding |
|-------|---------|
| Error type | ... |
| Time window | ... |
| Affected endpoints | ... |
| Max response time | ... |
| Root cause | ... |
| DB involved? | ... |
| Instance health | ... |

### Root Cause
🟥/🟧/🟨 **[Bucket]** — [one-sentence explanation]

[Supporting evidence: key log lines, metric values, timestamps]

### Recommendations
| Priority | Fix | Where | Impact |
|----------|-----|-------|--------|
| P0 | ... | ... | ... |
| P1 | ... | ... | ... |
```

**⏸ PAUSE** — Ask user if they want to push P0/P1 recommendations into `/plan` or `/work` execution state:

- Run `/plan --from-incident workforces/incidents/YYYY-MM-DD-[service].md` to turn fixes into an execution plan
- Or run `/investigate --push-to-work` (appends P0/P1 tasks to `workforces/workstate.md` and triggers GitHub issue creation via `github-project-planning` skill).

---

## Flags

| Flag | Behavior |
|------|----------|
| `--service [arn/url]` | Target a specific cloud service identifier directly, skipping interactive discovery. |
| `--window [30m|1h|6h|24h]` | Explicitly set the investigation time window. |
| `--push-to-work` | Push P0/P1 remediation tasks directly into `workforces/workstate.md` and create tracked GitHub issues. |
| `--postmortem` | Save formal postmortem report to `workforces/incidents/YYYY-MM-DD-[service-name].md`. |
