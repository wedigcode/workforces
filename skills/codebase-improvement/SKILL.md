---
name: codebase-improvement
description: >-
  Audits, refactors, and elevates repository quality across five core engineering pillars: Cleanup (dead code, unused deps), Performance (bottlenecks, query efficiency), Security (vulnerabilities, hardcoded secrets), Code Health (type safety, architectural debt), and Testing (coverage gaps). Reach for this skill during proactive hygiene sweeps, post-feature cleanup, or when investigating degraded system performance and accumulated technical debt.
---
# Skill: Continuous Codebase Improvement & Hygiene

Structured domain capability for auditing, maintaining hygiene, and upgrading code quality across five core engineering pillars. Combines automated codebase cleanliness audits and knowledge graph maintenance with continuous refactoring and PR reviews.

---

## Triggering & Execution

This skill is invoked autonomously by `@programmer` or coordinators, or directly through natural language:

### Prompt Triggers
- *"Clean up the codebase and refresh knowledge"*
- *"Audit code quality across the 5 pillars"*
- *"Find dead code and unreferenced symbols"*
- *"Audit performance bottlenecks and memory leaks"*
- *"Check security: input validation and hardcoded secrets"*
- *"Review open PRs and Google Jules sessions"*

### Coordinator & Standup Invocations
- **Via `/wf-sync`**: Standups surface pending debt and recommend hygiene sweeps.
- **Standup & Pre-Commit Sweeps**: Automatically executed prior to major architectural refactoring.
- **Autonomous Execution**: Route refactoring tasks directly to `@programmer` subagents via `agent-parallelization` isolated worktrees.


---

## The 5 Pillars of Improvement

### 1. Cleanup & Hygiene
- **Dead Code Elimination**: Remove unused imports, unreferenced functions/variables, obsolete comment blocks.
- **File & Directory Organization**: Group related modules cleanly, eliminate orphan scratch files.
- **Formatting & Consistency**: Enforce uniform code formatting, naming conventions, and docstrings.
- **Automated Refactoring & Upgrades**: Run automated codemods (`ast-grep`, `jscodeshift`, `Rector` for PHP, `ruff --fix` for Python) to modernize deprecated syntax and upgrade libraries.

### 2. Performance
- **Algorithmic Efficiency**: Replace $O(n^2)$ loops with $O(n)$ or $O(1)$ lookup maps where appropriate.
- **Async & I/O Optimization**: Eliminate sequential `await` bottlenecks using `Promise.all` or parallel execution.
- **Memory & Resource Leak Checks**: Ensure file handles, database connections, and event listeners are properly closed.

### 3. Security
- **Input Sanitization**: Ensure untrusted user inputs are validated and sanitized (prevent SQLi, XSS, Command Injection).
- **Secret Protection**: Check for hardcoded API keys, tokens, or credentials; move to environment variables.
- **Dependency Vulnerabilities & SAST**: Run automated security sweeps (`npm audit`, `pip-audit`, `composer audit`, `trivy fs`, `semgrep`) and remediate CVEs.

### 4. Code Health (SOLID / DRY / KISS & Architecture)
- **Architecture & Boundary Enforcement**: Run `dependency-cruiser` or `madge --circular` to eliminate circular dependencies and prevent UI layers from bypassing domain/service layers.
- **Refactoring Complex Functions**: Break down functions >30 lines or cyclomatic complexity >10.
- **Deduplication**: Merge identical or near-duplicate functions into single clean utilities.
- **Strict Type Safety**: Strengthen type declarations and eliminate explicit `any` usage.

### 5. Testing & Mutation Resilience
- **TDD & Test Coverage**: Identify untested execution paths and write unit/integration tests.
- **Mutation Testing Score**: Run mutation tests (`stryker run`, `mutmut`) on critical business logic, billing calculations, and domain services to ensure tests kill mutants rather than just providing shallow line coverage.
- **Regression Prevention**: Create reproduction tests for discovered bugs.
- **Flaky Test Cleanup**: Stabilize non-deterministic test assertions.

---

## Workflow Protocols

### Protocol A: Codebase Hygiene & Knowledge Maintenance

1. **Force Full Code Graph & OKF Catalog Rebuild**:
   Re-indexes all codebase symbols and regenerates individual OKF concept Markdown files under `workforces/knowledge-catalog/code/`:
   ```bash
   python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog/code --build-okf --force
   ```
   *(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py ...`)*

2. **Code Cleanliness Audit**:
   - **Dead Code & Unused Symbols**: Identify indexed symbols with zero downstream callers across the codebase.
   - **Workspace Scratch Cleanup**: Sweep `workforces/tmp/` and temporary execution logs older than 7 days.
   - **Broken Relative Links**: Scan `workforces/knowledge-catalog/` for references pointing to non-existent files.
   - **Git Workspace Hygiene**: Report untracked artifacts or uncommitted scratch files.

3. **Deferred Issue Reporting**:
   For any issues found that cannot be fixed immediately (e.g. dead code intertwined with active logic, architectural debt, breaking-change refactors), report each one to the issue inbox:
   ```bash
   python3 .agents/skills/issue-tracker/scripts/report-issue.py \
       --title "[Brief description]" \
       --type debt \
       --severity P2 \
       --reporter clean \
       --file "[affected file]" \
       --description "[What was found and why it can't be fixed now]" \
       --suggested-action "[What should be done]"
   ```
   *(Fallback: `python3 skills/issue-tracker/scripts/report-issue.py ...`)*
   Do NOT silently drop findings. Every unfixable issue becomes an inbox item.

4. **Summary Report**:
   ```markdown
   ### 🧹 Codebase Maintenance Summary

   | Check | Status | Details |
   |-------|--------|---------|
   | **Code Graph Index** | ✅ Up to date | 32 symbols indexed in `workforces/code-graph.json` |
   | **OKF Knowledge Catalog** | ✅ Rebuilt | Catalog synced at `workforces/knowledge-catalog/code/index.md` |
   | **Dead Code / Unused Symbols** | ⚠️ 2 found | `unused_helper()` (src/utils.ts:L14) |
   | **Workspace Scratch Clean** | ✅ Clean | 0 stale files removed |
   | **Issues Reported to Inbox** | 📬 2 logged | Reviewed by PM during /wf-sync or task triage |
   ```

---

### Protocol B: Continuous Improvement Across Pillars

1. **Baseline Verification**:
   - Check if project tests pass (`npm test`, `pytest`, `go test`, `cargo test`, etc.).
   - Index symbols using `python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./`.

2. **Pillar Audit**:
   - Perform static checks for selected pillar(s).
   - Generate improvement report listing issues by severity (P0, P1, P2).

3. **Incremental Execution**:
   - Apply fixes cleanly following Clean Coder principles (`skills/clean-coder/SKILL.md`).
   - Run tests after each change to guarantee zero regression.

4. **Catalog & Summary**:
   - Update `workforces/knowledge-catalog/` with updated symbol graphs.
   - Present a concise summary of improvements made.
