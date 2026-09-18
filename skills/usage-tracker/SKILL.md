---
name: usage-tracker
description: Monitors, logs, and analyzes token consumption, thinking steps, and subagent invocations across Antigravity agent sessions (`workforces/tmp/usage-log.json`). Reach for this skill when auditing LLM resource utilization, evaluating the token cost of complex workflows, diagnosing prompt bloat and heavy tool outputs, or generating real-time turn summaries during execution.
---
# Usage Tracker Skill

The `usage-tracker` skill enables real-time and historical token and content usage tracking across Antigravity agent sessions and subagents.

## Capabilities

1. **Transcript Log Parsing**: Reads JSONL logs from `~/.gemini/antigravity/brain/` for main agents and subagents.
2. **Thought & Reasoning Extraction**: Tracks model thoughts (`thinking` fields) separately from user inputs and final text responses.
3. **Subagent Monitoring**: Detects subagent invocations (`invoke_subagent`) and tracks parent/child usage.
4. **On-Demand & Event Logging**: Invoked via manual execution or workflow commands to update token and character consumption records.

## Output Files

- `workforces/tmp/usage-log.json`: Comprehensive JSON database of all tracked sessions, character counts, and estimated token metrics (gitignored under `workforces/tmp/`).
- `workforces/usage-summary.md`: Formatted Markdown report detailing aggregate usage and active session highlights.

## Manual Execution

To trigger an on-demand update of token and usage metrics:

```bash
python3 .agents/skills/usage-tracker/scripts/track_usage.py ./
```
*(Fallback: `python3 skills/usage-tracker/scripts/track_usage.py ./`)*
