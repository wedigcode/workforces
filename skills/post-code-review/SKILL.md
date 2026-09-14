---
name: post-code-review
description: Performs pre-handoff code review and quality verification on git diffs. Validates against a PR-style verification form (DRY, <= 35 lines per function, method decomposition, simplicity, and maintainability), enforces AI pushback on skipped principles, executes the automated quality triad (unit tests, static analysis/type checks, linters), and manages weekly-retried 3rd-party security bypass caching. Reach for this skill immediately after modifying code.
---
# Skill: Pre-Handoff Code Reviewer & Quality Gate

Automated whole-codebase code reviewer and quality gate that audits code modifications, generates a PR-style review checklist, pushes back on skipped principles, executes quality gates, and handles 3rd-party security bypasses with weekly retry intervals.

---

## Capabilities

1. **PR-Style Verification Form**: Automatically evaluates diffs against the 5 core criteria:
   - `[ ] - is it dry` (checks duplicate symbols across code-graph and neighboring class helpers)
   - `[ ] - no new code exceeds 35 lines` (flags functions/methods exceeding max line thresholds)
   - `[ ] - should any new code be in its own method` (detects deeply nested blocks or monolithic branches)
   - `[ ] - is any of it too verbose or can it be simplified?` (identifies redundant boilerplate or verbose returns)
   - `[ ] - code maintainability` (verifies error safety, missing tests, and caller blast radius)
2. **AI Pushback on Skipped Principles**: Flags checklist failures and demands either code remediation or documented technical justification before code handoff (via `--justification "<reason>"`, in-code `# justification: <reason>`, or commit messages). Evasive reasons ('lazy', 'skip') are rejected with pushback.
3. **Candidate Issue Discovery**: Discovered maintainability problems or technical debt outside immediate scope are surfaced with copy-paste `report-task.py` commands.
4. **Resilient 3rd-Party Security Bypass & Remediation**: Dependency security audits (`npm audit`, `pip-audit`, `composer audit`) catch vulnerabilities. The reviewer first executes an automated remediation attempt (`npm audit fix`). If the issue cannot be resolved automatically, learnings are cached in `workforces/memory/security-bypass.json` with a 7-day retry schedule, informing the user with non-blocking notices rather than blocking every session. If later fixed upstream, the system automatically returns to its normal routine.
5. **Quality Triad Execution**: Runs configured unit tests, static analysis/strict type checks (`tsc`, `mypy`, `phpstan`), and linters (`biome`, `eslint`, `ruff`).
6. **Strict Quality Gate**: Blocks handoff if unbypassed critical errors, test regressions, or unaddressed pushback violations exist.

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
