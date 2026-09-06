---
name: post-code-review
description: Performs pre-handoff code analysis on git diffs, cross-referencing changes against the AST code-graph to detect broken contract signatures, unhandled errors, duplicate utility functions, and missing tests. Executes the automated quality gate triad (unit tests, static analysis/type checks, and linters) and dependency security audits to guarantee zero errors before code handoff. Reach for this skill immediately after modifying code to verify architectural hygiene, run quality gates, prevent regressions, and trigger automated self-healing before committing or opening a pull request.
---
# Skill: Pre-Handoff Whole-Codebase Code Reviewer & Quality Gate

Automated whole-codebase code reviewer and quality gate designed to audit code modifications in context with the entire repository and verify zero test regressions, type errors, or lint failures before code handoff.

---

## Capabilities

1. **Downstream Blast Radius Audit**: Checks modified function/class signatures against caller files discovered in `workforces/code-graph.json`.
2. **Resilience & Swallowed Error Detection**: Flags empty `catch`/`except` blocks or swallowed promise rejections.
3. **Deduplication Check**: Cross-references new functions against existing indexed helper methods.
4. **Over-Engineering & Class Helper Audit**: Audits newly added class methods to ensure neighboring static/public helper methods in the same class (e.g. `Format::convertNumber()`) are composed rather than duplicated with raw regex or manual type-casting.
5. **Quality Gate Triad Execution (Tests + Static Analysis + Linters)**: Auto-detects and executes the target project's unit test suite, static analysis / strict typechecker (`tsc --noEmit`, `mypy`, `phpstan`), and linter (`biome`, `eslint`, `ruff`, `pint`).
6. **Dependency Security Audits**: Triggers automated vulnerability checks (`npm audit`, `pip-audit`, `composer audit`) whenever dependency manifests or lockfiles are modified.
7. **Zero-Handoff Gate Enforcement**: If any test fails, typecheck breaks, or linter reports errors, blocks completion and demands immediate self-remediation before handing over code.

---

## Execution Commands

### 1. Mandatory Post-Edit Heuristic Check
Fires on post-tool calls to audit diffs, blast radius, and swallowed errors:
```bash
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./` — automatically resolves target project root from `workrules.md`/`workstate.md`, `WORKFORCE_TARGET_DIR`, or pass explicit `--target-dir <path>`)*

### 2. Pre-Handoff Quality Gate Verification (MANDATORY BEFORE COMPLETION)
Before declaring any task done or handing code over to the user, the agent MUST run the full quality gate verification:
```bash
python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
```
*(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*

### 3. Pre-Hook Context Analysis (Pre-Coding)
```bash
python3 .agents/skills/code-graph/scripts/pre_impact_analyzer.py --file <target_file> [--target-dir <path>]
```
*(Fallback: `python3 skills/code-graph/scripts/pre_impact_analyzer.py ...`)*

---

## Review Rules Checklist

| Category | Check Description | Action |
|---|---|---|
| **Contract Compatibility** | Changed function signature in target file has callers in external files | Flag dependent caller files for parameter alignment |
| **Error Handling** | `except: pass` or `catch {}` present in diff | Require logging or rethrowing with context |
| **Deduplication** | Function logic duplicates an existing helper in `code-graph.json` | Recommend reusing existing helper utility |
| **Class Helper Reuse** | Custom regex/parsing used when neighboring helper exists in same class file | Recommend composing existing class helper (e.g. `convertNumber`) |
| **Unit Tests** | Unit test suite execution fails or regressions occur | **BLOCK HANDOFF**: Remediate all test failures immediately |
| **Static Analysis** | Strict typecheck errors (`tsc`, `mypy`, `phpstan`) detected | **BLOCK HANDOFF**: Resolve type violations; zero `any` escapes |
| **Styling & Linting** | Code formatting or lint rules violated (`biome`, `eslint`, `ruff`) | **BLOCK HANDOFF**: Fix lint errors before concluding |
| **Dependency Security** | High/critical vulnerabilities introduced in manifests | **BLOCK HANDOFF**: Upgrade vulnerable packages before completing |
