---
trigger: always_on
---

# Clean Coder Engineering Rules

These engineering rules govern all code generation, refactoring, and quality verification within workforce workflows.

---

## 0. Programming Task Detection & Mandatory Pre-Hooks
- **Task Pre-Check**: Whenever a prompt or workflow involves writing, refactoring, or modifying code (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the agent MUST treat it as a **Programming Task**.
- **Mandatory Pre-Hook Execution**: Before modifying any code, the agent MUST run symbol discovery (`python3 skills/code-graph/scripts/graph_indexer.py --query <target_name>`) and review active guidelines.
- **Fail-Safe**: If unsure whether a task is programming: evaluate *Will this change modify application logic, functions, classes, or tests?* If YES, execute the pre-hook lookup immediately.

---

## 1. AI TDD & Method Stubs First
- **Pre-Implementation Graph Check**: Before writing any new function, method, helper, or class, search `code-graph` (`graph_indexer.py --query <name>`) or the symbol catalog to verify if an existing implementation or helper already exists.
- **First Pass (Stubs & Contracts Only)**: Define the contract, type signatures, and method stubs first. Do not jump straight to full implementation.
- **Unit Tests First**: Write unit tests verifying input/output contracts and boundary edge cases before full implementation. Minimum requirement: test happy path and failure/edge cases.

---

## 2. Core Design Principles & Concrete Constraints
Follow standard engineering design principles: **SOLID, DRY, KISS, YAGNI, and Clean Architecture**. Do not reinvent these well-known patterns; enforce the following concrete constraints:

- **DRY (Don't Repeat Yourself)**: Zero copy-paste logic. Reuse existing class helpers and indexed symbols rather than reimplementing low-level parsing or helpers.
- **Function Line Limit (<= 35 lines)**: Keep functions and methods focused and concise. No newly added or refactored function should exceed 35 lines.
- **Single Responsibility & Method Decomposition**: If a code block contains deeply nested conditionals/loops (> 2 levels deep) or distinct sub-steps, extract them into focused private/helper methods.
- **Simplicity & Verbosity**: Avoid redundant boilerplate, intermediate one-use variables, or verbose conditional returns. Keep implementations idiomatic and lean.
- **Code Maintainability & Error Safety**: NEVER swallow errors with empty `catch {}` or `except: pass` blocks. Enrich exceptions with contextual metadata and propagate or log them gracefully.

---

## 3. Pre-Empting the PR Review Verification Form
The developer/agent MUST pre-empt what the post-hook reviewer will validate. Before submitting code for handoff, ensure the code satisfies each check of the review template:
- `[x] - is it dry`
- `[x] - no new code exceeds 35 lines`
- `[x] - should any new code be in its own method`
- `[x] - is any of it too verbose or can it be simplified?`
- `[x] - code maintainability`

---

## 4. Post-Hook Verification & AI Pushback Protocol
- **Automated Post-Hook Review**: Immediately after editing code, execute the post-code review audit:
  ```bash
  python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./
  ```
- **AI Pushback on Skipped Principles**:
  - The post-hook reviewer evaluates the changes against the PR review verification form.
  - If any principle is violated or skipped without a documented justification, the reviewer pushes back, demands an explanation, and requires remediation before code handoff.
- **Discovered Problems & Backlog Tracking**:
  - When non-blocking code smells, maintainability issues, or tech debt outside the immediate task scope are discovered, the reviewer notes them and surfaces candidate backlog items so an issue can be logged (`skills/task-tracker/scripts/report-task.py`).

---

## 5. Third-Party Security & Deprecation Bypass with Weekly Retry
- **Security & Deprecation Audits**: Vulnerability scans (`npm audit`, `pip-audit`, `composer audit`) run whenever dependency manifests are touched.
- **3rd-Party & Deprecation Resilience**:
  - Some security issues or deprecations stem from 3rd-party/transitive dependencies outside developer control.
  - The reviewer makes a remediation attempt (e.g. `npm audit fix`).
  - If the issue cannot be resolved automatically, the learning is recorded in `workforces/memory/security-bypass.json` with a 7-day retry schedule, and the user is informed with a non-blocking notice.
  - While bypassed, the check does not repeatedly block every session. Once per week, the reviewer re-evaluates the bypassed issue; if resolved upstream, standard validation resumes automatically.

---

## 6. Pre-Handoff Quality Gate Triad (MANDATORY BEFORE CODE HANDOFF)
Before declaring any coding task complete or handing code over to the user, run the strict quality gate:
```bash
python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
```
All unit tests must pass, static analysis / type checks must have zero errors, linters must pass, and unbypassed security audits must be clean.

---

## 7. Autonomous Git Workflow & PR Discipline
- **Worktree Isolation for Parallel Agents**: Follow [`git-workflow`](git-workflow.md) and [`agent-parallelization`](../skills/agent-parallelization/SKILL.md) for deterministic commit milestones, worktree isolation, and opening pull requests for code review.

