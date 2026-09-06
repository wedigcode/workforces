---
trigger: always_on
---

# Clean Coder Engineering Rules

These engineering rules govern all code generation, refactoring, and execution within workforce workflows.

---

## 0. Programming Task Detection & Mandatory Pre-Hooks
- **Task Pre-Check**: Whenever a prompt or workflow step involves writing, refactoring, or modifying code (triggering tools like `write_to_file`, `replace_file_content`, `multi_replace_file_content`), the agent MUST treat it as a **Programming Task**.
- **Mandatory Pre-Hook Execution**: Before modifying any code, the agent MUST automatically invoke the `code-graph` symbol discovery (`python3 .agents/skills/code-graph/scripts/graph_indexer.py --query <target_name>` or `skills/code-graph/scripts/graph_indexer.py --query <target_name>`) and load `skills/clean-coder` guidelines into active context. (Note: Use optional `--target-dir <path>` if orchestrating a child project directory outside workforce root).
- **Fail-Safe**: If unsure whether a task is a programming task, evaluate: *Will this change modify application logic, functions, classes, or tests?* If YES, execute the pre-hook lookup immediately.

---

## 1. Deduplication & Existing Method Discovery
- **Check Before Create**: BEFORE creating any function, method, helper, or class, the agent MUST check if a suitable method already exists in the codebase.
- **Pre-Plan Codebase Audit**: BEFORE populating an `implementation_plan.md` or proposing new architectural additions, the agent MUST execute codebase searches (`code-graph`, `grep_search`, `list_dir`) and document all audited symbols, tables, utilities, existing vs missing capabilities under `## Existing Codebase Audit Findings`.
- **Symbol Index Lookup**: Use the `code-graph` tool (`python3 .agents/skills/code-graph/scripts/graph_indexer.py --query <name>`), `grep_search`, or the OKF catalog under `workforces/knowledge-catalog/` to verify existence.
- **Target Class & Neighbor Method Inspection**: BEFORE writing a new method inside an existing class or module, the agent MUST inspect all existing public and static methods in that target file. If an existing method performs type conversion, sanitization, or formatting (e.g. `convertNumber`), the new method MUST reuse/compose it rather than reimplementing low-level regex, parsing, or type-casting logic.
- **Reuse and Extend**: If a function with similar capability exists, reuse or refactor it cleanly rather than introducing duplicate implementations.

## 2. Test-Driven Development (TDD) Mindset
- **Expectation First**: Define test cases, expected inputs/outputs, and contract boundaries before writing implementation logic.
- **Fail First Verification**: When adding features or fixing bugs, ensure a failing test or assertion exists to demonstrate the bug/gap before writing code to fix it.
- **Refactor Safely**: Refactor code only while tests pass.

## 3. SOLID, DRY, KISS & Anti-Over-Engineering Principles
- **Single Responsibility (SRP)**: Each function/class must do ONE thing and do it exceptionally well. Keep functions small (ideally <30 lines).
- **Open/Closed (OCP)**: Design modules for extension without modifying core existing contracts.
- **Liskov Substitution (LSP)**: Derived structures/types must remain fully compatible with base abstractions.
- **Interface Segregation (ISP)**: Prefer small, cohesive interfaces/types over monolithic ones.
- **Dependency Inversion (DIP)**: Depend upon abstractions, not concrete implementations.
- **DRY (Don't Repeat Yourself)**: Zero copy-paste logic. Extract repeated logic into clean, reusable utilities.
- **KISS (Keep It Simple, Stupid)**: Avoid over-engineering. Pick the simplest architecture that satisfies all requirements cleanly.
- **Diff Compression Check**: Prior to completing code edits, evaluate whether the new or modified function can be written in <50% of the lines by composing existing class methods.

## 4. Mandatory Pre-Handoff Quality Gate & Self-Review
- **Automated Post-Edit Review Execution**: Immediately after modifying any code file (via `write_to_file`, `replace_file_content`, or `multi_replace_file_content`), the agent MUST execute the post-code review audit:
  ```bash
  python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./
  ```
  *(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./` — automatically resolves target project root from `workrules.md`/`workstate.md` or `WORKFORCE_TARGET_DIR`).*
- **Pre-Handoff Quality Gate Triad (MANDATORY BEFORE CODE HANDOFF)**:
  Before declaring any coding task complete or handing code over to the user, the agent MUST execute the full quality gate triad:
  ```bash
  python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
  ```
  This automatically runs:
  1. **Unit Tests**: Full test suite execution with zero regressions.
  2. **Static Analysis & Typecheck**: Strict type checking (`tsc --noEmit`, `mypy --strict`, `phpstan`) with zero `any` bypasses.
  3. **Code Styling & Linting**: Linter compliance (`biome check`, `eslint`, `ruff`, `pint`).
  4. **Security & Dependency Audit**: Vulnerability scans (`npm audit`, `pip-audit`, `composer audit`) on modified manifests.
- **Zero-Handoff on Failing Gates Rule**: If any unit test fails, static analysis detects type errors, linters report violations, or security audits flag vulnerabilities, **THE AGENT MUST NOT HAND OVER CODE OR DECLARE WORK COMPLETE**. The agent must diagnose, remediate, and re-verify all errors immediately before concluding the turn.
- **Mutation-Resilient Testing**: Unit tests must feature assertions that test domain boundaries and state changes (designed to kill mutations) rather than shallow line-coverage execution.

## 5. Naming & Self-Documenting Code
- **Expressive Naming**: Use intent-revealing names for variables, methods, and classes (e.g. `calculateMonthlyTaxableIncome` instead of `calcTax`).
- **Clean Comments**: Comments must explain *why* non-obvious code decisions were made, NOT *what* standard code line does. Let clean code describe *what*.
- **No Swallowed Errors**: NEVER write empty `catch` or `except` blocks, silence exceptions with dummy fallbacks, or ignore promise rejections. Log, annotate, or propagate errors gracefully.

## 6. Framework Installation & Scaffolding Safeguard (Stop & Prompt User Rule)
- **No Manual Boilerplate Re-invention**: If an automated framework installation or package scaffolding command (e.g. `npx create-next-app`, `npm create vite@latest`, `django-admin startproject`, `poetry new`, `cargo new`, `firebase init`, `amplify init`, `docker build`) fails, blocks, requires interactive input, or hits sandbox network barriers:
  - **The agent MUST NEVER attempt to manually code or hand-write framework internals, complex config files, or node_modules from scratch.**
  - **STOP EXECUTION IMMEDIATELY.**
  - Provide the exact shell command(s) for the user to run directly in their local terminal.
  - Instruct the user to confirm once the command finishes, then resume automated workflow execution cleanly using the official scaffolded files.

## 7. Multi-Agent Git Safety & Stacked PR Discipline (`agent-parallelization`)
- **Worktree Isolation for Parallel Agents**: Whenever multiple agents write or test code concurrently, each agent MUST operate in an isolated Git worktree (`Workspace: 'share'`). Agents must NEVER modify the root working tree simultaneously.
- **Stacked PR Atomic Layer Rule**: In stacked PRs (`gh stack`), every intermediate layer MUST compile and pass its own unit tests in isolation before the next layer is stacked. Never commit broken intermediate layers.
- **Cascade Rebase with `git rerere`**: When trunk moves or a base layer is revised, run `gh stack sync` to cascade-rebase the stack. Ensure `git rerere` is enabled to automatically remember and apply conflict resolutions across downstream layers.


