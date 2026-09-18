---
name: clean-coder
description: MANDATORY for any programming, coding, refactoring, bug fixing, or code modification task. Enforces software craftsmanship, Test-Driven Development (TDD) red-green-refactor, method stubs first, symbol deduplication via code-graph, single responsibility and SOLID architecture, <= 35 lines per function, method decomposition, zero error swallowing, PR-style code review verification checklist, AI pushback on skipped rules, weekly-retried 3rd-party security bypass, and pre-handoff quality gates. Reach for this skill whenever writing, editing, or refactoring code, adding new functions or classes, implementing APIs, fixing bugs, or modifying tests before and after code changes.
---
# Skill: Clean Coder

Lean, high-signal engineering workflow enforcing AI TDD, method stubs first, symbol deduplication, and automated PR-style review verification.

---

## Workflow Protocol

### Step 1: Pre-Implementation Graph Check & Method Stubs
1. Run symbol discovery via `code-graph`:
   ```bash
   python3 .agents/skills/code-graph/scripts/graph_indexer.py --query "<method_or_keyword>"
   ```
   *(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py --query "<method_or_keyword>"`)
2. Check `workforces/code-graph.json` or target file helpers. If an existing method performs the required logic or formatting, compose or extend it.
3. **AI TDD First Pass**: Author method signatures, type contracts, and stubs first. Do not jump immediately into full code generation.

### Step 2: Unit Tests First
1. Write unit tests asserting input/output contracts, boundary values, and error conditions against the stubs.
2. Confirm the test fails (Red).
3. Implement minimal clean code to pass (Green).
4. Refactor for clarity and simplicity (Refactor).

### Step 3: Concrete Coding Constraints
- **SOLID, DRY, KISS, YAGNI**: Apply standard design principles cleanly without redundant boilerplate.
- **Function Line Limit (<= 35 lines)**: Keep functions and methods concise and single-purpose (advisory heuristic; methods exceeding this should be considered for decomposition unless contiguous flow is clearer).
- **Method Decomposition**: Extract nested blocks (> 2 levels deep) into helper methods when clarity improves.
- **Simplicity**: Favor clean, idiomatic expressions over verbose intermediate variables or redundant ternary conditionals.
- **Maintainability & Error Safety**: Always catch specific exceptions, attach contextual metadata, and propagate or log. Never swallow errors with empty `catch` or `except` blocks.

### Step 4: Pre-empt the PR Review Verification Form
Review the code against the 5-point verification checklist before declaring completion:
- [x] **is it dry**: No duplicate logic or copy-pasted helpers across files.
- [x] **no new code exceeds 35 lines**: All modified methods evaluated for concise scoping.
- [x] **should any new code be in its own method**: Monolithic or deeply nested code blocks extracted.
- [x] **is any of it too verbose or can it be simplified**: Concise and idiomatic.
- [x] **code maintainability**: Error propagation, contract compatibility, and tests verified.

### Step 5: Post-Hook Verification & Quality Gate
Run the automated review and quality triad:
```bash
# Post-edit heuristic & checklist audit:
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./`)*

```bash
# Pre-handoff quality gate verification:
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*

- **Advisory Heuristics & Pushback**: Checklist heuristics (line length, scoping, verbosity) provide advisory feedback and suggestions rather than blocking execution with non-zero exit codes.
- **Quality Triad Enforcement**: Unit tests, typechecks, and linters executed via `--run-checks` remain strictly blocking quality gates.
- **Security Bypass**: Third-party or deprecation issues that cannot be resolved automatically are recorded to `workforces/memory/security-bypass.json` for weekly re-check without blocking every session.
- **Discovered Issues**: Non-blocking issues or candidate tech debt surfaced by the reviewer can be recorded via `.agents/skills/task-tracker/scripts/report-task.py` (Fallback: `python3 skills/task-tracker/scripts/report-task.py`).
- **Autonomous Git Workflow & PR Discipline**: Follow [`git-workflow`](../../rules/git-workflow.md) and [`agent-parallelization`](../agent-parallelization/SKILL.md) for worktree isolation (`Workspace: 'share'`) and stacked PRs via `gh-stack`.
