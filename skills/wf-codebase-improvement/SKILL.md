---
name: wf-codebase-improvement
description: >-
  Audits, refactors, and elevates repository quality across five core engineering pillars: Cleanup (dead code, unused deps), Performance (bottlenecks, query efficiency), Security (vulnerabilities, hardcoded secrets), Code Health (type safety, architectural debt), and Testing (coverage gaps). Reach for this skill during proactive hygiene sweeps, post-feature cleanup, or when investigating degraded system performance and accumulated technical debt.
---
# Skill: Continuous Codebase Improvement & Hygiene

Structured domain capability for auditing, maintaining hygiene, and upgrading code quality across five core engineering pillars. Combines automated codebase cleanliness audits and knowledge graph maintenance with continuous refactoring and PR reviews.

---

## Triggering & Execution

This skill is invoked autonomously by `@wf-programmer` or coordinators, or directly through natural language:

### Prompt Triggers
- *"Clean up the codebase and refresh knowledge"*
- *"Audit code quality across the 5 pillars"*
- *"Find dead code and unreferenced symbols"*
- *"Audit performance bottlenecks and memory leaks"*
- *"Check security: input validation and hardcoded secrets"*
- *"Review open PRs and refactoring tasks"*

### Coordinator & Standup Invocations
- **Via `/wf-sync`**: Standups surface pending debt and recommend hygiene sweeps.
- **Standup & Pre-Commit Sweeps**: Automatically executed prior to major architectural refactoring.
- **Autonomous Execution**: Route refactoring tasks directly to `@wf-programmer` subagents via `wf-agent-parallelization` isolated worktrees.


---

## The 5 Pillars of Improvement

### 1. Cleanup & Hygiene
- **Dead Code Elimination**: Remove unused imports, unreferenced functions/variables, obsolete comment blocks.
- **File & Directory Organization**: Group related modules cleanly; surface questionable root files to the user rather than deleting them autonomously.
- **Uncommitted & Local File Protection**: NEVER delete, overwrite, or discard uncommitted, untracked (`??`), or `.gitignore`d (`!!`) files without explicit user consent. Always verify `git status --porcelain=v1 --ignored=matching -- <path>` returns empty before deleting any file outside ephemeral caches (`__pycache__/`, `*.pyc`, `workforces/tmp/`).
- **Formatting & Consistency**: Enforce uniform code formatting, naming conventions, and docstrings.
- **Automated Refactoring & Upgrades**: Run automated codemods (`ast-grep`, `jscodeshift`, `Rector` for PHP, `ruff --fix` for Python) to modernize deprecated syntax and upgrade libraries.

### 2. Performance
- **Algorithmic Efficiency**: Replace $O(n^2)$ loops with $O(n)$ or $O(1)$ lookup maps where appropriate.
- **Async & I/O Optimization**: Eliminate sequential `await` bottlenecks using `Promise.all` or parallel execution.
- **Memory & Resource Leak Checks**: Ensure file handles, database connections, and event listeners are properly closed.

### 3. Security
- **Input Sanitization**: Ensure untrusted user inputs are validated and sanitized (prevent SQLi, XSS, Command Injection).
- **Secret Protection & IaC Env Parity**: Check for hardcoded API keys, tokens, or credentials; move to environment variables **only after** verifying parity in deployment configs (`template.yaml`, `template.yml`, `samconfig.toml`, `serverless.yml`, `.env.example`) across every environment. NEVER introduce `"prod"`/`"production"` fallback defaults in code, and obtain explicit consent before running any deployment.
- **Dependency Vulnerabilities & SAST**: Run automated security sweeps (`npm audit`, `pip-audit`, `composer audit`, `trivy fs`, `semgrep`) and remediate CVEs.

### 4. Code Health (SOLID / DRY / KISS & Architecture)
- **Architecture & Boundary Enforcement**: Run `dependency-cruiser` or `madge --circular` to eliminate circular dependencies and prevent UI layers from bypassing domain/service layers.
- **Refactoring Complex Functions**: Break down functions that are hard to follow (well past ~60 lines or cyclomatic complexity >10), extracting only blocks you can name, reuse or test on their own.
- **Deduplication**: Merge identical or near-duplicate functions into single clean utilities.
- **Strict Type Safety**: Strengthen type declarations and eliminate explicit `any` usage.

