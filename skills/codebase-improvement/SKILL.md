---
name: codebase-improvement
description: Continuous codebase audit and automated refactoring across 5 pillars: Cleanup, Performance, Security, Code Health, Testing.
---

# Skill: Continuous Codebase Improvement

Structured workflow for auditing and upgrading code quality across five core engineering pillars.

---

## The 5 Pillars of Improvement

### 1. Cleanup
- **Dead Code Elimination**: Remove unused imports, unreferenced functions/variables, obsolete comment blocks.
- **File & Directory Organization**: Group related modules cleanly, eliminate orphan scratch files.
- **Formatting & Consistency**: Enforce uniform code formatting, naming conventions, and docstrings.

### 2. Performance
- **Algorithmic Efficiency**: Replace $O(n^2)$ loops with $O(n)$ or $O(1)$ lookup maps where appropriate.
- **Async & I/O Optimization**: Eliminate sequential `await` bottlenecks using `Promise.all` or parallel execution.
- **Memory & Resource Leak Checks**: Ensure file handles, database connections, and event listeners are properly closed.

### 3. Security
- **Input Sanitization**: Ensure untrusted user inputs are validated and sanitized (prevent SQLi, XSS, Command Injection).
- **Secret Protection**: Check for hardcoded API keys, tokens, or credentials; move to environment variables.
- **Dependency Vulnerabilities**: Audit package dependencies for known CVEs.

### 4. Code Health (SOLID / DRY / KISS)
- **Refactoring Complex Functions**: Break down functions >30 lines or cyclomatic complexity >10.
- **Deduplication**: Merge identical or near-duplicate functions into single clean utilities.
- **Type Safety**: Strengthen type declarations and remove explicit `any` usage.

### 5. Testing
- **TDD & Test Coverage**: Identify untested execution paths and write unit/integration tests.
- **Regression Prevention**: Create reproduction tests for discovered bugs.
- **Flaky Test Cleanup**: Stabilize non-deterministic test assertions.

---

## Audit Protocol

1. Run symbol indexer to analyze function size and complexity:
   ```bash
   python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./
   ```
   *(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py --scan ./`)*
2. Inspect `workforces/code-graph.json` and check for:
   - Duplicate signatures or function names
   - Monolithic functions with large line counts
3. Run test suites (`npm test`, `pytest`, `go test`, `cargo test`) to establish a passing baseline.
4. Apply refactorings incrementally, verifying tests pass after each edit.
