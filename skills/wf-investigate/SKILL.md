---
name: wf-investigate
description: Conducts structured, read-only incident triage and root-cause investigation across cloud services (AWS App Runner, ECS, Lambda, GCP Cloud Run, Kubernetes). Reach for this skill or trigger it when diagnosing production outages, service crashes, elevated error rates, memory exhaustion, or network timeouts, extracting relevant telemetry from cloud logs and metrics, and generating incident postmortems without modifying live infrastructure.
---
# Skill: /wf-investigate — Incident Investigation

A general-purpose incident triage workflow and cloud investigation engine. Works with any cloud service that has observable logs and metrics (AWS App Runner, ECS, Lambda, GCP Cloud Run, etc.).

Investigation only. **Do NOT change any configuration, code, or infrastructure.**

---

## Usage

```
/wf-investigate [service-name]            → Investigate recent incident for a service
/wf-investigate --service [arn/url]       → Target a specific service identifier
/wf-investigate --window [30m|1h|6h|24h]  → Set explicit time window (default: auto-detect)
/wf-investigate --push-to-work            → Sync P0/P1 fixes into workstate.md & GH issues
/wf-investigate --postmortem              → Save formal report to workforces/incidents/
```

---

## Investigation Phases

Follow all 6 phases in order:

### Phase 1 — Self-Discovery
Discover target service infrastructure parameters:
- The service ARN / identifier / URL
- Instance configuration and scaling limits (max concurrency, CPU/memory limits)
- Log group names and monitoring streams
- Associated databases or caching layers (if any)

### Phase 2 — Set Time Window
Based on any time hint the user provided, set the investigation window (e.g. past 30m, 1h, 6h, 24h). State the window explicitly in UTC before querying logs.

### Phase 3 — Error Investigation (Log to File Strategy)
To analyze large volumes of logs without exhausting context window memory:
1. **Redirect raw logs to local scratch storage**: Stream full CLI logs/queries into a workspace temporary file:
   ```bash
   # Example: redirect CloudWatch / GCP / Docker logs to temp file
   aws logs filter-log-events --log-group-name /aws/apprunner/service --start-time 1700000000 > workforces/tmp/incident-[service]-[timestamp].log
   ```
2. **Query and grep the local file**: Use local tools (`grep`, `awk`, `head`, `tail -n 20`, or count patterns) on `workforces/tmp/incident-[service]-[timestamp].log` to isolate specific HTTP 50x status codes, exceptions, stack traces, and peak latency logs.
3. **Present synthesized output**: Show key log evidence snippets and statistical summaries in chat rather than dumping raw multi-hundred line streams.

### Phase 4 — Slow Request Analysis
- Identify requests breaching p95/p99 latency thresholds or platform timeouts (e.g. 15s/30s gateway cutoffs).
- Check whether slow requests correlate with specific endpoints, database query locks, or external network calls.

### Phase 5 — Infrastructure Metrics
- Audit instance health: CPU utilization spikes, memory saturation / OOM killer events, active connection pool limits, and container restarts.

### Phase 6 — Diagnosis & Report
1. Output the Summary Table and Root Cause classification:
   - 🟥 **Bug** (unhandled exception, null pointer, syntax/runtime failure)
   - 🟧 **Config** (missing env var, wrong IAM policy, invalid connection string)
   - 🟨 **Scale** (connection pool exhaustion, OOM, CPU throttling, concurrency limit reached)
   - 🟦 **External** (third-party API outage, DNS failure, upstream service degradation)
2. List 2–4 prioritized recommendations (P0, P1, P2).
3. **Save Postmortem Artifact**: Save full report to `workforces/incidents/YYYY-MM-DD-[service-name].md`.
4. **Update Memory**: Append new learnings to `workforces/memory/incident-investigate.md` so the next investigation on this service is faster.

---

## Detailed Step Protocol

### Step 1 — Load Stack Memory

Read `workforces/memory/incident-investigate.md`.

If it exists, extract any known context for the named service:
- Platform limits (hard timeouts, max concurrency)
- DB scaling behavior
- Known slow endpoints or recurring patterns
- Architecture quirks (workers, crons in web tier, etc.)

Use this context to skip re-discovery steps you already know and to prime your hypothesis before pulling logs.

If the file doesn't exist, create it at the end of the investigation (Phase 6).

---

### Step 2 — Execute Self-Discovery (Phase 1)

Discover service identifier, ARN, container limits, and log group names.

---

### Step 3 — Define Time Window (Phase 2)

State start and end timestamps in UTC before initiating log retrieval.

---

### Step 4 — Log Triage & Metric Pull (Phases 3, 4, 5)

Stream raw logs to `workforces/tmp/incident-[service]-[timestamp].log` and grep for errors, slow endpoints, and container metrics.

---

### Step 5 — Diagnosis & Postmortem Artifact Generation (Phase 6)

Compile the findings and postmortem report.

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
🟥/🟧/🟨/🟦 **[Bucket]** — [one-sentence explanation]

[Supporting evidence: key log lines, metric values, timestamps]

### Recommendations
| Priority | Fix | Where | Impact |
|----------|-----|-------|--------|
| P0 | ... | ... | ... |
| P1 | ... | ... | ... |
```

**⏸ PAUSE** — Ask user if they want to push P0/P1 recommendations into `/wf-plan` or active execution state:

- Run `/wf-plan --from-incident workforces/incidents/YYYY-MM-DD-[service].md` to turn fixes into an execution plan
- Or run `/wf-investigate --push-to-work` (appends P0/P1 tasks to `workforces/workstate.md` and triggers GitHub issue creation via `skills/github-project-planning/SKILL.md`).

---

## Flags

| Flag | Behavior |
|------|----------|
| `--service [arn/url]` | Target a specific cloud service identifier directly, skipping interactive discovery. |
| `--window [30m|1h|6h|24h]` | Explicitly set the investigation time window. |
| `--push-to-work` | Push P0/P1 remediation tasks directly into `workforces/workstate.md` and create tracked GitHub issues. |
| `--postmortem` | Save formal postmortem report to `workforces/incidents/YYYY-MM-DD-[service-name].md`. |
