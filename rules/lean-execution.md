---
trigger: always_on
---

# Lean Execution & Satisficing Protocol

This protocol enforces high-velocity execution, bounded investigation, and strict anti-distraction guardrails across all agent workflows.

---

## 1. Stop Condition & Satisficing Rule
- **Satisficing Trigger**: The instant you possess sufficient evidence, context, or code references to answer the user's inquiry or execute the targeted fix, **STOP searching immediately**.
- **No Speculative Over-Searching**: Do NOT execute additional "just-in-case" searches, secondary verifications, or exploratory queries once the core solution or answer is identified. If confidence in the solution exceeds 90%, proceed directly to resolution or response.

## 2. Zero Unprompted Transcript Hunting
- **Strict Prohibition**: NEVER read, grep, or search past conversation transcripts (`transcript.jsonl` or `transcript_full.jsonl`) unless the user explicitly requests historical retrieval (e.g., *"recall what we discussed yesterday"*, *"find the message from our last session"*).
- **Context Primacy**: Rely strictly on active files, direct code references, and provided prompt context for real-time task execution.

## 3. Strict Scope & Blast Radius Confinement
- **Localized Focus**: When assigned to debug, inspect, or modify a specific component (e.g., a helper function, a single template, a localized utility):
  - Confine investigation strictly to the target file and its direct inputs/outputs.
  - Do NOT proactively traverse or inspect adjacent database tables, controllers, background job queues, or framework configuration files unless a concrete runtime failure or unhandled import directly demands it.
- **Hypothesis-Driven Lookups**: Every tool call must test a specific, falsifiable hypothesis. Never perform generic browsing or open-ended scanning of database tables or directories.

## 4. Triage & Bugfix Fast Path (Exemption from Plan Ceremonies)
- **Fast Path Criteria**: Localized bug fixes, targeted helper modifications, single-file edits (< 50 lines), and direct Q&A are categorized as **Fast Path tasks**.
- **Ceremony Bypass**: Fast Path tasks are strictly exempt from multi-file implementation plans, pre-plan AST codebase audits, and roadmap ceremonies. Diagnose, patch, test, and respond immediately.
