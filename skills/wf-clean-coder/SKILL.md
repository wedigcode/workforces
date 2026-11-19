---
name: wf-clean-coder
description: MANDATORY for any programming, coding, refactoring, bug fixing, or code modification task. Enforces software craftsmanship, a test written or updated and run for every behavior change or bug fix, searching for existing similar code before adding new functions, the simplest design that works with a rule of three for duplication, shallow control flow, a soft ~50-60 line function limit with extraction only for nameable, reused or separately tested blocks, zero error swallowing, PR-style code review verification checklist with advisory feedback, weekly-retried 3rd-party security bypass, and pre-handoff quality gates. Reach for this skill whenever writing, editing, or refactoring code, adding new functions or classes, implementing APIs, fixing bugs, or modifying tests before and after code changes.
---
# Skill: Clean Coder

Lean, high-signal engineering workflow: reuse before you write, test what you change, and verify against a PR-style review checklist.

---

## Workflow Protocol

### Step 1: Pre-Implementation Analog, Architecture & Blast Radius Check
1. **Architecture Index & Existing Analog First**: If `<repo>/docs/index.md` exists, inspect it and matching `docs/architecture/*.md` cards (`## Key Dependencies & Blast Radius`, `## Constraints, Invariants & Gotchas`, `## Test Coverage & Verification`) first. For any task touching domain events, subscribers, queues, webhooks, 3rd-party services, or env/IaC config, find **at least 1 existing analog** in the codebase so you reuse or group into existing dispatcher/subscriber flows instead of scattering duplicate notifications.
2. **Pre-Edit Blast Radius Protocol (Before Changing Public Contracts or Refactoring)**:
   - Run on-demand `python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --impact <file>` (Fallback: `skills/wf-doc-generator/scripts/scaffold_repo_okf.py`) to inspect matching OKF cards, direct importers, matching tests, and Git co-changed files.
   - Run targeted `grep_search` on the module import path and changed exported symbol names.
   - Verify exact caller compatibility via real stack typecheckers and tests (`tsc`, `mypy`, `phpstan`, `go vet`, `cargo check`) in `post_code_reviewer.py --run-checks --strict`.
3. **Search for Similar Code Before Adding Functions**: Before writing a new function, class or helper, search for existing ones with similar names or purpose using `grep_search` (name fragments, synonyms such as `format`/`render`/`to_string`) and `list_dir` (likely `utils`, `helpers`, `lib`, `services` folders). Reuse or extend what exists instead of adding a near-duplicate.

### Step 2: Test What You Change
For every behavior change or bug fix, write or update a test that covers it and run it before declaring the task done. For a bug fix, the test should exercise the failing case. Pure refactors, renames, docs and config-only changes rely on the existing suite passing.

### Step 3: Concrete Coding Constraints
- **Simplest Design That Works**: Write the most direct code that solves the task. Do not add a new interface, abstract base class, factory, or configuration layer until there are two real, current uses for it; one concrete implementation is not a reason to abstract.
- **Rule of Three for Duplication**: Copying a small piece of logic twice is acceptable. Extract a shared helper on the third copy, or earlier only when the copies must stay in sync (e.g. the same validation or business rule). Do not merge code that merely looks similar but changes for different reasons.
- **Function Length (soft limit ~50–60 lines)**: Prefer functions that fit on one screen, but length alone is not a reason to split. Extract a block into its own function only when (a) its purpose can be named in one short phrase, (b) it is reused, or (c) it is worth testing on its own. Never extract just to meet a line count, and keep a sequential flow (step 1, step 2, step 3) in one function that reads top to bottom rather than scattering it across single-use helpers the reviewer has to jump between.
- **Shallow Control Flow**: Keep nesting to about 3 levels inside a function. Flatten first with early returns, guard clauses, and `continue`; extract a nested block only under the same criteria as above (nameable, reused, or tested on its own).
- **Simplicity**: Favor clean, idiomatic expressions and drop pointless constructs (`x ? true : false`, `if cond: return True else: return False`). Well-named intermediate variables that explain a step are encouraged; do not collapse them into dense one-liners.
- **Maintainability & Error Safety**: Always catch specific exceptions, attach contextual metadata, and propagate or log. Never swallow errors with empty `catch` or `except` blocks.
- **No `"production"` Fallbacks & IaC Env Parity**: NEVER hardcode `"prod"`, `"production"`, or `"live"` as fallback defaults in code. Whenever adding, renaming, or removing an environment variable or hardcoded secret/config value, inspect deployment configs (`template.yaml`, `template.yml`, `samconfig.toml`, `serverless.yml`, `.env.example`) for parity across all environments. Treat missing deployment config as a config/runbook fix (**Config Outage != Code Workaround**).
- **Concise Boundary Docblocks**: New services, event subscribers, and integration handlers should carry a short (2–4 line) class/module docblock explaining role, events handled, and external config assumptions, paired with living `docs/architecture/*.md` OKF cards where cross-service contracts exist.

### Step 4: Pre-empt the PR Review Verification Form
Review the code against the 5-point verification checklist before declaring completion:
- [x] **is it dry**: No logic copied three or more times, and no re-implementation of an existing helper.
- [x] **no new code exceeds 60 lines**: Longer functions are fine when they read as one top-to-bottom flow; split only along the extraction criteria above.
- [x] **is any function hard to follow**: Control flow stays shallow (early returns first); no function a reviewer must read twice.
- [x] **is any of it too verbose or can it be simplified**: Concise and idiomatic.
- [x] **code maintainability**: Error propagation, contract compatibility, and tests verified.

### Step 5: Review & Quality Gate
Run the reviewer once before handing off. The `--run-checks --strict` run produces the same checklist audit as a plain run and also executes the project's tests, typechecks and linters:
```bash
python3 .agents/skills/wf-post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
```
*(Fallback: `python3 skills/wf-post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*

- **Advisory Heuristics & Pushback**: Checklist heuristics (line length, scoping, verbosity) provide advisory feedback and suggestions rather than blocking execution with non-zero exit codes.
- **Quality Triad Enforcement**: Unit tests, typechecks, and linters executed via `--run-checks` remain strictly blocking quality gates on modified code. Pre-existing errors in untouched legacy files are reported as non-blocking technical debt.
- **Legacy Codebases & Static Analysis Tuning**: When working on older repositories where static analysis is set too aggressively, the agent exercises judgement to adjust settings or scope checks. Quick localized fixes should be addressed immediately; widespread debt is raised to the user and tracked for a **Code Quality Sprint** via `report-task.py`.
- **Security & Bug Pattern Review**: The review gate audits modified diffs for genuine code security (hardcoded credentials, injection vulnerabilities, common bug traps). Third-party upstream library CVEs (`npm audit`, `pip-audit`) are recorded to `workforces/memory/security-bypass.json` as non-blocking advisory notices with 7-day retry intervals.
- **Discovered Issues**: Non-blocking issues or candidate tech debt surfaced by the reviewer can be recorded via `.agents/skills/wf-task-tracker/scripts/report-task.py` (Fallback: `python3 skills/wf-task-tracker/scripts/report-task.py`).
- **Autonomous Git Workflow & PR Discipline**: Follow [`wf-git-workflow`](../../rules/wf-git-workflow.md) and [`wf-agent-parallelization`](../wf-agent-parallelization/SKILL.md) for worktree isolation (`Workspace: 'share'`) and stacked PRs via `gh-stack`.
