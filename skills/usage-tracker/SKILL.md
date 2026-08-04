---
name: usage-tracker
description: Real-time token, character, thought, and subagent usage tracking skill for Antigravity workforces.
---

# Usage Tracker Skill

The `usage-tracker` skill enables real-time and historical token and content usage tracking across Antigravity agent sessions and subagents.

## Capabilities

1. **Transcript Log Parsing**: Reads JSONL logs from `~/.gemini/antigravity/brain/` for main agents and subagents.
2. **Thought & Reasoning Extraction**: Tracks model thoughts (`thinking` fields) separately from user inputs and final text responses.
3. **Subagent Monitoring**: Detects subagent invocations (`invoke_subagent`) and tracks parent/child usage.
4. **Automatic Real-time Logging**: Triggered automatically after tool calls via `post_tool_call` hooks in `workforce-usage-plugin`.

## Output Files

- `workforces/usage-log.json`: Comprehensive JSON database of all tracked sessions, character counts, and estimated token metrics.
- `workforces/usage-summary.md`: Formatted Markdown report detailing aggregate usage and active session highlights.

## Manual Execution

To trigger an on-demand update of token and usage metrics:

```bash
python3 skills/usage-tracker/scripts/track_usage.py ./
```
