---
name: post-code-review
description: Post-hook whole-codebase code reviewer. Analyzes modified code diffs against code-graph dependency relationships, contract signatures, swallowed errors, deduplication, and test coverage to provide immediate feedback for AI self-healing.
---

# Skill: Post-Hook Whole-Codebase Code Reviewer

Automated post-tool code reviewer designed to audit code modifications in context with the entire repository.

---

## Capabilities

1. **Downstream Blast Radius Audit**: Checks modified function/class signatures against caller files discovered in `workforces/code-graph.json`.
2. **Resilience & Swallowed Error Detection**: Flags empty `catch`/`except` blocks or swallowed promise rejections.
3. **Deduplication Check**: Cross-references new functions against existing indexed helper methods.
4. **Missing Test Verification**: Flags logic file modifications lacking unit/integration test updates.
5. **AI Self-Healing Feedback**: Outputs structured actionable feedback directly to console stdout after code modifications.

---

## Execution Commands

### Manual Execution
```bash
python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./
```

### Pre-Hook Context Analysis (Pre-Coding)
```bash
python3 skills/code-graph/scripts/pre_impact_analyzer.py --file <target_file>
```

---

## Review Rules Checklist

| Category | Check Description | Action |
|---|---|---|
| **Contract Compatibility** | Changed function signature in target file has callers in external files | Flag dependent caller files for parameter alignment |
| **Error Handling** | `except: pass` or `catch {}` present in diff | Require logging or rethrowing with context |
| **Deduplication** | Function logic duplicates an existing helper in `code-graph.json` | Recommend reusing existing helper utility |
| **Test Coverage** | Code logic modified without test updates | Request corresponding unit/integration tests |
