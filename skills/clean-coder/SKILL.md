---
name: clean-coder
description: Mindset and protocol for TDD, deduplication, clean architecture (SOLID/DRY/KISS), self-documenting code, and robust error handling.
---

# Skill: Clean Coder

Provides step-by-step guidance for writing pristine, self-documenting, reusable code while preventing function duplication and error swallowing.

---

## Workflow Protocol

### Step 1: Pre-Implementation Method Lookup
Before writing any code:
1. Run symbol search via `code-graph` or `grep_search`:
   ```bash
   python3 skills/code-graph/scripts/graph_indexer.py --query "<method_name_or_keyword>"
   ```
2. Inspect `workforces/knowledge-catalog/symbols/` or `workforces/code-graph.json` to check if a function already provides the required logic.
3. If an existing method covers ~80% of requirements, extend or compose it cleanly rather than re-creating.

### Step 2: TDD Test & Contract Design
1. State the input/output contract clearly.
2. Write unit test cases (or assertion scripts) covering:
   - Happy path
   - Edge cases (null/undefined inputs, empty collections, extreme bounds)
   - Failure modes & expected error exceptions
3. Run the test to confirm failure (Red state).
4. Write minimal, clean code to pass the test (Green state).
5. Refactor for clarity and performance (Refactor state).

### Step 3: Clean Code & Architecture Checklist

- [ ] **Function Size**: Is the function focused and concise (<30 lines)?
- [ ] **Single Responsibility**: Does this function solve one clear objective?
- [ ] **Self-Documenting Names**: Are names unambiguous (verbs for methods, nouns for classes)?
- [ ] **DRY Check**: Is there any duplicated logic across files?
- [ ] **Error Handling**: Are errors caught, enriched with context (stack traces, parameters), and re-thrown or handled gracefully?

### Step 4: Graceful Error Handling Patterns

#### ❌ Bad (Swallowing Errors)
```typescript
// NEVER DO THIS
try {
  await processPayment(user);
} catch (e) {
  // silent fail
}
```

#### ✅ Good (Enriched Error Handling)
```typescript
try {
  await processPayment(user);
} catch (error) {
  logger.error("Payment processing failed", { userId: user.id, error });
  throw new PaymentProcessingError(`Failed to process payment for user ${user.id}`, { cause: error });
}
```