### 5. Testing & Mutation Resilience
- **TDD & Test Coverage**: Identify untested execution paths and write unit/integration tests.
- **Mutation Testing Score**: Run mutation tests (`stryker run`, `mutmut`) on critical business logic, billing calculations, and domain services to ensure tests kill mutants rather than just providing shallow line coverage.
- **Regression Prevention**: Create reproduction tests for discovered bugs.
- **Flaky Test Cleanup**: Stabilize non-deterministic test assertions.

---

## Workflow Protocols

### Protocol A: Codebase Hygiene & Living OKF Knowledge Maintenance

1. **Audit Repo Hygiene & Living OKF Architecture Docs (`<repo>/docs/`)**:
   Keep portable architecture docs in `<repo>/docs/` using `wf-doc-generator`:
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --audit-hygiene ./
   ```
   *(Fallback: `python3 skills/wf-doc-generator/scripts/scaffold_repo_okf.py --audit-hygiene ./`)*

2. **Code Cleanliness Audit**:
   - **Dead Code & Unused Symbols**: Identify indexed symbols with zero downstream callers across the codebase — and cross-check `<repo>/docs/architecture/*.md` first so externally triggered handlers, webhooks, or EventSubscribers are never flagged or deleted as dead code.
   - **Workspace Scratch Cleanup**: Sweep `workforces/tmp/` and temporary execution logs older than 7 days (never delete outside `workforces/tmp/` without `git status --porcelain=v1 --ignored=matching` verification and user consent).
   - **Stale Cards & Broken Relative Links**: Verify `<repo>/docs/**/*.md` (`affected_files:` globs and relative links) and optional `workforces/knowledge-catalog/` references point to existing files.
   - **Git Workspace Hygiene**: Report untracked artifacts or uncommitted scratch files to the user; NEVER delete or `git clean` them autonomously.

3. **Deferred Issue Reporting**:
   For any issues found that cannot be fixed immediately (e.g. dead code intertwined with active logic, architectural debt, breaking-change refactors), report each one to the issue inbox:
   ```bash
   python3 .agents/skills/wf-issue-tracker/scripts/report-issue.py \
       --title "[Brief description]" \
       --type debt \
       --severity P2 \
       --reporter wf-codebase-improvement \
       --file "[affected file]" \
       --description "[What was found and why it can't be fixed now]" \
       --suggested-action "[What should be done]"
   ```
   *(Fallback: `python3 skills/wf-issue-tracker/scripts/report-issue.py ...`)*
   Do NOT silently drop findings. Every unfixable issue becomes an inbox item.

4. **Summary Report**:
   ```markdown
   ### 🧹 Codebase Maintenance Summary

   | Check | Status | Details |
   |-------|--------|---------|
   | **Repo Living OKF Docs** | ✅ Up to date | `<repo>/docs/index.md` & `docs/architecture/*.md` verified |
   | **Dead Code / Unused Symbols** | ⚠️ 2 found | `unused_helper()` (src/utils.ts:L14) |
   | **Workspace Scratch Clean** | ✅ Clean | 0 stale files removed |
   | **Issues Reported to Inbox** | 📬 2 logged | Reviewed by PM during /wf-sync or task triage |
   ```

---

### Protocol B: Continuous Improvement Across Pillars

1. **Baseline & Architecture Verification**:
   - Read `<repo>/docs/index.md` and matching `docs/architecture/*.md` cards (`affected_files:`) before deleting or refactoring so invariants, subscribers, env contracts, and verification commands are known up front.
   - Run `python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --impact <file>` and targeted `grep_search` on import paths/exported symbols to map direct importers and Git co-changed files.
   - Verify callers and behavior via real stack typecheckers and tests (`npm test`, `pytest`, `go test`, `cargo test`, `post_code_reviewer.py --run-checks --strict`).

2. **Pillar Audit**:
   - Perform static checks for selected pillar(s).
   - Generate improvement report listing issues by severity (P0, P1, P2).

3. **Incremental Execution**:
   - Apply fixes cleanly following Clean Coder principles (`skills/wf-clean-coder/SKILL.md`).
   - Run tests after each change to guarantee zero regression.

4. **Living Docs & Summary**:
   - Update matching `<repo>/docs/architecture/*.md` (`affected_files`, `last_verified_commit`, `## Constraints, Invariants & Gotchas`) and inline boundary docblocks in modified files; refresh `docs/index.md` via `scaffold_repo_okf.py --scan ./` (and optionally rebuild `workforces/knowledge-catalog/` if used).
   - Present a concise summary of improvements made.
