---
description: Continuous Codebase Improvement command — audit and refactor across cleanup, performance, security, health, and testing
---

# /work improve — Continuous Codebase Improvement

Audits the codebase and executes continuous refactoring across the 5 core pillars.

---

## Usage

```
/work improve                    → Audit all 5 pillars and surface top recommendations
/work improve cleanup            → Focus audit and refactoring on cleanup & dead code
/work improve performance        → Audit performance bottlenecks, async, memory
/work improve security           → Audit input validation, secrets, CVEs
/work improve health             → Refactor SOLID/DRY/KISS violations & method duplication
/work improve testing            → Expand test coverage and write missing TDD suites
/work improve pr                 → Audit open GitHub PRs, post review comments, escalate blockers
/work improve jules              → Audit and review code in active Google Jules sessions
/work improve --auto             → Automatically perform low-risk refactoring across all pillars
```

---

## Execution Protocol

1. **Baseline Verification**:
   - Check if project tests pass (`npm test`, `pytest`, `go test`, `cargo test`, etc.).
   - Index symbols using `python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./`.

2. **Pillar Audit**:
   - Perform static checks for selected pillar(s).
   - Generate improvement report listing issues by severity (P0, P1, P2).

3. **Incremental Execution**:
   - Apply fixes cleanly following Clean Coder rules (`rules/clean-coder.md`).
   - Run tests after each change to guarantee zero regression.

4. **Catalog & Summary**:
   - Update `workforces/knowledge-catalog/` with updated symbol graphs.
   - Present a concise summary of improvements made.
