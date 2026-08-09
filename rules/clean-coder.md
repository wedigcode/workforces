---
trigger: always_on
---

# Clean Coder Engineering Rules

These engineering rules govern all code generation, refactoring, and execution within workforce workflows.

---

## 1. Deduplication & Existing Method Discovery
- **Check Before Create**: BEFORE creating any function, method, helper, or class, the agent MUST check if a suitable method already exists in the codebase.
- **Symbol Index Lookup**: Use the `code-graph` tool (`python3 skills/code-graph/scripts/graph_indexer.py --query <name>`), `grep_search`, or the OKF catalog under `workforces/knowledge-catalog/` to verify existence.
- **Reuse and Extend**: If a function with similar capability exists, reuse or refactor it cleanly rather than introducing duplicate implementations.

## 2. Test-Driven Development (TDD) Mindset
- **Expectation First**: Define test cases, expected inputs/outputs, and contract boundaries before writing implementation logic.
- **Fail First Verification**: When adding features or fixing bugs, ensure a failing test or assertion exists to demonstrate the bug/gap before writing code to fix it.
- **Refactor Safely**: Refactor code only while tests pass.

## 3. SOLID, DRY & KISS Principles
- **Single Responsibility (SRP)**: Each function/class must do ONE thing and do it exceptionally well. Keep functions small (ideally <30 lines).
- **Open/Closed (OCP)**: Design modules for extension without modifying core existing contracts.
- **Liskov Substitution (LSP)**: Derived structures/types must remain fully compatible with base abstractions.
- **Interface Segregation (ISP)**: Prefer small, cohesive interfaces/types over monolithic ones.
- **Dependency Inversion (DIP)**: Depend upon abstractions, not concrete implementations.
- **DRY (Don't Repeat Yourself)**: Zero copy-paste logic. Extract repeated logic into clean, reusable utilities.
- **KISS (Keep It Simple, Stupid)**: Avoid over-engineering. Pick the simplest architecture that satisfies all requirements cleanly.

## 4. Naming & Self-Documenting Code
- **Expressive Naming**: Use intent-revealing names for variables, methods, and classes (e.g. `calculateMonthlyTaxableIncome` instead of `calcTax`).
- **Clean Comments**: Comments must explain *why* non-obvious code decisions were made, NOT *what* standard code line does. Let clean code describe *what*.
- **No Swallowed Errors**: NEVER write empty `catch` or `except` blocks, silence exceptions with dummy fallbacks, or ignore promise rejections. Log, annotate, or propagate errors gracefully.
