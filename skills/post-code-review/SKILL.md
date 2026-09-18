---
name: post-code-review
description: Performs pre-handoff code review and quality verification on git diffs. Analyzes git diff after editing code to detect broken function contract signatures, duplicate utilities, and missing tests. Evaluates against a PR-style verification form (DRY, advisory line limits, method decomposition, simplicity, and maintainability), surfaces advisory feedback on design heuristics, executes the automated quality triad (unit tests, static analysis/type checks, linters), and manages weekly-retried 3rd-party security bypass caching. Reach for this skill immediately after modifying code.
---
# Skill: Pre-Handoff Code Reviewer & Quality Gate

Automated whole-codebase code reviewer and quality gate that audits code modifications, generates a PR-style review checklist, surfaces advisory guidance on design heuristics, executes quality gates, and handles 3rd-party security bypasses with weekly retry intervals.

---

## Capabilities

1. **PR-Style Verification Form**: Automatically evaluates diffs against the 5 core criteria:
   - `[ ] - is it dry` (checks duplicate symbols across code-graph and neighboring class helpers)
   - `[ ] - no new code exceeds 35 lines` (flags functions/methods exceeding max line thresholds as advisory guidance)
   - `[ ] - should any new code be in its own method` (detects deeply nested blocks or monolithic branches)
   - `[ ] - is any of it too verbose or can it be simplified?` (identifies redundant boilerplate or verbose returns)
   - `[ ] - code maintainability` (verifies error safety, missing tests, and caller blast radius)
2. **Advisory Review Feedback & Heuristics**: Surfaces checklist recommendations and decomposition suggestions as advisory guidance, encouraging clean modular design without forcing artificial code fragmentation or blocking non-zero exits.
3. **Candidate Issue Discovery**: Discovered maintainability problems or technical debt outside immediate scope are surfaced with copy-paste `report-task.py` commands.
4. **Resilient 3rd-Party Security Bypass & Remediation**: Dependency security audits (`npm audit`, `pip-audit`, `composer audit`) catch vulnerabilities. The reviewer first executes an automated remediation attempt (`npm audit fix`). If the issue cannot be resolved automatically, learnings are cached in `workforces/memory/security-bypass.json` with a 7-day retry schedule, informing the user with non-blocking notices rather than blocking every session. If later fixed upstream, the system automatically returns to its normal routine.
5. **Quality Triad Execution**: Runs configured unit tests, static analysis/strict type checks (`tsc`, `mypy`, `phpstan`), and linters (`biome`, `eslint`, `ruff`).
6. **Strict Quality Gate & Blast Radius Scoping**: Blocks handoff if genuine quality gate failures occur on modified code (test regressions, linter errors, typecheck failures, or hardcoded secrets). Third-party dependency CVEs emit non-blocking advisory notices with 7-day retry caching, and pre-existing static analysis debt in untouched legacy files is routed to candidate tasks for a Code Quality Sprint rather than blocking the active task.

---

## Execution Commands

### 1. Post-Edit Heuristic & PR Verification Check
```bash
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./`)*

### 2. Pre-Handoff Quality Gate Verification (MANDATORY BEFORE COMPLETION)
```bash
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*
