# Clean Coder Engineering Protocol

- **Programming Task Detection**: Whenever a task involves writing, modifying, refactoring, or testing code (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the agent MUST load and follow the [`clean-coder`](../skills/clean-coder/SKILL.md) skill.
- **Skill Authority**: All software craftsmanship and engineering standards—including AI TDD, method stubs first, symbol deduplication via `code-graph`, function line limits (<= 35 lines as advisory heuristics), method decomposition, PR review verification form, and the pre-handoff quality gate triad—are governed by the `clean-coder` skill.
- **Worktree Isolation for Parallel Agents**: Follow [`git-workflow`](git-workflow.md) and [`agent-parallelization`](../skills/agent-parallelization/SKILL.md) for isolated worktrees (`Workspace: 'share'`) when multiple agents write code concurrently.
- **Pre-Handoff Quality Gate & Advisory Heuristics**: Before declaring any coding task complete or handing code over to the user, the agent MUST run the quality gate to execute automated unit tests, static typechecks, and linters:
  ```bash
  python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
  ```
  *(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*
  Checklist heuristics (e.g. line limits, scoping, DRY suggestions) provide advisory guidance rather than blocking non-zero exit codes. Real test regressions, static type errors, and linter errors on modified code remain strictly blocking.
- **3rd-Party Dependency Security vs. First-Party Code Security**: Upstream dependency audit issues (`npm audit`, `pip-audit`, timeouts) emit non-blocking advisory notices with 7-day retry caching, preventing 3rd-party upstream CVEs from halting progress. The review gate actively audits added diffs for genuine code security (hardcoded secrets, code injection, mutable parameter traps).
- **Legacy Codebases, Static Analysis Tuning & Quality Sprints**:
  - **Scope to Active Diff**: Pre-existing static analysis or lint errors in untouched legacy files outside the current diff do not block task completion.
  - **AI Judgement on Tool Sensitivity**: When working on legacy codebases where static analysis is set too strictly, the AI has discretion to adjust flags or configuration to align with project reality.
  - **Quick Fixes vs. Quality Sprints**: Quick adjacent fixes can be resolved immediately. For widespread pre-existing codebase errors, raise the concern to the user and route a tracking task to `@project-manager` / `task-tracker` for a dedicated **Code Quality Sprint**.
